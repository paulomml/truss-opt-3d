"""
Endpoints REST + WebSocket da API TRUSS-OPT 3D.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.memorial import codificar_base64, gerar_memorial_docx, gerar_memorial_pdf
from api.schemas import (
    MaterialSchema,
    PerfilSchema,
    RequisicaoOtimizacao,
    RespostaOtimizacao,
    StatusTarefa,
    TarefaResumo,
)
from core.cache import gerar_chave_cache, obter_do_cache
from core.celery_app import app_celery
from core.config import configuracoes
from core.database import obter_sessao
from db.modelos import Material, MemorialCalculo, Perfil, TarefaOtimizacao
from worker.tarefas import _atualizar_status_tarefa, otimizar_trelice

_logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Tempo máximo (em segundos) que uma tarefa pode ficar em PENDENTE antes de
# ser considerada "travada" (worker não respondeu). Evita o bug do PENDENTE
# infinito quando o worker Celery não consegue consumir a tarefa.
_TIMEOUT_PENDENTE_SEGUNDOS = 60.0

# Intervalo entre heartbeats enviados ao frontend via WebSocket (segundos).
# Garante que o cliente sempre receba alguma mensagem, mesmo sem mudança de
# progresso, para que possa detectar falhas de conexão/worker.
_INTERVALO_HEARTBEAT_SEGUNDOS = 5.0


@router.get("/health")
async def health() -> dict:
    """Health check operacional com metadados úteis ao frontend."""
    # Número de threads lógicas do CPU hospedeiro (limite para paralelismo).
    try:
        cpu_count = os.cpu_count() or 1
    except Exception:
        cpu_count = 1
    return {
        "status": "ok",
        "servico": "TRUSS-OPT 3D API",
        "versao": "1.0.0",
        "cpu_count": cpu_count,
        "ambiente": configuracoes.ambiente,
        "celery_max_concorrencia": configuracoes.celery_max_concorrencia,
    }


@router.get("/health/worker")
async def health_worker() -> dict:
    """
    Diagnóstico do worker Celery.

    Dispara a tarefa `tarefa_diagnostico` e aguarda até 5 segundos por uma
    resposta. Se o worker não responder, retorna `worker_disponivel=False`
    para que o frontend possa avisar o usuário antes de iniciar uma análise.
    """
    try:
        # Tenta pingar o worker: a tarefa_diagnostico retorna um dict simples.
        resultado = app_celery.send_task(
            "core.celery_app.tarefa_diagnostico",
            kwargs={},
            queue="default",
        )
        # Aguarda até 5s por uma resposta (timeout curto e não bloqueante).
        valor = resultado.get(timeout=5.0, disable_sync_subtasks=False)
        return {
            "worker_disponivel": True,
            "resposta": valor,
        }
    except Exception as e:
        # Timeout ou worker offline: o frontend deve bloquear novas análises.
        _logger.warning(f"Worker Celery não respondeu ao diagnóstico: {e}")
        return {
            "worker_disponivel": False,
            "erro": str(e),
        }


@router.get("/materiais", response_model=list[MaterialSchema])
async def listar_materiais(sessao: Session = Depends(obter_sessao)) -> list[Material]:
    """Lista todos os materiais estruturais ativos."""
    stmt = select(Material).where(Material.ativo.is_(True)).order_by(Material.nome)
    return list(sessao.scalars(stmt))


@router.get("/perfis", response_model=list[PerfilSchema])
async def listar_perfis(
    familia: str | None = None,
    sessao: Session = Depends(obter_sessao),
) -> list[Perfil]:
    """Lista perfis cadastrados, opcionalmente filtrados por família."""
    stmt = select(Perfil).where(Perfil.ativo.is_(True))
    if familia:
        stmt = stmt.where(Perfil.familia == familia)
    stmt = stmt.order_by(Perfil.familia, Perfil.nome)
    return list(sessao.scalars(stmt))


@router.get("/normas")
async def listar_normas() -> dict:
    """
    Expõe as constantes das normas brasileiras usadas pelo sistema.

    Permite ao frontend exibir uma referência de equações e parâmetros
    sem duplicar os valores no código cliente.
    """
    from engineering.standards import nbr_6120, nbr_6123, nbr_8800

    return {
        "nbr_6120": {
            "nome": "NBR 6120:2019",
            "descricao": "Cargas para o cálculo de estruturas de edificações.",
            "constantes": {
                "psi_0": nbr_6120.PSI_0,
                "psi_1": nbr_6120.PSI_1,
                "psi_2": nbr_6120.PSI_2,
                "gamma_g": nbr_6120.GAMMA_G,
                "gamma_q": nbr_6120.GAMMA_Q,
            },
            "combinacoes_elu": ["Normal", "Secundário", "Alívio", "Sem Vento", "Vento Dominante"],
            "combinacoes_els": ["Flecha Total", "Flecha Frequente", "Flecha Permanente"],
        },
        "nbr_6123": {
            "nome": "NBR 6123:1988",
            "descricao": "Forças devidas ao vento em edificações.",
            "constantes": {
                "pressao_dinamica_coeficiente": 0.613,
            },
            "vento_default": {
                "v0_mps": 40.0,
                "s1": 1.0,
                "s2": 1.0,
                "s3": 1.0,
                "ce_externo": 0.8,
                "ci_interno": 0.0,
            },
        },
        "nbr_8800": {
            "nome": "NBR 8800:2008",
            "descricao": "Projeto de estruturas de aço e de estruturas mistas de aço e concreto.",
            "constantes": {
                "gamma_a1": nbr_8800.GAMMA_A1,
                "flecha_limite_divisor": configuracoes.nbr_flecha_limite,
                "esbeltez_max_compressao": configuracoes.nbr_esbeltez_max_compressao,
                "esbeltez_max_tracao": configuracoes.nbr_esbeltez_max_tracao,
                "carga_manutencao_kn": configuracoes.nbr_carga_manutencao_kn,
            },
            "equacoes": [
                {"id": "5.2.2", "nome": "Resistência à tração (N_rd)"},
                {"id": "5.3.2", "nome": "Resistência à compressão (N_rd)"},
                {"id": "5.3.3.1", "nome": "Fator de flambagem χ (λ₀ ≤ 1,5)"},
                {"id": "5.3.3.2", "nome": "Fator de flambagem χ (λ₀ > 1,5)"},
                {"id": "5.3.4.1", "nome": "Limite de esbeltez à compressão"},
                {"id": "5.2.8.1", "nome": "Limite de esbeltez à tração"},
                {"id": "5.5.1.2", "nome": "Interação N+M"},
                {"id": "Anexo F", "nome": "Fator Q (flambagem local)"},
            ],
        },
        "ga": {
            "defaults": {
                "geracoes": configuracoes.ag_geracoes,
                "populacao": configuracoes.ag_populacao_tamanho,
                "probabilidade_cruzamento": configuracoes.ag_probabilidade_cruzamento,
                "probabilidade_mutacao": configuracoes.ag_probabilidade_mutacao,
                "indice_torneio": configuracoes.ag_indice_torneio,
                "max_perfis_distintos": configuracoes.ag_max_perfis_distintos,
                "usar_refinamento_local": configuracoes.ag_usar_refinamento_local,
                "penalidade_violacao_normativa": configuracoes.ag_penalidade_violacao_normativa,
                "penalidade_diversidade_perfis": configuracoes.ag_penalidade_diversidade_perfis,
            },
        },
    }


@router.post("/otimizar", response_model=StatusTarefa, status_code=status.HTTP_202_ACCEPTED)
async def iniciar_otimizacao(
    requisicao: RequisicaoOtimizacao,
    sessao: Session = Depends(obter_sessao),
) -> StatusTarefa:
    """
    Inicia uma otimização assíncrona via Celery.

    Retorna imediatamente com o ID da tarefa para polling subsequente.
    """
    # Verifica cache: se já existe resultado idêntico, retorna imediatamente.
    payload_dict = requisicao.model_dump(mode="json")
    chave = gerar_chave_cache(payload_dict)
    cacheado = obter_do_cache(chave)
    if cacheado:
        # Cria uma tarefa CONCLUIDA reaproveitando o resultado.
        tarefa = TarefaOtimizacao(
            status="CONCLUIDO",
            progresso=100.0,
            payload_json=json.dumps(payload_dict, default=str, ensure_ascii=False),
            resultado_json=json.dumps(cacheado, default=str, ensure_ascii=False),
        )
        sessao.add(tarefa)
        sessao.commit()
        sessao.refresh(tarefa)
        return StatusTarefa(
            task_id=str(tarefa.id),
            status="CONCLUIDO",
            progresso=100.0,
            resultado=RespostaOtimizacao(**cacheado),
            criado_em=tarefa.criado_em,
        )

    # Persiste a tarefa no banco.
    tarefa = TarefaOtimizacao(
        status="PENDENTE",
        progresso=0.0,
        payload_json=json.dumps(payload_dict, default=str, ensure_ascii=False),
    )
    sessao.add(tarefa)
    sessao.commit()
    sessao.refresh(tarefa)

    # Dispara a tarefa Celery e salva o ID para cancelamento posterior.
    resultado_celery = otimizar_trelice.delay(tarefa.id, payload_dict)
    tarefa.celery_task_id = resultado_celery.id
    sessao.commit()

    # Salva no cache para futuras requisições idênticas.
    # (O resultado final será salvo quando a tarefa concluir.)
    return StatusTarefa(
        task_id=str(tarefa.id),
        status="PENDENTE",
        progresso=0.0,
        criado_em=tarefa.criado_em,
    )


@router.get("/tarefas", response_model=list[TarefaResumo])
async def listar_tarefas(
    limite: int = Query(50, ge=1, le=500, description="Número máximo de tarefas retornadas."),
    status_filtro: str | None = Query(None, description="Filtra por status (PENDENTE, EM_ANDAMENTO, ...)."),
    sessao: Session = Depends(obter_sessao),
) -> list[TarefaResumo]:
    """
    Lista o histórico de tarefas, das mais recentes para as mais antigas.

    Permite ao frontend exibir um painel de histórico com status e progresso.
    """
    stmt = select(TarefaOtimizacao)
    if status_filtro:
        stmt = stmt.where(TarefaOtimizacao.status == status_filtro)
    stmt = stmt.order_by(TarefaOtimizacao.criado_em.desc()).limit(limite)
    tarefas = list(sessao.scalars(stmt))
    return [
        TarefaResumo(
            task_id=str(t.id),
            status=t.status,
            progresso=t.progresso,
            criado_em=t.criado_em,
            iniciado_em=t.iniciado_em,
            finalizado_em=t.finalizado_em,
            mensagem=t.mensagem_erro,
            tem_resultado=bool(t.resultado_json),
        )
        for t in tarefas
    ]


@router.get("/tarefas/{tarefa_id}", response_model=StatusTarefa)
async def consultar_tarefa(
    tarefa_id: int,
    sessao: Session = Depends(obter_sessao),
) -> StatusTarefa:
    """Consulta status e resultado de uma tarefa."""
    tarefa = sessao.get(TarefaOtimizacao, tarefa_id)
    if not tarefa:
        raise HTTPException(
            status_code=404,
            detail=f"Tarefa {tarefa_id} não encontrada.",
        )

    resultado = None
    if tarefa.resultado_json:
        try:
            resultado = RespostaOtimizacao(**json.loads(tarefa.resultado_json))
        except Exception:
            resultado = None

    return StatusTarefa(
        task_id=str(tarefa.id),
        status=tarefa.status,
        progresso=tarefa.progresso,
        mensagem=tarefa.mensagem_erro,
        resultado=resultado,
        criado_em=tarefa.criado_em,
    )


@router.post("/tarefas/{tarefa_id}/cancelar", response_model=StatusTarefa)
async def cancelar_tarefa(
    tarefa_id: int,
    sessao: Session = Depends(obter_sessao),
) -> StatusTarefa:
    """Cancela uma tarefa em andamento."""
    tarefa = sessao.get(TarefaOtimizacao, tarefa_id)
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")

    if tarefa.celery_task_id:
        # Revoga a tarefa Celery (envia sinal de terminação ao worker).
        app_celery.control.revoke(tarefa.celery_task_id, terminate=True)

    _atualizar_status_tarefa(tarefa_id, "CANCELADO")

    return StatusTarefa(
        task_id=str(tarefa.id),
        status="CANCELADO",
        progresso=tarefa.progresso,
        mensagem="Cancelada pelo usuário.",
        criado_em=tarefa.criado_em,
    )


@router.get("/tarefas/{tarefa_id}/memorial/{formato}")
async def baixar_memorial(
    tarefa_id: int,
    formato: str,
    sessao: Session = Depends(obter_sessao),
) -> Response:
    """
    Gera e disponibiliza o memorial de cálculo em PDF ou DOCX.

    Formato suportado: 'pdf' ou 'docx'.
    """
    if formato not in ("pdf", "docx"):
        raise HTTPException(status_code=400, detail="Formato deve ser 'pdf' ou 'docx'.")

    tarefa = sessao.get(TarefaOtimizacao, tarefa_id)
    if not tarefa or not tarefa.resultado_json:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada ou não concluída.")

    # Verifica se já existe memorial gerado.
    stmt = select(MemorialCalculo).where(
        MemorialCalculo.tarefa_id == tarefa_id,
        MemorialCalculo.formato == formato,
    )
    existente = sessao.scalars(stmt).first()
    if existente:
        from api.memorial import decodificar_base64

        conteudo = decodificar_base64(existente.conteudo_b64)
        media_tipo = (
            "application/pdf"
            if formato == "pdf"
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        return Response(
            content=conteudo,
            media_type=media_tipo,
            headers={"Content-Disposition": f'attachment; filename="{existente.nome_arquivo}"'},
        )

    # Gera o memorial.
    requisicao = RequisicaoOtimizacao(**json.loads(tarefa.payload_json))
    resposta = RespostaOtimizacao(**json.loads(tarefa.resultado_json))

    if formato == "pdf":
        conteudo = gerar_memorial_pdf(requisicao, resposta)
        nome_arquivo = f"memorial_tarefa_{tarefa_id}.pdf"
        media_tipo = "application/pdf"
    else:
        conteudo = gerar_memorial_docx(requisicao, resposta)
        nome_arquivo = f"memorial_tarefa_{tarefa_id}.docx"
        media_tipo = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    # Persiste para reuso.
    memorial = MemorialCalculo(
        tarefa_id=tarefa_id,
        formato=formato,
        nome_arquivo=nome_arquivo,
        conteudo_b64=codificar_base64(conteudo),
        tamanho_bytes=len(conteudo),
    )
    sessao.add(memorial)
    sessao.commit()

    return Response(
        content=conteudo,
        media_type=media_tipo,
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@router.websocket("/ws/otimizar")
async def websocket_otimizar(websocket: WebSocket) -> None:
    """
    WebSocket para streaming de progresso da otimização.
    """
    await websocket.accept()
    try:
        dados = await websocket.receive_text()
        payload = json.loads(dados)

        # Cria tarefa no banco.
        from core.database import SessionLocal

        with SessionLocal() as sessao:
            tarefa = TarefaOtimizacao(
                status="PENDENTE",
                progresso=0.0,
                payload_json=json.dumps(payload, default=str, ensure_ascii=False),
            )
            sessao.add(tarefa)
            sessao.commit()
            sessao.refresh(tarefa)
            tarefa_id = tarefa.id
            data_criacao = tarefa.criado_em

        # Dispara Celery e salva o ID da task para permitir cancelamento.
        resultado_celery = otimizar_trelice.delay(tarefa_id, payload)
        with SessionLocal() as sessao:
            tarefa = sessao.get(TarefaOtimizacao, tarefa_id)
            if tarefa:
                tarefa.celery_task_id = resultado_celery.id
                sessao.commit()

        # Envia confirmação imediata com o task_id (mesmo antes do primeiro
        # progresso), permitindo ao frontend acionar o cancelamento via REST.
        await websocket.send_json(
            {
                "type": "progress",
                "data": {
                    "task_id": str(tarefa_id),
                    "progress": 0.0,
                    "status": "PENDENTE",
                    "logs": "Status: aguardando o worker Celery iniciar o processamento...",
                },
            }
        )

        # Polling de status até conclusão.
        ultimo_progresso = -1.0
        ultimo_heartbeat = 0.0
        iteracao = 0
        while True:
            await asyncio.sleep(1.5)
            iteracao += 1
            agora = time.monotonic()

            with SessionLocal() as sessao:
                tarefa = sessao.get(TarefaOtimizacao, tarefa_id)
                if not tarefa:
                    await websocket.send_json(
                        {"type": "error", "message": "Tarefa não encontrada."}
                    )
                    break

                # Detecção de tarefa presa em PENDENTE (worker não respondeu).
                if (
                    tarefa.status == "PENDENTE"
                    and tarefa.iniciado_em is None
                    and data_criacao
                    and (datetime.utcnow() - data_criacao)
                    > timedelta(seconds=_TIMEOUT_PENDENTE_SEGUNDOS)
                ):
                    msg_timeout = (
                        f"Worker Celery não iniciou a tarefa em "
                        f"{int(_TIMEOUT_PENDENTE_SEGUNDOS)}s. Verifique se o container "
                        f"do worker está em execução (docker compose ps)."
                    )
                    _atualizar_status_tarefa(tarefa_id, "FALHOU", erro=msg_timeout)
                    await websocket.send_json({"type": "error", "message": msg_timeout})
                    break

                # Metadados de progresso (JSON) armazenados em mensagem_erro.
                meta = {}
                if tarefa.mensagem_erro:
                    try:
                        meta = json.loads(tarefa.mensagem_erro)
                    except (json.JSONDecodeError, TypeError):
                        meta = {"mensagem_erro": tarefa.mensagem_erro}

                progresso_alterado = tarefa.progresso != ultimo_progresso
                deve_heartbeat = (agora - ultimo_heartbeat) >= _INTERVALO_HEARTBEAT_SEGUNDOS

                # Envia progresso sempre que mudar, ou um heartbeat periódico
                # para que o frontend saiba que a conexão está viva.
                if progresso_alterado or deve_heartbeat:
                    await websocket.send_json(
                        {
                            "type": "progress",
                            "data": {
                                "task_id": str(tarefa.id),
                                "progress": tarefa.progresso,
                                "status": tarefa.status,
                                "logs": tarefa.logs or "",
                                "heartbeat": not progresso_alterado,
                                **meta,
                            },
                        }
                    )
                    ultimo_progresso = tarefa.progresso
                    ultimo_heartbeat = agora

                if tarefa.status == "CONCLUIDO":
                    resultado = json.loads(tarefa.resultado_json) if tarefa.resultado_json else {}
                    await websocket.send_json(
                        {
                            "type": "result",
                            "data": resultado,
                        }
                    )
                    break
                elif tarefa.status in ("FALHOU", "CANCELADO"):
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": tarefa.mensagem_erro or "Tarefa falhou.",
                        }
                    )
                    break

    except WebSocketDisconnect:
        _logger.info("Cliente WebSocket desconectou.")
    except Exception as e:
        _logger.exception("Erro no WebSocket de otimização.")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
