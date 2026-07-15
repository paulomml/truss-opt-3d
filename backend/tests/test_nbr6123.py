"""
Testes unitários das verificações NBR 6123 (vento).

Cobrem:
- Cálculo de velocidade característica Vk.
- Cálculo de pressão dinâmica q.
- Decomposição de direção do vento.
- Cálculo de forças de vento 3D.
- Identificação de fachadas perpendiculares.
"""
import math

import pytest

from engineering.modelos_fisicos import NoFisico
from engineering.standards.nbr_6123 import (
    ParametrosVento,
    calcular_area_frontal,
    calcular_forcas_vento_3d,
    decompor_direcao_vento,
    identificar_fachadas_perpendiculares,
)


def test_velocidade_caracteristica():
    """Vk = V0 * S1 * S2 * S3."""
    pv = ParametrosVento(v0_mps=40.0, s1=1.0, s2=1.0, s3=1.0)
    assert pv.velocidade_caracteristica == 40.0

    pv2 = ParametrosVento(v0_mps=40.0, s1=1.1, s2=0.9, s3=1.0)
    assert abs(pv2.velocidade_caracteristica - 39.6) < 0.1


def test_pressao_dinamica():
    """q = 0.613 * Vk^2."""
    pv = ParametrosVento(v0_mps=40.0, s1=1.0, s2=1.0, s3=1.0)
    # q = 0.613 * 40^2 = 0.613 * 1600 = 980.8 N/m^2
    assert abs(pv.pressao_dinamica - 980.8) < 1.0


def test_decompor_direcao_vento():
    """Direção 0 graus = eixo X puro."""
    fx, fz = decompor_direcao_vento(0.0)
    assert abs(fx - 1.0) < 1e-6
    assert abs(fz - 0.0) < 1e-6

    # Direção 90 graus = eixo Z puro.
    fx, fz = decompor_direcao_vento(90.0)
    assert abs(fx - 0.0) < 1e-6
    assert abs(fz - 1.0) < 1e-6


def test_calcular_area_frontal():
    """Área frontal = altura * largura_projetada."""
    nos = {
        "A": NoFisico("A", 0, 0, 0),
        "B": NoFisico("B", 10, 0, 0),
        "C": NoFisico("C", 0, 5, 0),
        "D": NoFisico("D", 10, 5, 0),
    }
    # Vento em 0 graus (eixo X): projeta em fx=1, fz=0 -> largura projetada = 0
    # Mas área frontal deve usar max-min da projeção.
    area = calcular_area_frontal(nos, 0.0)
    assert area > 0  # altura * (max - min da projeção)


def test_calcular_forcas_vento_3d():
    """Forças de vento devem ser geradas para os nós do banzo superior."""
    nos = {
        "A": NoFisico("A", 0, 0, 0),
        "B": NoFisico("B", 10, 0, 0),
        "C": NoFisico("C", 0, 5, 0),
        "D": NoFisico("D", 10, 5, 0),
        "E": NoFisico("E", 0, 5, 2),
        "F": NoFisico("F", 10, 5, 2),
    }
    pv = ParametrosVento()
    forcas = calcular_forcas_vento_3d(
        nos,
        pv,
        nos_banzo_superior=["C", "D", "E", "F"],
        nos_fachada=["A", "B"],
    )
    assert len(forcas) > 0
    # Deve haver forças verticais (FY) por causa do banzo superior.
    direcoes = {f.direction for f in forcas}
    assert "FY" in direcoes


def test_identificar_fachadas_perpendiculares():
    """Para vento em 0 graus, fachadas são os nós em x_min e x_max."""
    nos = {
        "A": NoFisico("A", 0, 0, 0),
        "B": NoFisico("B", 10, 0, 0),
        "C": NoFisico("C", 5, 5, 0),
    }
    fachadas = identificar_fachadas_perpendiculares(nos, 0.0)
    assert "A" in fachadas
    assert "B" in fachadas
    assert "C" not in fachadas
