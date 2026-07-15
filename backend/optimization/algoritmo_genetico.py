"""
Motor de Otimização — Algoritmo Genético Memético (DEAP + Hill Climbing).

Combina:
- GA (exploração global): crossover, mutação, seleção por torneio.
- Busca local (refinamento): hill climbing first-improvement nos melhores
  indivíduos a cada geração (aprendizagem Lamarckiana).

Indivíduo: vetor de inteiros (índices no catálogo de perfis), um por grupo.
Fitness: peso_total_kg × custo_kg_material + penalidades (minimiza R$).
Penalidades: violação NBR 8800/6120/6123, flecha ELS, diversidade de perfis.
"""
from __future__ import annotations

import logging
import math
import random
import time
from typing import Callable, Dict, List, Optional, Tuple

from deap import algorithms, base, creator, tools
from sqlalchemy.orm import Session

from core.config import configuracoes
from core.memoria import CanceladorOtimizacao, verificar_memoria
from engineering.fea.pynite_solver import construir_e_resolver
from engineering.modelos_fisicos import (
    BarraFisica,
    MaterialFisico,
    NoFisico,
    PerfilFisico,
    ResultadoAnalise,
    perfil_dict_para_fisico,
)
from engineering.standards.nbr_6123 import ParametrosVento
from engineering.standards.nbr_8800 import verificar_flecha_els

_logger = logging.getLogger(__name__)


# ----------------------------------------------------------------
# Garantia de criação única das classes DEAP (evita erros em reloads).
# ----------------------------------------------------------------
_FITNESS_CRIADO = False


def _garantiar_classes_deap() -> None:
    """Cria as classes FitnessMin e Individual no creator (idempotente)."""
    global _FITNESS_CRIADO
    if _FITNESS_CRIADO:
        return
    if not hasattr(creator, "FitnessMin"):
        creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
    if not hasattr(creator, "Individual"):
        creator.create("Individual", list, fitness=creator.FitnessMin)
    _FITNESS_CRIADO = True


def _filtrar_perfis(
    perfis_disponiveis: List[PerfilFisico],
    restricoes: Optional[dict],
) -> List[PerfilFisico]:
    """Aplica restrições do usuário ao espaço de busca."""
    if not restricoes:
        return perfis_disponiveis
    perfis = perfis_disponiveis
    if restricoes.get("familias_permitidas"):
        perfis = [p for p in perfis if p.familia in restricoes["familias_permitidas"]]
    if restricoes.get("perfis_permitidos"):
        perfis = [p for p in perfis if p.nome in restricoes["perfis_permitidos"]]
    if restricoes.get("perfis_excluidos"):
        perfis = [p for p in perfis if p.nome not in restricoes["perfis_excluidos"]]
    return perfis or perfis_disponiveis


def _calcular_peso_total(
    barras: List[BarraFisica],
    perfil_por_grupo: Dict[str, PerfilFisico],
    material: MaterialFisico,
) -> float:
    """Calcula o peso total da estrutura em kg."""
    peso = 0.0
    for b in barras:
        perfil = perfil_por_grupo.get(b.group)
        if perfil:
            peso += perfil.area_m2 * material.rho_kg_m3 * b.length
    return peso


def _contar_perfis_distintos(individuo: List[int], perfis: List[PerfilFisico]) -> int:
    """Conta quantos perfis distintos um indivíduo utiliza."""
    indices = set(individuo)
    return len({perfis[i].nome for i in indices if 0 <= i < len(perfis)})


def _avaliar_individuo(
    individuo: List[int],
    grupos: List[str],
    perfis: List[PerfilFisico],
    material: MaterialFisico,
    nos: Dict[str, NoFisico],
    barras: List[BarraFisica],
    nos_banzo_superior: List[str],
    nos_fachada: List[str],
    casos_carga: List[dict],
    parametros_vento: Optional[ParametrosVento],
    water_lamina_mm: float,
    solo_tipo: str,
    custom_ks: Optional[float],
    footing_b: float,
    footing_l: float,
    usar_penalidade_diversidade: bool,
) -> Tuple[float]:
    """
    Função objetivo do GA.

    Retorna uma tupla (fitness,) — DEAP exige iterável mesmo para fitness simples.
    Fitness = peso_total_kg × custo_kg_material + penalidades (minimiza custo em R$).
    """
    # Mapa grupo → perfil (a partir do indivíduo).
    perfil_por_grupo: Dict[str, PerfilFisico] = {}
    for i, grupo in enumerate(grupos):
        idx = individuo[i] if i < len(individuo) else 0
        idx = max(0, min(idx, len(perfis) - 1))
        perfil_por_grupo[grupo] = perfis[idx]

    # Executa análise MEF.
    resultado = construir_e_resolver(
        nos_entrada=nos,
        barras_entrada=barras,
        perfil_por_grupo=perfil_por_grupo,
        material=material,
        casos_carga_externos=casos_carga,
        parametros_vento=parametros_vento,
        nos_banzo_superior=nos_banzo_superior,
        nos_fachada=nos_fachada,
        water_lamina_mm=water_lamina_mm,
        solo_tipo=solo_tipo,
        custom_ks=custom_ks,
        footing_b=footing_b,
        footing_l=footing_l,
    )

    if resultado.erro:
        # Estrutura inviável — penalidade máxima.
        return (configuracoes.ag_penalidade_violacao_normativa,)

    peso = resultado.peso_total_kg
    penalidade = 0.0

    # 1) Penalidade por violação normativa (NBR 8800).
    for b in resultado.barras:
        if b.utilization > 1.0:
            excesso = b.utilization - 1.0
            penalidade += configuracoes.ag_penalidade_violacao_normativa * excesso

    # 2) Penalidade por flecha excessiva (ELS).
    atendido, _, _ = verificar_flecha_els(
        resultado.flecha_maxima,
        resultado.vano_real,
        limite_divisor=configuracoes.nbr_flecha_limite,
    )
    if not atendido:
        excesso_flecha = resultado.flecha_maxima / max(resultado.vano_real / configuracoes.nbr_flecha_limite, 0.001) - 1.0
        penalidade += configuracoes.ag_penalidade_violacao_normativa * excesso_flecha

    # 3) Penalidade por diversidade de perfis (padronização).
    if usar_penalidade_diversidade:
        num_distintos = _contar_perfis_distintos(individuo, perfis)
        if num_distintos > configuracoes.ag_max_perfis_distintos:
            excesso_diversidade = num_distintos - configuracoes.ag_max_perfis_distintos
            penalidade += configuracoes.ag_penalidade_diversidade_perfis * excesso_diversidade

    fitness = peso * material.custo_kg + penalidade
    return (fitness,)


def otimizar_trelice_ga(
    nos: Dict[str, NoFisico],
    barras: List[BarraFisica],
    grupos: List[str],
    perfis_disponiveis: List[PerfilFisico],
    material: MaterialFisico,
    casos_carga: List[dict],
    nos_banzo_superior: List[str],
    nos_fachada: List[str],
    parametros_vento: Optional[ParametrosVento] = None,
    water_lamina_mm: float = 0.0,
    solo_tipo: str = "Rocha",
    custom_ks: Optional[float] = None,
    footing_b: float = 0.6,
    footing_l: float = 0.6,
    restricoes: Optional[dict] = None,
    geracoes: Optional[int] = None,
    tamanho_populacao: Optional[int] = None,
    cancelador: Optional[CanceladorOtimizacao] = None,
    callback_progresso: Optional[Callable[[int, int, float, str], None]] = None,
    usar_refinamento_local: Optional[bool] = None,
) -> Tuple[ResultadoAnalise, Dict[str, PerfilFisico], List[str]]:
    """
    Executa o algoritmo genético memético completo.

    Se usar_refinamento_local for True (padrão), aplica hill climbing
    first-improvement nos melhores indivíduos a cada geração,
    combinando exploração global (GA) com refinamento local (Lamarckiano).

    Retorna (melhor_resultado, perfil_por_grupo, logs).
    """
    _garantiar_classes_deap()

    # Aplica restrições do usuário ao espaço de busca.
    perfis = _filtrar_perfis(perfis_disponiveis, restricoes)
    num_perfis = len(perfis)
    num_grupos = len(grupos)
    usar_penalidade_diversidade = (
        restricoes.get("usar_penalidade_diversidade", True) if restricoes else True
    )
    usar_refinamento_local = (
        usar_refinamento_local
        if usar_refinamento_local is not None
        else configuracoes.ag_usar_refinamento_local
    )

    geracoes = geracoes or configuracoes.ag_geracoes
    tamanho_populacao = tamanho_populacao or configuracoes.ag_populacao_tamanho

    logs: List[str] = []
    logs.append(
        f"GA {'memético' if usar_refinamento_local else 'puro'} inicializado: "
        f"{num_grupos} grupos, {num_perfis} perfis, "
        f"população={tamanho_populacao}, gerações={geracoes}, "
        f"material={material.nome} (R$ {material.custo_kg:.2f}/kg)."
    )

    # ----------------------------------------------------------------
    # Cache de avaliação (evita re-calcular FEA para mesmos perfis).
    # Resetado a cada execução do GA.
    # ----------------------------------------------------------------
    _cache_avaliacao: Dict[Tuple[int, ...], Tuple[float, ...]] = {}

    def _avaliar_com_cache(individuo: List[int]) -> Tuple[float, ...]:
        """Envolve _avaliar_individuo com cache por combinação de perfis."""
        chave = tuple(individuo)
        if chave in _cache_avaliacao:
            return _cache_avaliacao[chave]
        resultado = _avaliar_individuo(
            individuo, grupos, perfis, material, nos, barras,
            nos_banzo_superior, nos_fachada, casos_carga,
            parametros_vento, water_lamina_mm, solo_tipo,
            custom_ks, footing_b, footing_l, usar_penalidade_diversidade,
        )
        _cache_avaliacao[chave] = resultado
        return resultado

    # ----------------------------------------------------------------
    # Busca local (hill climbing first-improvement com reinício).
    # ----------------------------------------------------------------
    def _refinamento_local(individuo: List[int]) -> float:
        """
        Hill climbing first-improvement com reinício de varredura.

        Para cada grupo, testa o perfil imediatamente acima e abaixo.
        Se qualquer troca unitária melhorar o fitness, adota e reinicia
        a varredura desde o primeiro grupo. Repete até nenhuma troca
        unitária melhorar (convergência para ótimo local).

        Retorna o fitness do indivíduo refinado.
        """
        melhor_fitness = _avaliar_com_cache(individuo)[0]

        while True:
            melhorou = False
            for i in range(num_grupos):
                original = individuo[i]

                # Tenta perfil mais leve (menor índice).
                if original > 0:
                    individuo[i] = original - 1
                    fitness = _avaliar_com_cache(individuo)[0]
                    if fitness < melhor_fitness:
                        melhor_fitness = fitness
                        melhorou = True
                        break
                    individuo[i] = original  # desfaz

                # Tenta perfil mais pesado (maior índice).
                if original < num_perfis - 1:
                    individuo[i] = original + 1
                    fitness = _avaliar_com_cache(individuo)[0]
                    if fitness < melhor_fitness:
                        melhor_fitness = fitness
                        melhorou = True
                        break
                    individuo[i] = original  # desfaz

            if not melhorou:
                break

        return melhor_fitness

    # Configuração do toolbox DEAP.
    toolbox = base.Toolbox()
    toolbox.register("attr_perfil", random.randint, 0, max(num_perfis - 1, 0))
    toolbox.register(
        "individual",
        tools.initRepeat,
        creator.Individual,
        toolbox.attr_perfil,
        n=num_grupos,
    )
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Registra a função de avaliação COM cache.
    toolbox.register("evaluate", _avaliar_com_cache)

    # Crossover de 2 pontos — apropriado para variáveis discretas (índices).
    toolbox.register("mate", tools.cxTwoPoint)
    # Mutação uniforme — substitui um gene por um índice aleatório.
    toolbox.register("mutate", tools.mutUniformInt, low=0, up=max(num_perfis - 1, 0),
                     indpb=1.0 / max(num_grupos, 1))
    toolbox.register("select", tools.selTournament, tournsize=configuracoes.ag_indice_torneio)

    # População inicial.
    populacao = toolbox.population(n=tamanho_populacao)

    # Estatísticas — fitness.values é uma tupla, extraímos o escalar.
    stats = tools.Statistics(lambda ind: ind.fitness.values[0] if ind.fitness.values else float("inf"))
    stats.register("min", lambda x: min(x) if x else float("inf"))
    stats.register("avg", lambda x: sum(x) / len(x) if x else float("inf"))

    # Hall da fama (top 1).
    hof = tools.HallOfFame(1)

    # Loop manual para permitir cancelamento e callback de progresso.
    melhor_fitness_historico = float("inf")
    logbook = tools.Logbook()
    logbook.header = ["gen", "nevals", "min", "avg"]

    for geracao in range(geracoes):
        # Verifica cancelamento.
        if cancelador:
            try:
                cancelador.verificar(contexto=f"geração {geracao+1}/{geracoes}")
            except InterruptedError as e:
                logs.append(f"GA cancelado na geração {geracao+1}: {e}")
                break

        # Verifica memória.
        try:
            verificar_memoria(contexto=f"geração {geracao+1}")
        except Exception as e:
            logs.append(f"GA interrompido por limite de memória: {e}")
            break

        # --------------------------------------------------------
        # FASE GENÉTICA: variação (crossover + mutação)
        # --------------------------------------------------------
        offspring = algorithms.varAnd(populacao, toolbox,
                                      cxpb=configuracoes.ag_probabilidade_cruzamento,
                                      mutpb=configuracoes.ag_probabilidade_mutacao)

        # Avaliação dos inválidos.
        invalidos = [ind for ind in offspring if not ind.fitness.valid]
        if invalidos:
            fitnesses = toolbox.map(toolbox.evaluate, invalidos)
            for ind, fit in zip(invalidos, fitnesses):
                ind.fitness.values = fit

        # --------------------------------------------------------
        # FASE MEMÉTICA: refinamento local nos melhores indivíduos
        # --------------------------------------------------------
        if usar_refinamento_local:
            # Ordena por fitness (menor = melhor) e seleciona top 30%.
            ordenados = sorted(offspring, key=lambda ind: ind.fitness.values[0] if ind.fitness.valid else float("inf"))
            n_refinar = max(1, len(ordenados) // 3)
            for ind in ordenados[:n_refinar]:
                # Converte para lista mutável para a busca local.
                valores = list(ind)
                fitness_refinado = _refinamento_local(valores)
                # Atualiza indivíduo (aprendizagem Lamarckiana).
                for i, val in enumerate(valores):
                    ind[i] = val
                ind.fitness.values = (fitness_refinado,)

        # --------------------------------------------------------
        # SELEÇÃO para próxima geração
        # --------------------------------------------------------
        populacao[:] = toolbox.select(offspring, k=len(populacao))
        hof.update(populacao)

        # Estatísticas.
        record = stats.compile(populacao)
        logbook.record(gen=geracao+1, nevals=len(invalidos), **record)

        if callback_progresso:
            min_fit = record["min"] if record else float("inf")
            msg = f"Geração {geracao+1}/{geracoes} | min=R$ {min_fit:.2f} | avg=R$ {record['avg']:.2f}" if record else f"Geração {geracao+1}/{geracoes}"
            callback_progresso(geracao+1, geracoes, min_fit, msg)

        if record and record["min"] < melhor_fitness_historico:
            melhor_fitness_historico = record["min"]

    # Reconstrói o melhor resultado.
    melhor_individuo = hof[0] if hof else populacao[0]
    perfil_por_grupo: Dict[str, PerfilFisico] = {}
    for i, grupo in enumerate(grupos):
        idx = max(0, min(int(melhor_individuo[i]), num_perfis - 1))
        perfil_por_grupo[grupo] = perfis[idx]

    melhor_resultado = construir_e_resolver(
        nos_entrada=nos,
        barras_entrada=barras,
        perfil_por_grupo=perfil_por_grupo,
        material=material,
        casos_carga_externos=casos_carga,
        parametros_vento=parametros_vento,
        nos_banzo_superior=nos_banzo_superior,
        nos_fachada=nos_fachada,
        water_lamina_mm=water_lamina_mm,
        solo_tipo=solo_tipo,
        custom_ks=custom_ks,
        footing_b=footing_b,
        footing_l=footing_l,
    )
    melhor_resultado.logs = logs

    logs.append(
        f"GA concluído. Melhor custo: R$ {melhor_fitness_historico:.2f}. "
        f"Perfis escolhidos: {', '.join(f'{g}={p.nome}' for g, p in perfil_por_grupo.items())}."
    )

    return melhor_resultado, perfil_por_grupo, logs
