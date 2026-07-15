"""
Testes unitários das verificações NBR 6120.

Cobrem:
- Geração de casos de carga de manutenção (Item 6.4).
- Geração de casos de carga assimétricos.
- Combinações ELU e ELS.
- Verificação de empoçamento progressivo (Anexo D).
"""

from engineering.standards.nbr_6120 import (
    calcular_carga_cobertura,
    combinacoes_els,
    combinacoes_elu,
    gerar_casos_assimetricos,
    gerar_casos_manutencao,
    verificar_empozamento,
)


def test_carga_cobertura_inclinacao_baixa():
    """Para inclinação < 1%, q deve usar o máximo (0.50 kN/m^2)."""
    q = calcular_carga_cobertura(0.5)
    assert q == 0.50


def test_carga_cobertura_inclinacao_alta():
    """Para inclinação >= 5%, q deve ser 0.25 kN/m^2."""
    q = calcular_carga_cobertura(7.0)
    assert q == 0.25


def test_gerar_casos_manutencao():
    """Deve gerar um caso de 1 kN por nó do banzo superior."""
    nos = ["N1", "N2", "N3"]
    casos = gerar_casos_manutencao(nos, carga_kn=1.0)
    assert len(casos) == 3
    for caso in casos:
        assert abs(abs(caso.valor) - 1000.0) < 1.0  # 1 kN = 1000 N
        assert len(caso.nos) == 1


def test_gerar_casos_assimetricos():
    """Deve gerar 3 casos: metade esq, metade dir, alternados."""
    nos = ["N1", "N2", "N3", "N4"]
    casos = gerar_casos_assimetricos(nos, 5000.0)
    assert len(casos) == 3
    # Metade esquerda: 2 nós.
    assert len(casos[0].nos) == 2
    # Metade direita: 2 nós.
    assert len(casos[1].nos) == 2
    # Alternados: 2 nós (pares).
    assert len(casos[2].nos) == 2


def test_combinacoes_elu_contem_normal():
    """Deve incluir combinação ELU_Normal."""
    combos = combinacoes_elu()
    nomes = [c[0] for c in combos]
    assert "ELU_Normal" in nomes


def test_combinacoes_els_contem_flecha_total():
    """Deve incluir combinação ELS_Flecha_Total."""
    combos = combinacoes_els()
    nomes = [c[0] for c in combos]
    assert "ELS_Flecha_Total" in nomes


def test_verificacao_empozamento_ok():
    """Inclinação efetiva >= 1% deve retornar atendido."""
    atendido, msg = verificar_empozamento(
        flecha_permanente=0.005,
        vano=5.0,
        inclinacao_projeto=3.0,
        contraflecha=0.0,
    )
    assert atendido


def test_verificacao_empozamento_falha():
    """Inclinação efetiva < 1% deve falhar."""
    atendido, msg = verificar_empozamento(
        flecha_permanente=0.1,  # 100 mm de flecha
        vano=5.0,
        inclinacao_projeto=1.0,
        contraflecha=0.0,
    )
    assert not atendido
    assert "empoçamento" in msg.lower()
