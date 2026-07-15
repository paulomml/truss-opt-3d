"""
Motor de Otimização: Algoritmo Genético Memético (DEAP + Hill Climbing).

Combina:
- GA (exploração global): crossover, mutação, seleção por torneio.
- Busca local (refinamento): hill climbing first-improvement nos melhores
  indivíduos a cada geração (aprendizagem Lamarckiana).

Indivíduo: vetor de inteiros (índices no catálogo de perfis), um por grupo.
Fitness: peso_total_kg x custo_kg_material + penalidades (minimiza R$).
Penalidades: violação NBR 8800/6120/6123, flecha ELS, diversidade de perfis.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable

from deap import algorithms, base, creator, tools

from core.config import configuracoes
from core.memoria import CanceladorOtimizacao, verificar_memoria
from engineering.fea.pynite_solver import construir_e_resolver
from engineering.modelos_fisicos import (
    BarraFisica,
    MaterialFisico,
    NoFisico,
    PerfilFisico,
    ResultadoAnalise,
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
    perfis_disponiveis: list[PerfilFisico],
    restricoes: dict | None,
) -> list[PerfilFisico]:
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
    barras: list[BarraFisica],
    perfil_por_grupo: dict[str, PerfilFisico],
    material: MaterialFisico,
) -> float:
    """Calcula o peso total da estrutura em kg."""
    peso = 0.0
    for b in barras:
        perfil = perfil_por_grupo.get(b.group)
        if perfil:
            peso += perfil.area_m2 * material.rho_kg_m3 * b.length
    return peso


def _contar_perfis_distintos(individuo: list[int], perfis: list[PerfilFisico]) -> int:
    """Conta quantos perfis distintos um indivíduo utiliza."""
    indices = set(individuo)
    return len({perfis[i].nome for i in indices if 0 <= i < len(perfis)})


def _avaliar_individuo(
    individuo: list[int],
    grupos: list[str],
    perfis: list[PerfilFisico],
    material: MaterialFisico,
    nos: dict[str, NoFisico],
    barras: list[BarraFisica],
    nos_banzo_superior: list[str],
    nos_fachada: list[str],
    casos_carga: list[dict],
    parametros_vento: ParametrosVento | None,
    water_lamina_mm: float,
    solo_tipo: str,
    custom_ks: float | None,
    footing_b: float,
    footing_l: float,
    usar_penalidade_diversidade: bool,
) -> tuple[float]:
    """
    Função objetivo do GA.

    Retorna uma tupla (fitness,): DEAP exige iterável mesmo para fitness simples.
    Fitness = peso_total_kg x custo_kg_material + penalidades (minimiza custo em R$).
    """
    # Mapa grupo -> perfil (a partir do indivíduo).
    perfil_por_grupo: dict[str, PerfilFisico] = {}
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
        # Estrutura inviável: penalidade máxima.
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
        excesso_flecha = (
            resultado.flecha_maxima
            / max(resultado.vano_real / configuracoes.nbr_flecha_limite, 0.001)
            - 1.0
        )
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
    nos: dict[str, NoFisico],
    barras: list[BarraFisica],
    grupos: list[str],
    perfis_disponiveis: list[PerfilFisico],
    material: MaterialFisico,
    casos_carga: list[dict],
    nos_banzo_superior: list[str],
    nos_fachada: list[str],
    parametros_vento: ParametrosVento | None = None,
    water_lamina_mm: float = 0.0,
    solo_tipo: str = "Rocha",
    custom_ks: float | None = None,
    footing_b: float = 0.6,
    footing_l: float = 0.6,
    restricoes: dict | None = None,
    geracoes: int | None = None,
    tamanho_populacao: int | None = None,
    cancelador: CanceladorOtimizacao | None = None,
    callback_progresso: Callable[[int, int, float, str], None] | None = None,
    usar_refinamento_local: bool | None = None,
) -> tuple[ResultadoAnalise, dict[str, PerfilFisico], list[str]]:
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

    logs: list[str] = []
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
    _cache_avaliacao: dict[tuple[int, ...], tuple[float, ...]] = {}

    def _avaliar_com_cache(individuo: list[int]) -> tuple[float, ...]:
        """Envolve _avaliar_individuo com cache por combinação de perfis."""
        chave = tuple(individuo)
        if chave in _cache_avaliacao:
            return _cache_avaliacao[chave]
        resultado = _avaliar_individuo(
            individuo,
            grupos,
            perfis,
            material,
            nos,
            barras,
            nos_banzo_superior,
            nos_fachada,
            casos_carga,
            parametros_vento,
            water_lamina_mm,
            solo_tipo,
            custom_ks,
            footing_b,
            footing_l,
            usar_penalidade_diversidade,
        )
        _cache_avaliacao[chave] = resultado
        return resultado

    # ----------------------------------------------------------------
    # Busca local (hill climbing first-improvement com reinício).
    # ----------------------------------------------------------------
    def _refinamento_local(individuo: list[int], max_iter: int = 2000) -> float:
        """
        Hill climbing first-improvement com reinício de varredura.

        Testa o perfil imediatamente acima e abaixo de cada grupo.
        Reinicia a varredura ao encontrar melhora. Trava de segurança
        em max_iter iteracoes.

        Retorna o fitness do indivíduo refinado.
        """
        melhor_fitness = _avaliar_com_cache(individuo)[0]
        iter_count = 0

        while iter_count < max_iter:
            iter_count += 1
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

    # Crossover de 2 pontos: apropriado para variáveis discretas (índices).
    toolbox.register("mate", tools.cxTwoPoint)
    # Mutação uniforme: substitui um gene por um índice aleatório.
    toolbox.register(
        "mutate",
        tools.mutUniformInt,
        low=0,
        up=max(num_perfis - 1, 0),
        indpb=1.0 / max(num_grupos, 1),
    )
    toolbox.register("select", tools.selTournament, tournsize=configuracoes.ag_indice_torneio)

    # População inicial.
    populacao = toolbox.population(n=tamanho_populacao)

    # Estatísticas: fitness.values é uma tupla, extraímos o escalar.
    stats = tools.Statistics(
        lambda ind: ind.fitness.values[0] if ind.fitness.values else float("inf")
    )
    stats.register("min", lambda x: min(x) if x else float("inf"))
    stats.register("avg", lambda x: sum(x) / len(x) if x else float("inf"))

    # Hall da fama (top 1): rastreia o melhor indivíduo já visto.
    hof = tools.HallOfFame(1)

    # Loop manual para permitir cancelamento e callback de progresso.
    melhor_fitness_historico = float("inf")
    logbook = tools.Logbook()
    logbook.header = ["gen", "nevals", "min", "avg"]

    # ----------------------------------------------------------------
    # Avaliação da população inicial (geração 0)
    # ----------------------------------------------------------------
    # algorithms.varAnd não avalia a população: apenas produz filhos.
    invalidos_iniciais = [ind for ind in populacao if not ind.fitness.valid]
    if invalidos_iniciais:
        fitnesses_init = toolbox.map(toolbox.evaluate, invalidos_iniciais)
        for ind, fit in zip(invalidos_iniciais, fitnesses_init):
            ind.fitness.values = fit

    # Fase memética inicial: refina os melhores ~30% da população.
    if usar_refinamento_local and populacao:
        ordenados_init = sorted(
            populacao,
            key=lambda ind: ind.fitness.values[0] if ind.fitness.valid else float("inf"),
        )
        n_refinar_init = max(1, len(ordenados_init) // 3)
        for ind in ordenados_init[:n_refinar_init]:
            valores = list(ind)
            fitness_refinado = _refinamento_local(valores)
            for i, val in enumerate(valores):
                ind[i] = val
            ind.fitness.values = (fitness_refinado,)

    # Atualiza o Hall of Fame com a população inicial refinada.
    hof.update(populacao)

    # Estatísticas da geração 0 (população inicial).
    record_init = stats.compile(populacao)
    logbook.record(gen=0, nevals=len(invalidos_iniciais), **(record_init or {}))
    if record_init and record_init["min"] < melhor_fitness_historico:
        melhor_fitness_historico = record_init["min"]
    if callback_progresso:
        min_fit_init = record_init["min"] if record_init else float("inf")
        avg_init = record_init["avg"] if record_init else float("inf")
        msg_init = (
            f"Geração 0/{geracoes} (inicial) | min=R$ {min_fit_init:.2f} | avg=R$ {avg_init:.2f}"
            if record_init
            else f"Geração 0/{geracoes} (inicial)"
        )
        callback_progresso(0, geracoes, min_fit_init, msg_init)

    for geracao in range(geracoes):
        # Verifica cancelamento.
        if cancelador:
            try:
                cancelador.verificar(contexto=f"geração {geracao + 1}/{geracoes}")
            except InterruptedError as e:
                logs.append(f"GA cancelado na geração {geracao + 1}: {e}")
                break

        # Verifica memória.
        try:
            verificar_memoria(contexto=f"geração {geracao + 1}")
        except Exception as e:
            logs.append(f"GA interrompido por limite de memória: {e}")
            break

        # --------------------------------------------------------
        # FASE GENÉTICA: variação (crossover + mutação)
        # --------------------------------------------------------
        offspring = algorithms.varAnd(
            populacao,
            toolbox,
            cxpb=configuracoes.ag_probabilidade_cruzamento,
            mutpb=configuracoes.ag_probabilidade_mutacao,
        )

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
            ordenados = sorted(
                offspring,
                key=lambda ind: ind.fitness.values[0] if ind.fitness.valid else float("inf"),
            )
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
        # SELEÇÃO para próxima geração (mu, lambda)
        # --------------------------------------------------------
        # Seleciona a próxima população apenas a partir dos filhos.
        populacao[:] = toolbox.select(offspring, k=len(populacao))

        # --------------------------------------------------------
        # Elitismo: substitui o pior pelo melhor (Hall of Fame)
        # --------------------------------------------------------
        if len(hof) > 0 and len(populacao) > 0:
            elite = hof[0]
            elite_fit = elite.fitness.values[0] if elite.fitness.valid else float("inf")
            # Localiza o pior indivíduo da população atual (maior fitness
            # = pior, pois o GA minimiza custo em R$).
            pior_idx = max(
                range(len(populacao)),
                key=lambda i: (
                    populacao[i].fitness.values[0] if populacao[i].fitness.valid else float("-inf")
                ),
            )
            pior_fit = (
                populacao[pior_idx].fitness.values[0]
                if populacao[pior_idx].fitness.valid
                else float("inf")
            )
            # Substitui o pior por uma cópia do elite, apenas se o elite
            # for estritamente melhor (evita cópias desnecessárias e
            # preserva diversidade quando o elite já está na população).
            if elite_fit < pior_fit:
                populacao[pior_idx] = toolbox.clone(elite)

        hof.update(populacao)

        # Estatísticas.
        record = stats.compile(populacao)
        logbook.record(gen=geracao + 1, nevals=len(invalidos), **(record or {}))

        if callback_progresso:
            min_fit = record["min"] if record else float("inf")
            avg_fit = record["avg"] if record else float("inf")
            msg = (
                f"Geração {geracao + 1}/{geracoes} | min=R$ {min_fit:.2f} | avg=R$ {avg_fit:.2f}"
                if record
                else f"Geração {geracao + 1}/{geracoes}"
            )
            callback_progresso(geracao + 1, geracoes, min_fit, msg)

        if record and record["min"] < melhor_fitness_historico:
            melhor_fitness_historico = record["min"]

    # Reconstrói o melhor resultado.
    melhor_individuo = hof[0] if hof else populacao[0]
    perfil_por_grupo: dict[str, PerfilFisico] = {}
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
