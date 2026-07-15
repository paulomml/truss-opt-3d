"""
Endpoints REST da API TRUSS-OPT 3D.

Rotas:
- POST /api/otimizar          — inicia otimização assíncrona, retorna task_id
- GET  /api/tarefas/{id}      — consulta status/resultado por polling
- POST /api/tarefas/{id}/cancelar — cancela tarefa em andamento
- GET  /api/materiais         — lista materiais cadastrados
- GET  /api/perfis            — lista perfis cadastrados
- GET  /api/health            — health check
- WS   /api/ws/otimizar       — otimização com streaming WebSocket
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.schemas import (
    MaterialSchema,
    PerfilSchema,
    RequisicaoOtimizacao,
    RespostaOtimizacao,
    StatusTarefa,
)
from core.cache import gerar_chave_cache, obter_do_cache, salvar_no_cache
from core.database import obter_sessao
from core.celery_app import app_celery
from db.modelos import Material, Perfil, TarefaOtimizacao
from worker.tarefas import otimizar_trelice, _atualizar_status_tarefa
from api.memorial import gerar_memorial_pdf, gerar_memorial_docx, codificar_base64
from db.modelos import MemorialCalculo

_logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict:
    """Health check operacional."""
    return {"status": "ok", "servico": "TRUSS-OPT 3D API", "versao": "1.0.0"}


@router.get("/materiais", response_model=List[MaterialSchema])
async def listar_materiais(sessao: Session = Depends(obter_sessao)) -> List[Material]:
    """Lista todos os materiais estruturais ativos."""
    stmt = select(Material).where(Material.ativo.is_(True)).order_by(Material.nome)
    return list(sessao.scalars(stmt))


@router.get("/perfis", response_model=List[PerfilSchema])
async def listar_perfis(
    familia: str | None = None,
    sessao: Session = Depends(obter_sessao),
) -> List[Perfil]:
    """Lista perfis cadastrados, opcionalmente filtrados por família."""
    stmt = select(Perfil).where(Perfil.ativo.is_(True))
    if familia:
        stmt = stmt.where(Perfil.familia == familia)
    stmt = stmt.order_by(Perfil.familia, Perfil.nome)
    return list(sessao.scalars(stmt))


@router.post("/otimizar", response_model=StatusTarefa, status_code=status.HTTP_202_ACCEPTED)
async def iniciar_otimizacao(
    requisicao: RequisicaoOtimizacao,
    sessao: Session = Depends(obter_sessao),
) -> StatusTarefa:
    """
    Inicia uma otimização assíncrona via Celery.

    Retorna imediatamente com o ID da tarefa para polling subsequente.
    """
    # Verifica cache — se já existe resultado idêntico, retorna imediatamente.
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

    # Dispara a tarefa Celery.
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
        media_tipo = "application/pdf" if formato == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        return Response(
            content=conteudo,
            media_type=media_tipo,
            headers={
                "Content-Disposition": f'attachment; filename="{existente.nome_arquivo}"'
            },
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

    Fluxo:
    1. Cliente envia payload JSON.
    2. Servidor cria tarefa no banco e dispara Celery.
    3. Servidor faz polling do status e envia progresso ao cliente.
    4. Ao concluir, envia resultado final e fecha conexão.
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

        # Dispara Celery.
        otimizar_trelice.delay(tarefa_id, payload)

        # Polling de status até conclusão.
        ultimo_progresso = -1.0
        while True:
            await asyncio.sleep(1.5)
            with SessionLocal() as sessao:
                tarefa = sessao.get(TarefaOtimizacao, tarefa_id)
                if not tarefa:
                    await websocket.send_json({"type": "error", "message": "Tarefa não encontrada."})
                    break

                if tarefa.progresso != ultimo_progresso:
                    # Metadados de progresso (JSON) armazenados em mensagem_erro.
                    meta = {}
                    if tarefa.mensagem_erro:
                        try:
                            meta = json.loads(tarefa.mensagem_erro)
                        except (json.JSONDecodeError, TypeError):
                            meta = {"mensagem_erro": tarefa.mensagem_erro}

                    await websocket.send_json({
                        "type": "progress",
                        "data": {
                            "task_id": str(tarefa.id),
                            "progress": tarefa.progresso,
                            "status": tarefa.status,
                            "logs": tarefa.logs or "",
                            **meta,
                        },
                    })
                    ultimo_progresso = tarefa.progresso

                if tarefa.status == "CONCLUIDO":
                    resultado = json.loads(tarefa.resultado_json) if tarefa.resultado_json else {}
                    await websocket.send_json({
                        "type": "result",
                        "data": resultado,
                    })
                    break
                elif tarefa.status in ("FALHOU", "CANCELADO"):
                    await websocket.send_json({
                        "type": "error",
                        "message": tarefa.mensagem_erro or "Tarefa falhou.",
                    })
                    break

    except WebSocketDisconnect:
        _logger.info("Cliente WebSocket desconectou.")
    except Exception as e:
        _logger.exception("Erro no WebSocket de otimização.")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
