"""
Tarefas Celery para processamento assíncrono de otimização.

A tarefa `otimizar_trelice` recebe um payload JSON serializável, executa
o algoritmo genético e persiste o resultado no PostgreSQL. O frontend
pode acompanhar progresso via WebSocket ou polling na API de status.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from core.celery_app import app_celery
from core.database import SessionLocal
from core.memoria import CanceladorOtimizacao, verificar_memoria
from db.modelos import TarefaOtimizacao, Material, Perfil
from engineering.modelos_fisicos import (
    BarraFisica,
    NoFisico,
    material_dict_para_fisico,
    perfil_dict_para_fisico,
)
from engineering.standards.nbr_6123 import ParametrosVento
from optimization.algoritmo_genetico import otimizar_trelice_ga
from api.schemas import RespostaOtimizacao, BarraResultado, NoResultado

_logger = logging.getLogger(__name__)


def _atualizar_status_tarefa(
    tarefa_id: int,
    status: str,
    progresso: float = 0.0,
    mensagem: Optional[str] = None,
    resultado: Optional[dict] = None,
    erro: Optional[str] = None,
    logs: Optional[str] = None,
) -> None:
    """Atualiza o registro da tarefa no banco de dados."""
    with SessionLocal() as sessao:
        tarefa = sessao.get(TarefaOtimizacao, tarefa_id)
        if not tarefa:
            return
        tarefa.status = status
        tarefa.progresso = progresso
        if mensagem:
            tarefa.mensagem_erro = mensagem
        if resultado is not None:
            tarefa.resultado_json = json.dumps(resultado, default=str, ensure_ascii=False)
        if erro:
            tarefa.mensagem_erro = erro
        if logs is not None:
            tarefa.logs = logs
        if status == "EM_ANDAMENTO" and not tarefa.iniciado_em:
            tarefa.iniciado_em = datetime.utcnow()
        if status in ("CONCLUIDO", "FALHOU", "CANCELADO"):
            tarefa.finalizado_em = datetime.utcnow()
        sessao.commit()


@app_celery.task(bind=True, name="worker.tarefas.otimizar_trelice")
def otimizar_trelice(self, tarefa_id: int, payload: dict) -> dict:
    """
    Tarefa Celery principal — executa o GA e persiste o resultado.

    Args:
        tarefa_id: ID da tarefa no banco (tabela `tarefas_otimizacao`).
        payload: dicionário com `RequisicaoOtimizacao` (já validado).

    Returns:
        Dicionário com o resultado serializável (também persistido no banco).
    """
    inicio = time.time()
    _logger.info(f"Iniciando otimização para tarefa {tarefa_id}")
    _atualizar_status_tarefa(tarefa_id, "EM_ANDAMENTO", progresso=0.0)

    try:
        # Reconstrói o payload a partir do dict.
        raw_truss = payload.get("raw_truss")
        if not raw_truss:
            raise ValueError("Geometria da treliça (raw_truss) é obrigatória.")

        nos = {
            nid: NoFisico(
                id=n["id"],
                x=float(n["x"]),
                y=float(n["y"]),
                z=float(n["z"]),
                support=n.get("support", "None"),
            )
            for nid, n in raw_truss["nodes"].items()
        }
        barras = [
            BarraFisica(
                id=int(m["id"]),
                node_start=m["node_start"],
                node_end=m["node_end"],
                group=m.get("group", "Padrão"),
                length=_calcular_comprimento(nos[m["node_start"]], nos[m["node_end"]]),
            )
            for m in raw_truss["members"]
        ]
        grupos = list({b.group for b in barras if b.group}) or ["Padrão"]

        # Carrega materiais e perfis do banco (com restrições opcionais).
        with SessionLocal() as sessao:
            materiais_orm = list(sessao.scalars(
                select(Material).where(Material.ativo.is_(True))
            ))
            perfis_orm = list(sessao.scalars(
                select(Perfil).where(Perfil.ativo.is_(True))
            ))

        restricoes = payload.get("restricoes") or {}
        # Filtra materiais.
        if restricoes.get("materiais_permitidos"):
            nomes = set(restricoes["materiais_permitidos"])
            materiais_orm = [m for m in materiais_orm if m.nome in nomes]
        if not materiais_orm:
            raise ValueError("Nenhum material disponível com as restrições fornecidas.")

        materiais_fisicos = [material_dict_para_fisico(m.como_dicionario()) for m in materiais_orm]
        perfis_fisicos = [perfil_dict_para_fisico(p.como_dicionario()) for p in perfis_orm]

        # Parâmetros de vento (opcional).
        pv = payload.get("parametros_vento")
        parametros_vento = ParametrosVento(**pv) if pv else None

        # Casos de carga.
        casos_carga = payload.get("load_cases", [])

        # Identifica nós do banzo superior e fachadas.
        y_max = max((n.y for n in nos.values()), default=0.0)
        nos_banzo_superior = [nid for nid, n in nos.items() if abs(n.y - y_max) < 0.05]
        nos_fachada = [nid for nid, n in nos.items() if abs(n.y - 0.0) < 0.05]

        # Executa para cada material e escolhe o melhor (menor peso).
        melhor_resultado = None
        melhor_material_nome = None
        melhor_material_custo_kg = 8.5
        melhor_perfil_por_grupo = None
        melhor_logs: list[str] = []

        # Acumuladores de logs e melhor global (entre materiais).
        all_logs_acumulados: list[str] = []
        melhor_global_fitness = float("inf")
        melhor_global_material = ""
        total_materiais = len(materiais_fisicos)

        for idx, material in enumerate(materiais_fisicos):
            # Re-cria cancelador por material para isolar execuções.
            cancelador_mat = CanceladorOtimizacao()
            material_best = float("inf")

            # Callback de progresso (captura contexto do material via closure).
            def callback_progresso(geracao: int, total: int, min_fit: float, msg: str) -> None:
                nonlocal material_best, melhor_global_fitness, melhor_global_material

                # Progresso global considerando todos os materiais.
                overall_progress = ((idx + geracao / total) / total_materiais) * 100

                # Melhor fitness deste material até agora.
                if min_fit < material_best:
                    material_best = min_fit

                # Melhor fitness global entre todos os materiais processados.
                if material_best < melhor_global_fitness:
                    melhor_global_fitness = material_best
                    melhor_global_material = material.nome

                # Linha de log prefixada com o nome do material.
                linha_log = f"[{material.nome}] {msg}"
                all_logs_acumulados.append(linha_log)

                # Metadados estruturados para o WebSocket (codificados em mensagem_erro).
                meta = {
                    "material_atual": material.nome,
                    "indice_material": idx,
                    "total_materiais": total_materiais,
                    "geracao": geracao,
                    "total_geracoes": total,
                    "melhor_fitness": min_fit,
                    "melhor_do_material": material_best,
                    "melhor_global_fitness": melhor_global_fitness if melhor_global_fitness != float("inf") else None,
                    "melhor_global_material": melhor_global_material,
                    "materiais_nomes": [m.nome for m in materiais_fisicos],
                }

                _atualizar_status_tarefa(
                    tarefa_id,
                    "EM_ANDAMENTO",
                    progresso=min(overall_progress, 99.0),
                    logs="\n".join(all_logs_acumulados),
                    mensagem=json.dumps(meta, ensure_ascii=False),
                )

            resultado, perfil_por_grupo, logs = otimizar_trelice_ga(
                nos=nos,
                barras=barras,
                grupos=grupos,
                perfis_disponiveis=perfis_fisicos,
                material=material,
                casos_carga=casos_carga,
                nos_banzo_superior=nos_banzo_superior,
                nos_fachada=nos_fachada,
                parametros_vento=parametros_vento,
                water_lamina_mm=payload.get("water_lamina", 0.0),
                solo_tipo=payload.get("soil_type", "Rocha"),
                custom_ks=payload.get("custom_ks"),
                footing_b=payload.get("footing_b", 0.6),
                footing_l=payload.get("footing_l", 0.6),
                restricoes=restricoes,
                geracoes=payload.get("ag_geracoes"),
                tamanho_populacao=payload.get("ag_populacao"),
                cancelador=cancelador_mat,
                callback_progresso=callback_progresso,
                usar_refinamento_local=payload.get("ag_usar_refinamento_local"),
            )

            # Linha de resumo ao finalizar o material.
            if resultado.erro:
                linha_sumario = f"[{material.nome}] Falhou: {resultado.erro}"
            else:
                linha_sumario = f"[{material.nome}] Concluído. Custo: R$ {resultado.peso_total_kg * material.custo_kg:.2f} ({resultado.peso_total_kg:.1f} kg × R$ {material.custo_kg:.2f}/kg) | Utilização: {resultado.utilizacao_maxima*100:.1f}%"
            all_logs_acumulados.append(linha_sumario)
            _atualizar_status_tarefa(
                tarefa_id,
                "EM_ANDAMENTO",
                progresso=min(((idx + 1) / total_materiais) * 100, 99.0),
                logs="\n".join(all_logs_acumulados),
            )

            # Compara pelo custo total (peso × preço do material).
            custo_novo = resultado.peso_total_kg * material.custo_kg
            custo_atual = (
                melhor_resultado.peso_total_kg * melhor_material_custo_kg
                if melhor_resultado and not melhor_resultado.erro
                else float("inf")
            )
            if melhor_resultado is None or (not resultado.erro and custo_novo < custo_atual):
                melhor_resultado = resultado
                melhor_material_nome = material.nome
                melhor_material_custo_kg = material.custo_kg
                melhor_perfil_por_grupo = perfil_por_grupo
                melhor_logs = logs

        if melhor_resultado is None:
            raise RuntimeError("Nenhum material conseguiu produzir um resultado.")

        # Constrói resposta final.
        resposta = _construir_resposta(
            melhor_resultado,
            melhor_material_nome,
            melhor_material_custo_kg,
            melhor_perfil_por_grupo,
            melhor_logs,
            time.time() - inicio,
            len(set(p.nome for p in (melhor_perfil_por_grupo or {}).values())),
        )

        _atualizar_status_tarefa(
            tarefa_id,
            "CONCLUIDO",
            progresso=100.0,
            resultado=resposta,
            logs="\n".join(melhor_logs),
        )
        return resposta

    except Exception as e:
        _logger.exception(f"Erro na otimização da tarefa {tarefa_id}")
        _atualizar_status_tarefa(
            tarefa_id,
            "FALHOU",
            erro=str(e),
        )
        return {"erro": str(e), "task_id": tarefa_id}


def _calcular_comprimento(n1: NoFisico, n2: NoFisico) -> float:
    """Distância euclidiana 3D entre dois nós."""
    return ((n1.x - n2.x) ** 2 + (n1.y - n2.y) ** 2 + (n1.z - n2.z) ** 2) ** 0.5


def _construir_resposta(
    resultado,
    material_nome: str,
    material_custo_kg: float,
    perfil_por_grupo: Optional[dict],
    logs: list[str],
    tempo_execucao: float,
    num_perfis_distintos: int,
) -> dict:
    """Constrói o dict final no formato RespostaOtimizacao."""

    # Mapa barra → perfil (para preencher nome do material).
    barras_saida = []
    for b in resultado.barras:
        barras_saida.append({
            "id": b.id,
            "node_start": b.node_start,
            "node_end": b.node_end,
            "group": b.group,
            "profile": b.profile_name,
            "material": material_nome,
            "axial_force": b.axial_force,
            "my": b.my,
            "mz": b.mz,
            "utilization": b.utilization,
            "stress_type": b.stress_type,
            "n_rd": b.n_rd,
            "m_rd": b.m_rd,
            "esbeltez": b.esbeltez,
            "fator_chi": b.fator_chi,
            "fator_q": b.fator_q,
        })

    nos_saida = {
        nid: {
            "id": n.id,
            "x": n.x,
            "y": n.y,
            "z": n.z,
            "support": n.support,
            "deslocamento_y": resultado.deslocamentos.get(nid, (0, 0, 0))[1],
            "deslocamento_x": resultado.deslocamentos.get(nid, (0, 0, 0))[0],
            "deslocamento_z": resultado.deslocamentos.get(nid, (0, 0, 0))[2],
        }
        for nid, n in resultado.nos.items()
    }

    return {
        "is_structurally_stable": not resultado.erro and resultado.utilizacao_maxima <= 1.0,
        "status_message": resultado.erro or (
            f"Otimização concluída com material {material_nome} "
            f"(R$ {material_custo_kg:.2f}/kg). "
            f"Utilização máxima: {resultado.utilizacao_maxima*100:.1f}%."
        ),
        "total_weight": resultado.peso_total_kg,
        "total_cost": resultado.peso_total_kg * material_custo_kg,
        "winning_material": material_nome,
        "precamber": resultado.contraflecha,
        "max_deflection": resultado.flecha_maxima,
        "real_span": resultado.vano_real,
        "max_utilization": resultado.utilizacao_maxima,
        "num_perfis_distintos": num_perfis_distintos,
        "geracoes_executadas": len(logs),
        "tempo_execucao_segundos": tempo_execucao,
        "members": barras_saida,
        "nodes": nos_saida,
        "logs": logs,
    }
