"""Teste de integração do Algoritmo Genético com o solver MEF."""

import pytest

from engineering.modelos_fisicos import BarraFisica, MaterialFisico, NoFisico, PerfilFisico
from optimization.algoritmo_genetico import otimizar_trelice_ga


@pytest.fixture
def trelica_simples():
    """Treliça Pratt simples com 3 painéis para teste rápido."""
    nos = {
        "L0": NoFisico("L0", 0, 0, 0, support="Pinned"),
        "L1": NoFisico("L1", 2, 0, 0),
        "L2": NoFisico("L2", 4, 0, 0),
        "L3": NoFisico("L3", 6, 0, 0, support="Roller"),
        "U0": NoFisico("U0", 0, 1.5, 0),
        "U1": NoFisico("U1", 2, 1.5, 0),
        "U2": NoFisico("U2", 4, 1.5, 0),
        "U3": NoFisico("U3", 6, 1.5, 0),
    }
    barras = [
        BarraFisica(1, "L0", "L1", "Banzo Inferior", 2.0),
        BarraFisica(2, "L1", "L2", "Banzo Inferior", 2.0),
        BarraFisica(3, "L2", "L3", "Banzo Inferior", 2.0),
        BarraFisica(4, "U0", "U1", "Banzo Superior", 2.0),
        BarraFisica(5, "U1", "U2", "Banzo Superior", 2.0),
        BarraFisica(6, "U2", "U3", "Banzo Superior", 2.0),
        BarraFisica(7, "L0", "U0", "Montante", 1.5),
        BarraFisica(8, "L1", "U1", "Montante", 1.5),
        BarraFisica(9, "L2", "U2", "Montante", 1.5),
        BarraFisica(10, "L3", "U3", "Montante", 1.5),
        # Diagonais (Pratt: tracionadas sob carga descendente).
        BarraFisica(11, "L0", "U1", "Diagonal", 2.5),
        BarraFisica(12, "L1", "U2", "Diagonal", 2.5),
        BarraFisica(13, "L2", "U3", "Diagonal", 2.5),
    ]
    return nos, barras


@pytest.fixture
def material_a36():
    return MaterialFisico(
        nome="A36",
        e_gpa=200.0,
        g_gpa=76.9,
        nu=0.30,
        fy_mpa=250.0,
        fu_mpa=400.0,
        rho_kg_m3=7850.0,
        custo_kg=8.45,
    )


@pytest.fixture
def perfis_curtos():
    """Catálogo reduzido para teste rápido do GA."""
    return [
        PerfilFisico(1, "L25x3.18", "L", 25, 25, 0, 3.18, 1.49e-4, 7.49e-9, 7.49e-9, 5.02e-10),
        PerfilFisico(2, "L32x3.18", "L", 32, 32, 0, 3.18, 1.92e-4, 1.60e-8, 1.60e-8, 6.47e-10),
        PerfilFisico(3, "L51x3.18", "L", 51, 51, 0, 3.18, 3.06e-4, 6.55e-8, 6.55e-8, 9.95e-10),
        PerfilFisico(
            4, "RHS50x30x2.00", "RHS", 50, 30, 0, 2.00, 2.96e-4, 5.60e-8, 2.08e-8, 5.50e-8
        ),
        PerfilFisico(
            5, "RHS60x40x2.00", "RHS", 60, 40, 0, 2.00, 3.76e-4, 1.11e-7, 5.43e-8, 1.28e-7
        ),
    ]


def test_ga_produz_solucao_estavel(trelica_simples, material_a36, perfis_curtos):
    """GA deve produzir uma solução sem erro em treliça simples."""
    nos, barras = trelica_simples
    grupos = list({b.group for b in barras})
    casos_carga = [
        {"type": "G", "direction": "FY", "value": -2000.0},
        {"type": "Q", "direction": "FY", "value": -3000.0},
    ]
    nos_banzo_superior = ["U0", "U1", "U2", "U3"]

    resultado, perfil_por_grupo, logs = otimizar_trelice_ga(
        nos=nos,
        barras=barras,
        grupos=grupos,
        perfis_disponiveis=perfis_curtos,
        material=material_a36,
        casos_carga=casos_carga,
        nos_banzo_superior=nos_banzo_superior,
        nos_fachada=[],
        geracoes=3,
        tamanho_populacao=6,
    )

    assert resultado is not None
    assert len(logs) > 0
    assert perfil_por_grupo is not None
    assert len(perfil_por_grupo) == len(grupos)


def test_ga_respeita_restricoes_familia(trelica_simples, material_a36, perfis_curtos):
    """GA deve usar apenas perfis da família permitida."""
    nos, barras = trelica_simples
    grupos = list({b.group for b in barras})
    casos_carga = [{"type": "G", "direction": "FY", "value": -1000.0}]
    nos_banzo_superior = ["U0", "U1", "U2", "U3"]

    _, perfil_por_grupo, _ = otimizar_trelice_ga(
        nos=nos,
        barras=barras,
        grupos=grupos,
        perfis_disponiveis=perfis_curtos,
        material=material_a36,
        casos_carga=casos_carga,
        nos_banzo_superior=nos_banzo_superior,
        nos_fachada=[],
        restricoes={"familias_permitidas": ["RHS"]},
        geracoes=2,
        tamanho_populacao=4,
    )

    for perfil in perfil_por_grupo.values():
        assert perfil.familia == "RHS"


# =====================================================================
# Testes de regressão: algoritmo memético
# =====================================================================


def test_ga_populacao_inicial_eh_avaliada(trelica_simples, material_a36, perfis_curtos):
    """População inicial é avaliada antes do loop evolutivo."""
    nos, barras = trelica_simples
    grupos = list({b.group for b in barras})
    casos_carga = [{"type": "G", "direction": "FY", "value": -1000.0}]
    nos_banzo_superior = ["U0", "U1", "U2", "U3"]

    progresso = []

    def callback(geracao, total, min_fit, msg):
        progresso.append((geracao, min_fit))

    otimizar_trelice_ga(
        nos=nos,
        barras=barras,
        grupos=grupos,
        perfis_disponiveis=perfis_curtos,
        material=material_a36,
        casos_carga=casos_carga,
        nos_banzo_superior=nos_banzo_superior,
        nos_fachada=[],
        geracoes=3,
        tamanho_populacao=6,
        callback_progresso=callback,
    )

    # O callback deve ter recebido a geração 0 (população inicial).
    assert len(progresso) > 0
    assert progresso[0][0] == 0, "Geração 0 (população inicial) não foi reportada"
    # O fitness mínimo da geração 0 deve ser finito (não inf).
    assert progresso[0][1] < float("inf"), "População inicial não foi avaliada (fitness=inf)"


def test_ga_elitismo_preserva_melhor_entre_geracoes(trelica_simples, material_a36, perfis_curtos):
    """Fitness é monótono não-crescente entre gerações (elitismo efetivo)."""
    nos, barras = trelica_simples
    grupos = list({b.group for b in barras})
    casos_carga = [{"type": "G", "direction": "FY", "value": -1500.0}]
    nos_banzo_superior = ["U0", "U1", "U2", "U3"]

    fitness_por_geracao = []

    def callback(geracao, total, min_fit, msg):
        fitness_por_geracao.append(min_fit)

    otimizar_trelice_ga(
        nos=nos,
        barras=barras,
        grupos=grupos,
        perfis_disponiveis=perfis_curtos,
        material=material_a36,
        casos_carga=casos_carga,
        nos_banzo_superior=nos_banzo_superior,
        nos_fachada=[],
        geracoes=6,
        tamanho_populacao=8,
        callback_progresso=callback,
        usar_refinamento_local=False,  # GA puro para isolar o elitismo
    )

    # O melhor fitness deve ser monótono não-crescente.
    for i in range(1, len(fitness_por_geracao)):
        assert fitness_por_geracao[i] <= fitness_por_geracao[i - 1] + 1e-6, (
            f"Elitismo quebrado: geração {i} tem fitness "
            f"{fitness_por_geracao[i]:.4f} > {fitness_por_geracao[i - 1]:.4f} "
            f"(geração anterior)"
        )


def test_ga_puro_sem_refinamento_local_funciona(trelica_simples, material_a36, perfis_curtos):
    """
    GA puro (usar_refinamento_local=False) também deve funcionar e
    produzir uma solução válida.
    """
    nos, barras = trelica_simples
    grupos = list({b.group for b in barras})
    casos_carga = [{"type": "G", "direction": "FY", "value": -1000.0}]
    nos_banzo_superior = ["U0", "U1", "U2", "U3"]

    resultado, perfil_por_grupo, logs = otimizar_trelice_ga(
        nos=nos,
        barras=barras,
        grupos=grupos,
        perfis_disponiveis=perfis_curtos,
        material=material_a36,
        casos_carga=casos_carga,
        nos_banzo_superior=nos_banzo_superior,
        nos_fachada=[],
        geracoes=3,
        tamanho_populacao=6,
        usar_refinamento_local=False,
    )

    assert resultado is not None
    assert len(perfil_por_grupo) == len(grupos)
    # Confirma que o GA puro foi registrado nos logs.
    assert any("puro" in linha.lower() for linha in logs), "GA puro não foi registrado nos logs"


def test_ga_memetico_nao_termina_infinito(trelica_simples, material_a36, perfis_curtos):
    """Busca local hill-climbing termina em tempo finito (trava max_iter)."""
    import time

    nos, barras = trelica_simples
    grupos = list({b.group for b in barras})
    casos_carga = [{"type": "G", "direction": "FY", "value": -1000.0}]
    nos_banzo_superior = ["U0", "U1", "U2", "U3"]

    inicio = time.time()
    otimizar_trelice_ga(
        nos=nos,
        barras=barras,
        grupos=grupos,
        perfis_disponiveis=perfis_curtos,
        material=material_a36,
        casos_carga=casos_carga,
        nos_banzo_superior=nos_banzo_superior,
        nos_fachada=[],
        geracoes=2,
        tamanho_populacao=4,
        usar_refinamento_local=True,
    )
    duracao = time.time() - inicio

    # Deve terminar em menos de 60 segundos para uma treliça simples.
    assert duracao < 60.0, (
        f"GA memético demorou {duracao:.1f}s: possível loop infinito na busca local"
    )


def test_ga_zero_geracoes_avalia_populacao_inicial(trelica_simples, material_a36, perfis_curtos):
    """Com zero gerações, avalia população inicial e retorna resultado."""
    nos, barras = trelica_simples
    grupos = list({b.group for b in barras})
    casos_carga = [{"type": "G", "direction": "FY", "value": -1000.0}]
    nos_banzo_superior = ["U0", "U1", "U2", "U3"]

    resultado, perfil_por_grupo, logs = otimizar_trelice_ga(
        nos=nos,
        barras=barras,
        grupos=grupos,
        perfis_disponiveis=perfis_curtos,
        material=material_a36,
        casos_carga=casos_carga,
        nos_banzo_superior=nos_banzo_superior,
        nos_fachada=[],
        geracoes=0,
        tamanho_populacao=4,
    )

    # Mesmo com 0 gerações, deve retornar um resultado (da pop inicial).
    assert resultado is not None
    assert len(perfil_por_grupo) == len(grupos)
