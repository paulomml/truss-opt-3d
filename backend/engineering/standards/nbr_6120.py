"""
Verificações NBR 6120:2019: Ações para o cálculo de estruturas de edificações.

Carga de manutenção, cargas em coberturas, assimetria de cargas (Anexo D)
e empoçamento progressivo (Anexo D).
"""

from __future__ import annotations

from dataclasses import dataclass

# Coeficientes de combinação NBR 8681 (referenciados pela NBR 6120).
PSI_0 = 0.7  # Sobrecarga de uso (valor de cálculo reduzido para combinações).
PSI_1 = 0.5  # Sobrecarga freqüente.
PSI_2 = 0.3  # Sobrecarga quase-permanente.

# Coeficientes de ponderação para combinações últimas (ELU).
GAMMA_G = 1.35  # Carga permanente (desfavorável).
GAMMA_Q = 1.50  # Carga variável principal.
GAMMA_G_FAV = 1.0  # Carga permanente favorável (alívio).

# Coeficientes para combinações de serviço (ELS).
GAMMA_G_SLS = 1.0
GAMMA_Q_SLS_FREQ = 0.5
GAMMA_Q_SLS_PERM = 0.3


@dataclass
class CasoCargaNormalizado:
    """Caso de carga normalizado para o solver."""

    tipo: str  # 'G' | 'Q' | 'G2' (permanente adicional) | 'W' (vento) | 'M' (manutenção)
    direction: str  # 'FX' | 'FY' | 'FZ'
    valor: float  # em Newtons
    nos: list[str] | None = None  # None = distribuir no banzo superior


def calcular_carga_cobertura(inclinacao_percentual: float) -> float:
    """
    Carga variável mínima em cobertura (Item 6.4).

    Para inclinações de 1% a 5%, q varia de 0.50 a 0.25 kN/m^2.
    Acima de 5%, q = 0.25 kN/m^2 (mínimo absoluto).
    Abaixo de 1%, não é permitido (recomendação).
    """
    if inclinacao_percentual < 1.0:
        return 0.50  # Conservador: usar máximo.
    if inclinacao_percentual >= 5.0:
        return 0.25
    # Faixa intermediária: valores conservadores entre 1% e 5%.
    if inclinacao_percentual < 3.0:
        return 0.40
    return 0.25


def gerar_casos_manutencao(
    nos_banzo_superior: list[str],
    carga_kn: float = 1.0,
) -> list[CasoCargaNormalizado]:
    """
    Gera casos de carga concentrada de manutenção (Item 6.4).

    A carga de 1 kN atua isoladamente em cada nó do banzo superior, na
    posição mais desfavorável. O solver cria uma combinação por nó.
    """
    carga_n = carga_kn * 1000.0  # kN -> N
    casos = []
    for nid in nos_banzo_superior:
        casos.append(
            CasoCargaNormalizado(
                tipo="M",
                direction="FY",
                valor=-carga_n,
                nos=[nid],
            )
        )
    return casos


def gerar_casos_assimetricos(
    nos_banzo_superior: list[str],
    carga_distribuida_n: float,
    eixo_x: bool = True,
) -> list[CasoCargaNormalizado]:
    """
    Gera casos de carga assimétrica (NBR 6120: envoltória).

    Para treliças, a envoltória mais crítica considera:
    1. Meia carga no lado esquerdo (primeira metade dos nós).
    2. Meia carga no lado direito.
    3. Carga em nós alternados (efeito de montagem).

    Retorna lista de casos para serem combinados como 'Q' pelo solver.
    """
    if not nos_banzo_superior:
        return []
    n = len(nos_banzo_superior)
    meio = n // 2

    casos = []
    # Caso 1: metade esquerda carregada.
    casos.append(
        CasoCargaNormalizado(
            tipo="Q",
            direction="FY",
            valor=-carga_distribuida_n,
            nos=nos_banzo_superior[:meio],
        )
    )
    # Caso 2: metade direita carregada.
    casos.append(
        CasoCargaNormalizado(
            tipo="Q",
            direction="FY",
            valor=-carga_distribuida_n,
            nos=nos_banzo_superior[meio:],
        )
    )
    # Caso 3: nós alternados (1 sim, 1 não).
    casos.append(
        CasoCargaNormalizado(
            tipo="Q",
            direction="FY",
            valor=-carga_distribuida_n * 2,  # compensação de nós vazios
            nos=[nid for i, nid in enumerate(nos_banzo_superior) if i % 2 == 0],
        )
    )
    return casos


def verificar_empozamento(
    flecha_permanente: float,
    vano: float,
    inclinacao_projeto: float,
    contraflecha: float,
    carga_chuva_kn_m2: float = 0.0,
) -> tuple[bool, str]:
    """
    Verifica empoçamento progressivo (Anexo D: NBR 6120).

    Requisitos:
    1. i_def = i_projeto - 0.024 * L3 * g / (E * I) + contraflecha/24 >= 1%
    2. i_def = i_projeto + 0.024 * L * p / (E * I) - contraflecha/24 > 0

    Implementação simplificada: compara flecha sob carga permanente + chuva
    com a inclinação mínima de 1%.
    """
    if vano <= 0:
        return True, "Vão indefinido."

    inclinacao_efetiva = inclinacao_projeto - (flecha_permanente / vano) * 100
    inclinacao_efetiva += (contraflecha / vano) * 100

    if inclinacao_efetiva < 1.0:
        return False, (
            f"Inclinação efetiva {inclinacao_efetiva:.2f}% < 1% mínimo "
            "(Anexo D NBR 6120): risco de empoçamento progressivo."
        )
    return True, f"Inclinação efetiva {inclinacao_efetiva:.2f}% >= 1% (Anexo D)."


def combinacoes_elu() -> list[tuple[str, dict]]:
    """
    Define as combinações últimas (ELU) conforme NBR 8681/6120.

    Retorna lista de (nome, fatores) para PyNite.
    """
    return [
        ("ELU_Normal", {"Dead1": 1.25, "Dead2": 1.40, "Live": 1.50, "Wind": 1.40}),
        ("ELU_Secundario", {"Dead1": 1.25, "Dead2": 1.40, "Live": 1.40, "Wind": 1.40}),
        ("ELU_Alivio", {"Dead1": 1.00, "Dead2": 1.00, "Live": 1.50, "Wind": 0.00}),
        ("ELU_Sem_Vento", {"Dead1": 1.25, "Dead2": 1.40, "Live": 1.50}),
        ("ELU_Vento_Dominante", {"Dead1": 1.25, "Dead2": 1.40, "Live": 1.00, "Wind": 1.40}),
    ]


def combinacoes_els() -> list[tuple[str, dict]]:
    """
    Define as combinações de serviço (ELS) para verificação de flecha.

    NBR 6120 recomenda:
    - Frequente: G + psi1 * Q  (flecha incômoda)
    - Quase-permanente: G + psi2 * Q  (flecha de longa duração)
    - Rara: G + Q  (flecha total)
    """
    return [
        ("ELS_Flecha_Total", {"Dead1": 1.00, "Dead2": 1.00, "Live": 1.00}),
        ("ELS_Flecha_Frequente", {"Dead1": 1.00, "Dead2": 1.00, "Live": PSI_1}),
        ("ELS_Flecha_Permanente", {"Dead1": 1.00, "Dead2": 1.00, "Live": PSI_2}),
        ("ELS_Permanente", {"Dead1": 1.00, "Dead2": 1.00}),
    ]
