"""
Tarefas Celery para otimização assíncrona de treliças.
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime

from sqlalchemy import select

from core.celery_app import app_celery
from core.database import SessionLocal
from core.memoria import CanceladorOtimizacao
from db.modelos import Material, Perfil, TarefaOtimizacao
from engineering.fea.pynite_solver import ModeloBaseFEA
from engineering.modelos_fisicos import (
    BarraFisica,
    MaterialFisico,
    NoFisico,
    PerfilFisico,
    ResultadoAnalise,
    material_dict_para_fisico,
    perfil_dict_para_fisico,
)
from engineering.standards.nbr_6123 import ParametrosVento
from optimization.algoritmo_genetico import otimizar_trelice_ga

_logger = logging.getLogger(__name__)


def _atualizar_status_tarefa(
    tarefa_id: int,
    status: str,
    progresso: float = 0.0,
    mensagem: str | None = None,
    resultado: dict | None = None,
    erro: str | None = None,
    logs: str | None = None,
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
    Tarefa Celery principal: executa o GA e persiste o resultado.

    Args:
        tarefa_id: ID da tarefa no banco (tabela tarefas_otimizacao).
        payload: dicionário com RequisicaoOtimizacao (já validado).

    Returns:
        Dicionário com o resultado serializável (também persistido no banco).
    """
    inicio = time.time()
    _logger.info(f"Iniciando otimização para tarefa {tarefa_id}")
    _atualizar_status_tarefa(
        tarefa_id, "EM_ANDAMENTO", progresso=0.0, logs="Inicializando análise estrutural..."
    )

    # Semente fixa para reprodutibilidade (afeta todo o processo).
    semente = payload.get("ag_semente")
    if semente and semente > 0:
        random.seed(semente)

    try:
        # Reconstrói o payload a partir do dict.
        raw_truss = payload.get("raw_truss")
        if not raw_truss:
            raise ValueError("Geometria da treliça (raw_truss) é obrigatória.")

        nos = _construir_nos(raw_truss)
        barras = _construir_barras(raw_truss, nos)
        grupos = list({b.group for b in barras if b.group}) or ["Padrão"]

        # Carrega materiais e perfis do banco (com restrições opcionais).
        with SessionLocal() as sessao:
            materiais_orm = list(sessao.scalars(select(Material).where(Material.ativo.is_(True))))
            perfis_orm = list(sessao.scalars(select(Perfil).where(Perfil.ativo.is_(True))))

        restricoes = payload.get("restricoes") or {}
        # Filtra materiais.
        if restricoes.get("materiais_permitidos"):
            nomes = set(restricoes["materiais_permitidos"])
            materiais_orm = [m for m in materiais_orm if m.nome in nomes]
        if not materiais_orm:
            raise ValueError("Nenhum material disponível com as restrições fornecidas.")

        materiais_fisicos = [material_dict_para_fisico(m.como_dicionario()) for m in materiais_orm]
        perfis_fisicos = [perfil_dict_para_fisico(p.como_dicionario()) for p in perfis_orm]

        _atualizar_status_tarefa(
            tarefa_id,
            "EM_ANDAMENTO",
            progresso=0.0,
            logs=f"Materiais carregados: {len(materiais_fisicos)} materiais, {len(perfis_fisicos)} perfis disponíveis.",
        )

        # Parâmetros de vento (opcional).
        pv = payload.get("parametros_vento")
        parametros_vento = ParametrosVento(**pv) if pv else None

        # Casos de carga.
        casos_carga = payload.get("load_cases", [])

        # Identifica nós do banzo superior e fachadas.
        y_max = max((n.y for n in nos.values()), default=0.0)
        nos_banzo_superior = [nid for nid, n in nos.items() if abs(n.y - y_max) < 0.05]
        nos_fachada = [nid for nid, n in nos.items() if abs(n.y - 0.0) < 0.05]

        # Paralelismo: min(len(materiais), cpu_count, n_parallel do payload).
        n_parallel_solicitado = int(payload.get("n_parallel") or 1)
        n_parallel_solicitado = max(1, n_parallel_solicitado)
        cpu_count = os.cpu_count() or 1
        n_parallel = max(1, min(n_parallel_solicitado, len(materiais_fisicos), cpu_count))
        _logger.info(
            f"Tarefa {tarefa_id}: n_parallel solicitado={n_parallel_solicitado}, "
            f"efetivo={n_parallel} (materiais={len(materiais_fisicos)}, cpu={cpu_count})."
        )

        # Envia metadados dos materiais para o frontend sair do estado
        # "Aguardando dados do servidor" e exibir a lista de materiais.
        nomes_materiais = [m.nome for m in materiais_fisicos]
        _atualizar_status_tarefa(
            tarefa_id,
            "EM_ANDAMENTO",
            progresso=0.0,
            logs=f"Carregados {len(materiais_fisicos)} materiais. Iniciando processamento...",
            mensagem=json.dumps(
                {
                    "material_atual": "(preparando GA)",
                    "indice_material": 0,
                    "total_materiais": len(materiais_fisicos),
                    "melhor_global_fitness": None,
                    "melhor_global_material": "",
                    "materiais_nomes": nomes_materiais,
                    "n_parallel": n_parallel,
                    "paralelo": n_parallel > 1,
                },
                ensure_ascii=False,
            ),
        )

        # Monta argumentos serializáveis para cada subprocesso.
        nos_dicts = {
            nid: {
                "id": n.id,
                "x": n.x,
                "y": n.y,
                "z": n.z,
                "support": n.support,
            }
            for nid, n in nos.items()
        }
        barras_dicts = [
            {
                "id": b.id,
                "node_start": b.node_start,
                "node_end": b.node_end,
                "group": b.group,
                "length": b.length,
            }
            for b in barras
        ]
        perfis_dicts = [p.__dict__ for p in perfis_fisicos]
        parametros_vento_dict = pv  # já é dict puro do payload.

        args_lista = [
            (
                m.__dict__,  # material_dict
                perfis_dicts,
                payload,
                nos_dicts,
                barras_dicts,
                grupos,
                parametros_vento_dict,
                casos_carga,
                nos_banzo_superior,
                nos_fachada,
                idx,
                len(materiais_fisicos),
            )
            for idx, m in enumerate(materiais_fisicos)
        ]

        # Execução: paralela ou sequencial.
        if n_parallel > 1:
            resultados_por_material = _executar_materiais_paralelo(
                tarefa_id, args_lista, materiais_fisicos, n_parallel
            )
        else:
            resultados_por_material = _executar_materiais_sequencial(
                tarefa_id, args_lista, materiais_fisicos
            )

        # Escolhe o melhor material (menor custo total = peso * preço).
        melhor = _selecionar_melhor_material(resultados_por_material)
        if melhor is None:
            raise RuntimeError("Nenhum material conseguiu produzir um resultado.")

        # Constrói resposta final a partir do dict serializado do material vencedor.
        resposta = _construir_resposta(
            melhor,
            melhor["material_nome"],
            melhor["material_custo_kg"],
            melhor.get("perfil_por_grupo"),
            melhor.get("logs", []),
            time.time() - inicio,
            len(set(p["nome"] for p in (melhor.get("perfil_por_grupo") or {}).values())),
        )

        _atualizar_status_tarefa(
            tarefa_id,
            "CONCLUIDO",
            progresso=100.0,
            resultado=resposta,
            logs="\n".join(melhor.get("logs", [])),
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


# Funções auxiliares: construção de objetos a partir do payload.


def _construir_nos(raw_truss: dict) -> dict[str, NoFisico]:
    """Reconstrói o dicionário de nós a partir do raw_truss do payload."""
    return {
        nid: NoFisico(
            id=n["id"],
            x=float(n["x"]),
            y=float(n["y"]),
            z=float(n["z"]),
            support=n.get("support", "None"),
        )
        for nid, n in raw_truss["nodes"].items()
    }


def _construir_barras(raw_truss: dict, nos: dict[str, NoFisico]) -> list[BarraFisica]:
    """Reconstrói a lista de barras a partir do raw_truss do payload."""
    return [
        BarraFisica(
            id=int(m["id"]),
            node_start=m["node_start"],
            node_end=m["node_end"],
            group=m.get("group", "Padrão"),
            length=_calcular_comprimento(nos[m["node_start"]], nos[m["node_end"]]),
        )
        for m in raw_truss["members"]
    ]


# Funções auxiliares: execução paralela e sequencial dos materiais.


def _executar_materiais_paralelo(
    tarefa_id: int,
    args_lista: list[tuple],
    materiais_fisicos: list[MaterialFisico],
    n_parallel: int,
) -> list[dict]:
    """
    Executa o GA para cada material em paralelo (ProcessPoolExecutor).
    """
    nomes_materiais = [m.nome for m in materiais_fisicos]
    total_materiais = len(materiais_fisicos)
    all_logs_acumulados: list[str] = []
    melhor_global_fitness = float("inf")
    melhor_global_material = ""
    concluidos = 0
    resultados: list[dict] = [None] * total_materiais  # type: ignore[list-item]

    # Mensagem inicial informativa sobre paralelismo.
    all_logs_acumulados.append(
        f"Iniciando processamento paralelo: {total_materiais} materiais em "
        f"{n_parallel} workers simultâneos."
    )
    _atualizar_status_tarefa(
        tarefa_id,
        "EM_ANDAMENTO",
        progresso=0.0,
        logs="\n".join(all_logs_acumulados),
        mensagem=json.dumps(
            {
                "material_atual": "(iniciando paralelo)",
                "indice_material": 0,
                "total_materiais": total_materiais,
                "melhor_global_fitness": None,
                "melhor_global_material": "",
                "materiais_nomes": nomes_materiais,
                "n_parallel": n_parallel,
                "paralelo": True,
            },
            ensure_ascii=False,
        ),
    )

    with ProcessPoolExecutor(max_workers=n_parallel) as executor:
        # Submete todos os materiais ao pool.
        future_to_idx = {
            executor.submit(_executar_ga_material_subprocesso, args): args[10]
            for args in args_lista
        }

        # Processa resultados conforme ficam prontos.
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            nome_mat = nomes_materiais[idx]
            try:
                resultado_dict = future.result()
                resultados[idx] = resultado_dict
                concluidos += 1

                # Atualiza melhor global (custo total, não fitness bruto).
                custo_mat = resultado_dict.get("custo_total", float("inf"))
                if custo_mat < melhor_global_fitness:
                    melhor_global_fitness = custo_mat
                    melhor_global_material = nome_mat

                # Acumula logs deste material.
                all_logs_acumulados.extend(resultado_dict.get("logs", []))

                # Progresso global: concluidos / total.
                progresso = (concluidos / total_materiais) * 100
                meta = {
                    "material_atual": nome_mat,
                    "indice_material": concluidos,
                    "total_materiais": total_materiais,
                    "melhor_global_fitness": melhor_global_fitness
                    if melhor_global_fitness != float("inf")
                    else None,
                    "melhor_global_material": melhor_global_material,
                    "materiais_nomes": nomes_materiais,
                    "n_parallel": n_parallel,
                    "paralelo": True,
                    "concluidos": concluidos,
                }
                _atualizar_status_tarefa(
                    tarefa_id,
                    "EM_ANDAMENTO",
                    progresso=min(progresso, 99.0),
                    logs="\n".join(all_logs_acumulados),
                    mensagem=json.dumps(meta, ensure_ascii=False),
                )
            except Exception as e:
                _logger.exception(
                    f"Erro no subprocesso do material {nome_mat} (tarefa {tarefa_id})."
                )
                all_logs_acumulados.append(f"[{nome_mat}] Falhou no subprocesso: {e}")
                # Mesmo em falha, marca como concluído para fins de progresso.
                concluidos += 1

    # Filtra None (materiais que falharam no subprocesso).
    return [r for r in resultados if r is not None]


def _executar_materiais_sequencial(
    tarefa_id: int,
    args_lista: list[tuple],
    materiais_fisicos: list[MaterialFisico],
) -> list[dict]:
    """
    Executa o GA sequencialmente para cada material.
    """
    total_materiais = len(materiais_fisicos)
    nomes_materiais = [m.nome for m in materiais_fisicos]
    all_logs_acumulados: list[str] = []
    melhor_global_fitness = float("inf")
    melhor_global_material = ""
    resultados: list[dict] = []

    for idx, args in enumerate(args_lista):
        material_dict = args[0]
        material_nome = material_dict["nome"]
        material_custo_kg = material_dict["custo_kg"]

        # Re-cria cancelador por material para isolar execuções.
        cancelador_mat = CanceladorOtimizacao()
        material_best = float("inf")

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
                melhor_global_material = material_nome

            # Linha de log prefixada com o nome do material.
            linha_log = f"[{material_nome}] {msg}"
            all_logs_acumulados.append(linha_log)

            # Metadados estruturados para o WebSocket (codificados em mensagem_erro).
            meta = {
                "material_atual": material_nome,
                "indice_material": idx,
                "total_materiais": total_materiais,
                "geracao": geracao,
                "total_geracoes": total,
                "melhor_fitness": min_fit,
                "melhor_do_material": material_best,
                "melhor_global_fitness": melhor_global_fitness
                if melhor_global_fitness != float("inf")
                else None,
                "melhor_global_material": melhor_global_material,
                "materiais_nomes": nomes_materiais,
                "n_parallel": 1,
                "paralelo": False,
            }

            _atualizar_status_tarefa(
                tarefa_id,
                "EM_ANDAMENTO",
                progresso=min(overall_progress, 99.0),
                logs="\n".join(all_logs_acumulados),
                mensagem=json.dumps(meta, ensure_ascii=False),
            )

        # Informa qual material será processado ANTES de iniciar o GA,
        # dando feedback imediato ao usuário.
        all_logs_acumulados.append(f"[{material_nome}] Preparando modelo MEF...")
        _atualizar_status_tarefa(
            tarefa_id,
            "EM_ANDAMENTO",
            progresso=min((idx / total_materiais) * 100, 99.0),
            logs="\n".join(all_logs_acumulados),
        )

        meta_pre_ga = {
            "material_atual": material_nome,
            "indice_material": idx,
            "total_materiais": total_materiais,
            "geracao": 0,
            "total_geracoes": 0,
            "melhor_fitness": None,
            "melhor_do_material": None,
            "melhor_global_fitness": melhor_global_fitness
            if melhor_global_fitness != float("inf")
            else None,
            "melhor_global_material": melhor_global_material,
            "materiais_nomes": nomes_materiais,
            "n_parallel": 1,
            "paralelo": False,
        }
        all_logs_acumulados.append(f"[{material_nome}] Iniciando avaliação estrutural...")
        _atualizar_status_tarefa(
            tarefa_id,
            "EM_ANDAMENTO",
            progresso=min((idx / total_materiais) * 100, 99.0),
            logs="\n".join(all_logs_acumulados),
            mensagem=json.dumps(meta_pre_ga, ensure_ascii=False),
        )

        # Executa o GA no processo atual (sem subprocesso).
        resultado_dict = _executar_ga_material_inprocess(
            args, callback_progresso, cancelador_mat, tarefa_id
        )

        if resultado_dict.get("erro"):
            linha_sumario = f"[{material_nome}] Falhou: {resultado_dict['erro']}"
        else:
            linha_sumario = (
                f"[{material_nome}] Concluído. Custo: R$ {resultado_dict['custo_total']:.2f} "
                f"({resultado_dict['peso_total_kg']:.1f} kg x R$ {material_custo_kg:.2f}/kg) | "
                f"Utilização: {resultado_dict['utilizacao_maxima'] * 100:.1f}%"
            )
        all_logs_acumulados.append(linha_sumario)
        _atualizar_status_tarefa(
            tarefa_id,
            "EM_ANDAMENTO",
            progresso=min(((idx + 1) / total_materiais) * 100, 99.0),
            logs="\n".join(all_logs_acumulados),
        )

        resultados.append(resultado_dict)

    return resultados


def _executar_ga_material_inprocess(
    args: tuple,
    callback_progresso,
    cancelador: CanceladorOtimizacao,
    tarefa_id: int,
) -> dict:
    """
    Executa o GA para um material no processo atual.
    """
    (
        material_dict,
        perfis_dicts,
        payload,
        nos_dicts,
        barras_dicts,
        grupos,
        parametros_vento_dict,
        casos_carga,
        nos_banzo_superior,
        nos_fachada,
        idx,
        total_materiais,
    ) = args

    material = material_dict_para_fisico(material_dict)
    perfis = [perfil_dict_para_fisico(p) for p in perfis_dicts]
    nos = {
        nid: NoFisico(
            id=n["id"],
            x=float(n["x"]),
            y=float(n["y"]),
            z=float(n["z"]),
            support=n.get("support", "None"),
        )
        for nid, n in nos_dicts.items()
    }
    barras = [
        BarraFisica(
            id=int(b["id"]),
            node_start=b["node_start"],
            node_end=b["node_end"],
            group=b.get("group", "Padrão"),
            length=float(b["length"]),
        )
        for b in barras_dicts
    ]
    parametros_vento = ParametrosVento(**parametros_vento_dict) if parametros_vento_dict else None

    restricoes = payload.get("restricoes") or {}

    # Constrói modelo base reutilizável (geometria, cargas invariantes,
    # combinações) para evitar recriar o modelo MEF a cada avaliação.
    modelo_base = ModeloBaseFEA(
        nos=nos,
        barras=barras,
        material=material,
        casos_carga_externos=casos_carga,
        parametros_vento=parametros_vento,
        nos_banzo_superior=nos_banzo_superior,
        nos_fachada=nos_fachada,
        water_lamina_mm=payload.get("water_lamina", 0.0),
        solo_tipo=payload.get("soil_type", "Rocha"),
        custom_ks=payload.get("custom_ks"),
        footing_b=payload.get("footing_b", 0.6),
        footing_l=payload.get("footing_l", 0.6),
        perfis_disponiveis=perfis,
    )

    resultado, perfil_por_grupo, logs, logbook_dicts, parametros_usados = otimizar_trelice_ga(
        nos=nos,
        barras=barras,
        grupos=grupos,
        perfis_disponiveis=perfis,
        material=material,
        casos_carga=casos_carga,
        nos_banzo_superior=nos_banzo_superior,
        nos_fachada=nos_fachada,
        parametros_vento=parametros_vento,
        modelo_base=modelo_base,
        water_lamina_mm=payload.get("water_lamina", 0.0),
        solo_tipo=payload.get("soil_type", "Rocha"),
        custom_ks=payload.get("custom_ks"),
        footing_b=payload.get("footing_b", 0.6),
        footing_l=payload.get("footing_l", 0.6),
        restricoes=restricoes,
        geracoes=payload.get("ag_geracoes"),
        tamanho_populacao=payload.get("ag_populacao"),
        cancelador=cancelador,
        callback_progresso=callback_progresso,
        usar_refinamento_local=payload.get("ag_usar_refinamento_local"),
        probabilidade_cruzamento=payload.get("ag_probabilidade_cruzamento"),
        probabilidade_mutacao=payload.get("ag_probabilidade_mutacao"),
        indice_torneio=payload.get("ag_indice_torneio"),
        max_perfis_distintos=payload.get("ag_max_perfis_distintos"),
        modo_rapido=payload.get("modo_rapido", True),
        usar_paralelismo=payload.get("usar_paralelismo", True),
        semente=payload.get("ag_semente"),
    )

    # Serializa o resultado e o perfil_por_grupo para dict puro.
    return _serializar_resultado_material(
        resultado, perfil_por_grupo, logs, material, idx,
        logbook_dicts=logbook_dicts, parametros_usados=parametros_usados,
    )


def _executar_ga_material_subprocesso(args: tuple) -> dict:
    """
    Executa o GA para um material em subprocesso (picklable).
    """
    (
        material_dict,
        perfis_dicts,
        payload,
        nos_dicts,
        barras_dicts,
        grupos,
        parametros_vento_dict,
        casos_carga,
        nos_banzo_superior,
        nos_fachada,
        idx,
        total_materiais,
    ) = args

    # Aplica a semente no subprocesso (ProcessPoolExecutor não herda a seed do processo pai).
    semente = payload.get("ag_semente")
    if semente and semente > 0:
        random.seed(semente + idx)

    material = material_dict_para_fisico(material_dict)
    perfis = [perfil_dict_para_fisico(p) for p in perfis_dicts]
    nos = {
        nid: NoFisico(
            id=n["id"],
            x=float(n["x"]),
            y=float(n["y"]),
            z=float(n["z"]),
            support=n.get("support", "None"),
        )
        for nid, n in nos_dicts.items()
    }
    barras = [
        BarraFisica(
            id=int(b["id"]),
            node_start=b["node_start"],
            node_end=b["node_end"],
            group=b.get("group", "Padrão"),
            length=float(b["length"]),
        )
        for b in barras_dicts
    ]
    parametros_vento = ParametrosVento(**parametros_vento_dict) if parametros_vento_dict else None

    restricoes = payload.get("restricoes") or {}
    cancelador = CanceladorOtimizacao()  # Cada subprocesso tem o seu.

    # Constrói modelo base reutilizável para acelerar o GA no subprocesso.
    modelo_base = ModeloBaseFEA(
        nos=nos,
        barras=barras,
        material=material,
        casos_carga_externos=casos_carga,
        parametros_vento=parametros_vento,
        nos_banzo_superior=nos_banzo_superior,
        nos_fachada=nos_fachada,
        water_lamina_mm=payload.get("water_lamina", 0.0),
        solo_tipo=payload.get("soil_type", "Rocha"),
        custom_ks=payload.get("custom_ks"),
        footing_b=payload.get("footing_b", 0.6),
        footing_l=payload.get("footing_l", 0.6),
        perfis_disponiveis=perfis,
    )

    logs_locais: list[str] = []
    melhor_fitness_local = float("inf")

    def callback_local(geracao: int, total: int, min_fit: float, msg: str) -> None:
        nonlocal melhor_fitness_local
        logs_locais.append(f"[{material.nome}] {msg}")
        if min_fit < melhor_fitness_local:
            melhor_fitness_local = min_fit

    resultado, perfil_por_grupo, logs, logbook_dicts, parametros_usados = otimizar_trelice_ga(
        nos=nos,
        barras=barras,
        grupos=grupos,
        perfis_disponiveis=perfis,
        material=material,
        casos_carga=casos_carga,
        nos_banzo_superior=nos_banzo_superior,
        nos_fachada=nos_fachada,
        parametros_vento=parametros_vento,
        modelo_base=modelo_base,
        water_lamina_mm=payload.get("water_lamina", 0.0),
        solo_tipo=payload.get("soil_type", "Rocha"),
        custom_ks=payload.get("custom_ks"),
        footing_b=payload.get("footing_b", 0.6),
        footing_l=payload.get("footing_l", 0.6),
        restricoes=restricoes,
        geracoes=payload.get("ag_geracoes"),
        tamanho_populacao=payload.get("ag_populacao"),
        cancelador=cancelador,
        callback_progresso=callback_local,
        usar_refinamento_local=payload.get("ag_usar_refinamento_local"),
        probabilidade_cruzamento=payload.get("ag_probabilidade_cruzamento"),
        probabilidade_mutacao=payload.get("ag_probabilidade_mutacao"),
        indice_torneio=payload.get("ag_indice_torneio"),
        max_perfis_distintos=payload.get("ag_max_perfis_distintos"),
        modo_rapido=payload.get("modo_rapido", True),
        usar_paralelismo=payload.get("usar_paralelismo", True),
        semente=payload.get("ag_semente"),
    )

    # Junta logs locais (callback) com logs retornados pelo GA.
    logs_completos = logs_locais + logs

    return _serializar_resultado_material(
        resultado, perfil_por_grupo, logs_completos, material, idx,
        logbook_dicts=logbook_dicts, parametros_usados=parametros_usados,
    )


def _serializar_resultado_material(
    resultado: ResultadoAnalise,
    perfil_por_grupo: dict | None,
    logs: list[str],
    material: MaterialFisico,
    idx: int,
    logbook_dicts: list[dict] | None = None,
    parametros_usados: dict | None = None,
) -> dict:
    """Converte o resultado do GA em um dict puro (serializável JSON/pickle)."""
    return {
        "material_nome": material.nome,
        "material_custo_kg": material.custo_kg,
        "idx": idx,
        "peso_total_kg": resultado.peso_total_kg,
        "flecha_maxima": resultado.flecha_maxima,
        "utilizacao_maxima": resultado.utilizacao_maxima,
        "vano_real": resultado.vano_real,
        "erro": resultado.erro,
        "contraflecha": resultado.contraflecha,
        "custo_total": resultado.peso_total_kg * material.custo_kg,
        "barras": [
            {
                "id": b.id,
                "node_start": b.node_start,
                "node_end": b.node_end,
                "group": b.group,
                "profile_name": b.profile_name,
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
                "length": b.length,
                "lkx": b.lkx,
                "lky": b.lky,
                "lambda_0": b.lambda_0,
                "detalhes": b.detalhes,
                "violacao_normativa": b.violacao_normativa,
                "peso_kg": b.peso_kg,
            }
            for b in resultado.barras
        ],
        "nos": {
            nid: {
                "id": n.id,
                "x": n.x,
                "y": n.y,
                "z": n.z,
                "support": n.support,
                "deslocamentos": resultado.deslocamentos.get(nid, (0.0, 0.0, 0.0)),
            }
            for nid, n in resultado.nos.items()
        },
        "perfil_por_grupo": {g: p.__dict__ for g, p in (perfil_por_grupo or {}).items()},
        "logs": logs,
        "dados_extras": resultado.dados_extras,
        "ga_logbook": logbook_dicts or [],
        "ga_parametros": parametros_usados or {},
        "ga_fitness_final": (parametros_usados or {}).get("fitness_final", 0.0),
    }


def _selecionar_melhor_material(resultados: list[dict]) -> dict | None:
    """Seleciona o material mais estável e mais barato.

    Critérios: 1) estabilidade (utilização <= 100%); 2) menor custo total.
    Se nenhum for estável, retorna None (tarefa FALHOU).
    """
    melhor: dict | None = None
    melhor_custo = float("inf")
    for r in resultados:
        if r.get("erro"):
            continue
        # Ignora materiais que produzem estrutura instável.
        if r.get("utilizacao_maxima", 0) > 1.0:
            continue
        custo = r.get("custo_total", float("inf"))
        if custo < melhor_custo:
            melhor_custo = custo
            melhor = r
    return melhor


def _calcular_comprimento(n1: NoFisico, n2: NoFisico) -> float:
    """Distância euclidiana 3D entre dois nós."""
    return ((n1.x - n2.x) ** 2 + (n1.y - n2.y) ** 2 + (n1.z - n2.z) ** 2) ** 0.5


def _extrair_perfis_usados(perfil_por_grupo_dicts: dict | None) -> dict[str, dict]:
    """Extrai metadados dos perfis usados para o memorial (BOM)."""
    if not perfil_por_grupo_dicts:
        return {}
    saida: dict[str, dict] = {}
    for grupo, p in perfil_por_grupo_dicts.items():
        nome = p.get("nome", p.get("Name", "?"))
        saida[nome] = {
            "nome": nome,
            "grupo": grupo,
            "familia": p.get("familia", ""),
            "h_mm": p.get("h_mm", 0.0),
            "bf_mm": p.get("bf_mm", 0.0),
            "t_mm": p.get("t_mm", 0.0),
            "area_m2": p.get("area_m2", 0.0),
            "ix_m4": p.get("ix_m4", 0.0),
            "iy_m4": p.get("iy_m4", 0.0),
            "j_m4": p.get("j_m4", 0.0),
            "uso_recomendado": p.get("uso_recomendado", ""),
            "chapa_referencia": p.get("chapa_referencia", ""),
            "raio_giracao_x": (p.get("ix_m4", 0.0) / max(p.get("area_m2", 1e-12), 1e-12)) ** 0.5,
            "raio_giracao_y": (p.get("iy_m4", 0.0) / max(p.get("area_m2", 1e-12), 1e-12)) ** 0.5,
        }
    return saida


def _construir_resposta(
    resultado_dict: dict,
    material_nome: str,
    material_custo_kg: float,
    perfil_por_grupo_dicts: dict | None,
    logs: list[str],
    tempo_execucao: float,
    num_perfis_distintos: int,
) -> dict:
    """
    Constrói o dict final no formato RespostaOtimizacao.

    Diferente da versão anterior, recebe dicts serializáveis (não mais
    dataclasses) para suportar tanto o caminho paralelo quanto o sequencial.
    """
    # Mapa barra -> perfil (para preencher nome do material).
    barras_saida = []
    for b in resultado_dict["barras"]:
        barras_saida.append(
            {
                "id": b["id"],
                "node_start": b["node_start"],
                "node_end": b["node_end"],
                "group": b["group"],
                "profile": b["profile_name"],
                "material": material_nome,
                "axial_force": b["axial_force"],
                "my": b["my"],
                "mz": b["mz"],
                "utilization": b["utilization"],
                "stress_type": b["stress_type"],
                "n_rd": b["n_rd"],
                "m_rd": b["m_rd"],
                "esbeltez": b["esbeltez"],
                "fator_chi": b["fator_chi"],
                "fator_q": b["fator_q"],
                "length": b.get("length", 0.0),
                "lkx": b.get("lkx", 0.0),
                "lky": b.get("lky", 0.0),
                "lambda_0": b.get("lambda_0", 0.0),
                "detalhes": b.get("detalhes", ""),
                "violacao_normativa": b.get("violacao_normativa", False),
                "peso_kg": b.get("peso_kg", 0.0),
            }
        )

    nos_saida = {
        nid: {
            "id": n["id"],
            "x": n["x"],
            "y": n["y"],
            "z": n["z"],
            "support": n["support"],
            "deslocamento_y": n["deslocamentos"][1] if len(n["deslocamentos"]) > 1 else 0.0,
            "deslocamento_x": n["deslocamentos"][0] if len(n["deslocamentos"]) > 0 else 0.0,
            "deslocamento_z": n["deslocamentos"][2] if len(n["deslocamentos"]) > 2 else 0.0,
        }
        for nid, n in resultado_dict["nos"].items()
    }

    return {
        "is_structurally_stable": not resultado_dict["erro"]
        and resultado_dict["utilizacao_maxima"] <= 1.0,
        "status_message": resultado_dict["erro"]
        or (
            f"Otimização concluída com material {material_nome} "
            f"(R$ {material_custo_kg:.2f}/kg). "
            f"Utilização máxima: {resultado_dict['utilizacao_maxima'] * 100:.1f}%."
        ),
        "total_weight": resultado_dict["peso_total_kg"],
        "total_cost": resultado_dict["peso_total_kg"] * material_custo_kg,
        "winning_material": material_nome,
        "precamber": resultado_dict["contraflecha"],
        "max_deflection": resultado_dict["flecha_maxima"],
        "real_span": resultado_dict["vano_real"],
        "max_utilization": resultado_dict["utilizacao_maxima"],
        "num_perfis_distintos": num_perfis_distintos,
        "geracoes_executadas": len(logs),
        "tempo_execucao_segundos": tempo_execucao,
        "members": barras_saida,
        "nodes": nos_saida,
        "logs": logs,
        # Dados extras
        "fundacao": resultado_dict.get("dados_extras", {}).get("ise", {}),
        "vento": resultado_dict.get("dados_extras", {}).get("vento", {}),
        "ga_parametros": resultado_dict.get("ga_parametros", {}),
        "ga_logbook": resultado_dict.get("ga_logbook", []),
        "ga_fitness_final": resultado_dict.get("ga_fitness_final", 0.0),
        "perfis_usados": _extrair_perfis_usados(resultado_dict.get("perfil_por_grupo", {})),
        "material_vencedor": {
            "nome": material_nome,
            "custo_kg": material_custo_kg,
        },
    }
