"""
Testes unitários das verificações NBR 8800.

Cobrem:
- Esbeltez máxima (compressão e tração).
- Fator Q (flambagem local).
- Fator χ (flambagem global).
- Interação N + M (Item 5.5.1.2).
- Verificação ELS (flecha).
"""
import math

import pytest

from engineering.modelos_fisicos import BarraFisica, MaterialFisico, PerfilFisico
from engineering.standards.nbr_8800 import (
    calcular_fator_chi,
    calcular_fator_q,
    calcular_n_rd,
    verificar_barra_nbr8800,
    verificar_flecha_els,
)


@pytest.fixture
def material_a36():
    """Material A36 padrão para testes."""
    return MaterialFisico(
        nome="A36",
        e_gpa=200.0, g_gpa=76.9, nu=0.30,
        fy_mpa=250.0, fu_mpa=400.0, rho_kg_m3=7850.0,
        custo_kg=8.45,
    )


@pytest.fixture
def perfil_l25():
    """Cantoneira L25x3.18 para testes."""
    return PerfilFisico(
        id=1, nome="L25x3.18", familia="L",
        h_mm=25, bf_mm=25, d_mm=0, t_mm=3.18,
        area_m2=1.49e-4, ix_m4=7.49e-9, iy_m4=7.49e-9, j_m4=5.02e-10,
    )


def test_esbeltez_maxima_compressao(material_a36, perfil_l25):
    """Barra com λ > 200 em compressão deve retornar U = 999."""
    barra = BarraFisica(
        id=1, node_start="A", node_end="B",
        group="Diagonal", length=2.5,
        axial_force=-1000.0,  # compressão
    )
    # lk = 2.5 m; raio de giração ≈ 7.1 mm; λ ≈ 350.
    resultado = verificar_barra_nbr8800(barra, perfil_l25, material_a36)
    assert resultado.utilization == 999.0
    assert resultado.violacao_normativa


def test_esbeltez_maxima_tracao(material_a36, perfil_l25):
    """Barra com λ > 300 em tração deve retornar U = 999."""
    barra = BarraFisica(
        id=1, node_start="A", node_end="B",
        group="Diagonal", length=2.5,
        axial_force=1000.0,  # tração
    )
    resultado = verificar_barra_nbr8800(barra, perfil_l25, material_a36)
    assert resultado.utilization == 999.0


def test_fator_q_secao_compacta(material_a36, perfil_l25):
    """Seção compacta (b/t < λr) deve ter Q = 1.0."""
    q = calcular_fator_q(perfil_l25, material_a36)
    assert q == 1.0


def test_fator_q_seção_esbelta(material_a36):
    """Seção muito esbelta (b/t > λr) deve ter Q < 1.0."""
    perfil_esbelto = PerfilFisico(
        id=2, nome="Test_Esbelto", familia="L",
        h_mm=100, bf_mm=100, d_mm=0, t_mm=1.0,  # b/t = 100
        area_m2=4e-4, ix_m4=1e-7, iy_m4=1e-7, j_m4=1e-9,
    )
    q = calcular_fator_q(perfil_esbelto, material_a36)
    assert 0 < q < 1.0


def test_fator_chi_decrece_com_esbeltez(material_a36, perfil_l25):
    """χ deve diminuir à medida que Lk aumenta."""
    chi_curto, _, _ = calcular_fator_chi(perfil_l25, material_a36, 0.5, 0.5, 1.0)
    chi_longo, _, _ = calcular_fator_chi(perfil_l25, material_a36, 2.0, 2.0, 1.0)
    assert chi_curto > chi_longo


def test_n_rd_tracao_vs_compressao(material_a36, perfil_l25):
    """N_rd de tração deve ser ≥ N_rd de compressão (devido a χ)."""
    chi, _, _ = calcular_fator_chi(perfil_l25, material_a36, 1.0, 1.0, 1.0)
    n_rd_tracao = calcular_n_rd(perfil_l25, material_a36, chi, 1.0, tracao=True)
    n_rd_compressao = calcular_n_rd(perfil_l25, material_a36, chi, 1.0, tracao=False)
    assert n_rd_tracao >= n_rd_compressao


def test_interacao_nm_alta_compressao(material_a36, perfil_l25):
    """Barra com N/N_rd ≥ 0.2 deve usar Eq. 5.5.1.2-a."""
    barra = BarraFisica(
        id=1, node_start="A", node_end="B",
        group="Banzo", length=1.0,
        axial_force=-20000.0,  # alta compressão
        mz=50.0, my=0.0,
    )
    resultado = verificar_barra_nbr8800(barra, perfil_l25, material_a36)
    assert "5.5.1.2-a" in resultado.detalhes or resultado.utilization > 1.0


def test_verificacao_flecha_els_atendida():
    """Flecha dentro do limite deve retornar atendido=True."""
    atendido, _, _ = verificar_flecha_els(0.01, 5.0, limite_divisor=250.0)
    assert atendido


def test_verificacao_flecha_els_violada():
    """Flecha acima do limite deve retornar atendido=False."""
    atendido, _, msg = verificar_flecha_els(0.05, 5.0, limite_divisor=250.0)
    assert not atendido
    assert "violado" in msg.lower()
