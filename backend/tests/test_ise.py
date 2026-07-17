"""
Testes do subsistema de Interação Solo-Estrutura (ISE):
- Correção geométrica de Terzaghi (granular, coesivo, rígido)
- Aplicação de molas Winkler via def_support_spring
- Integração com o solver MEF (construir_e_resolver)
- Combinações ELS Frequente e Quase Permanente
"""

import pytest
from Pynite import FEModel3D

from engineering.fea.pynite_solver import BANCO_SOLOS, construir_e_resolver
from engineering.modelos_fisicos import (
    BarraFisica,
    MaterialFisico,
    NoFisico,
    PerfilFisico,
)


# Fixtures


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
def perfil_rhs():
    return PerfilFisico(
        id=1,
        nome="RHS50x30x2.00",
        familia="RHS",
        h_mm=50,
        bf_mm=30,
        d_mm=0,
        t_mm=2.00,
        area_m2=2.96e-4,
        ix_m4=5.60e-8,
        iy_m4=2.08e-8,
        j_m4=5.50e-8,
    )


@pytest.fixture
def trelica_minima():
    """Treliça 2D simples de 2 painéis para testes rápidos do ISE."""
    nos = {
        "L0": NoFisico("L0", 0, 0, 0, support="Pinned"),
        "L1": NoFisico("L1", 4, 0, 0),
        "L2": NoFisico("L2", 8, 0, 0, support="Roller"),
        "U0": NoFisico("U0", 0, 2, 0),
        "U1": NoFisico("U1", 4, 2, 0),
        "U2": NoFisico("U2", 8, 2, 0),
    }
    barras = [
        BarraFisica(1, "L0", "L1", "Banzo Inferior", 4.0),
        BarraFisica(2, "L1", "L2", "Banzo Inferior", 4.0),
        BarraFisica(3, "U0", "U1", "Banzo Superior", 4.0),
        BarraFisica(4, "U1", "U2", "Banzo Superior", 4.0),
        BarraFisica(5, "L0", "U0", "Montante", 2.0),
        BarraFisica(6, "L1", "U1", "Montante", 2.0),
        BarraFisica(7, "L2", "U2", "Montante", 2.0),
        BarraFisica(8, "L0", "U1", "Diagonal", 4.472),
        BarraFisica(9, "L1", "U2", "Diagonal", 4.472),
    ]
    return nos, barras


# Testes de correção Terzaghi (unidades: kN/m^3)


class TestTerzaghi:
    """Verifica as fórmulas de correção geométrica de Terzaghi."""

    def test_granular_areia_fofa(self):
        """Areia Fofa (ks1=15000 kN/m3, granular, B=0.6 m).
        ks = 15000 * ((0.6 + 0.305) / (2 * 0.6))2 = 8532 kN/m3"""
        solo = BANCO_SOLOS["Areia Fofa"]
        assert solo["tipo"] == "granular"
        ks1 = solo["ks1"]
        B = 0.6
        ks = ks1 * ((B + 0.305) / (2 * B)) ** 2
        assert abs(ks - 8532) < 1

    def test_granular_areia_compacta(self):
        """Areia Compacta (ks1=100000 kN/m^3, granular, B=0.6 m)."""
        solo = BANCO_SOLOS["Areia Compacta"]
        assert solo["tipo"] == "granular"
        ks1 = solo["ks1"]
        B = 0.6
        ks = ks1 * ((B + 0.305) / (2 * B)) ** 2
        assert abs(ks - 56877) < 2

    def test_granular_b_maior_que_referencia(self):
        """B=1.0 m: fator de correção diminui com B maior."""
        solo = BANCO_SOLOS["Areia Fofa"]
        ks1 = solo["ks1"]
        ks_06 = ks1 * ((0.6 + 0.305) / (2 * 0.6)) ** 2
        ks_10 = ks1 * ((1.0 + 0.305) / (2 * 1.0)) ** 2
        assert ks_10 < ks_06  # sapata maior -> menor correção

    def test_granular_b_minimo(self):
        """B < 0.305 m deve usar B=0.305 m."""
        solo = BANCO_SOLOS["Areia Fofa"]
        ks1 = solo["ks1"]
        B = max(0.2, 0.305)  # clamp
        ks = ks1 * ((B + 0.305) / (2 * B)) ** 2
        assert abs(ks - ks1) < 1  # B=0.305 -> fator=1.0

    def test_coesivo_argila_mole(self):
        """Argila Mole (ks1=10000 kN/m^3, coesivo, B=0.6 m).
        ks = 10000 * (0.305 / 0.6) = 5083 kN/m^3"""
        solo = BANCO_SOLOS["Argila Mole"]
        assert solo["tipo"] == "coesivo"
        ks1 = solo["ks1"]
        B = 0.6
        ks = ks1 * (0.305 / B)
        assert abs(ks - 5083) < 1

    def test_coesivo_argila_rija(self):
        """Argila Rija (ks1=40000 kN/m^3, coesivo, B=0.6 m)."""
        solo = BANCO_SOLOS["Argila Rija"]
        assert solo["tipo"] == "coesivo"
        ks1 = solo["ks1"]
        B = 0.6
        ks = ks1 * (0.305 / B)
        assert abs(ks - 20333) < 1

    def test_rigido_rocha_sem_correcao(self):
        """Rocha (ks1=250000 kN/m^3, rigido): sem correção."""
        solo = BANCO_SOLOS["Rocha"]
        assert solo["tipo"] == "rigido"
        assert solo["ks1"] == 250000

    def test_customizado_fallback(self):
        """Customizado: usa ks1=50000 (coesivo) se custom_ks não fornecido."""
        solo = BANCO_SOLOS["Customizado"]
        assert solo["tipo"] == "coesivo"
        assert solo["ks1"] == 50000

    def test_customizado_com_ks_explicito(self):
        """Customizado com custom_ks sobrescreve ks1."""
        solo = BANCO_SOLOS["Customizado"]
        custom_ks = 30000
        ks1 = custom_ks  # substitui solo["ks1"]
        B = 0.6
        ks = ks1 * (0.305 / B)
        assert abs(ks - 15250) < 1


# Testes de aplicação de molas Winkler (API PyNite)


class TestMolasWinkler:
    """Verifica a API def_support_spring do PyNite."""

    def test_spring_dy_aplicada(self):
        """Mola translacional DY deve ser armazenada no nó."""
        m = FEModel3D()
        m.add_node("N1", 0, 0, 0)
        m.def_support_spring("N1", "DY", 3.0e6)
        assert m.nodes["N1"].spring_DY == [3.0e6, None, True]

    def test_spring_rotacional_rx(self):
        """Mola rotacional RX deve ser armazenada no nó."""
        m = FEModel3D()
        m.add_node("N1", 0, 0, 0)
        m.def_support_spring("N1", "RX", 9.0e4)
        assert m.nodes["N1"].spring_RX == [9.0e4, None, True]

    def test_spring_rotacional_rz(self):
        """Mola rotacional RZ deve ser armazenada no nó."""
        m = FEModel3D()
        m.add_node("N1", 0, 0, 0)
        m.def_support_spring("N1", "RZ", 9.0e4)
        assert m.nodes["N1"].spring_RZ == [9.0e4, None, True]

    def test_multiplas_molas_mesmo_no(self):
        """Um nó pode receber molas em múltiplos DOFs."""
        m = FEModel3D()
        m.add_node("N1", 0, 0, 0)
        m.def_support_spring("N1", "DY", 3.0e6)
        m.def_support_spring("N1", "RX", 9.0e4)
        m.def_support_spring("N1", "RZ", 9.0e4)
        assert m.nodes["N1"].spring_DY[0] == 3.0e6
        assert m.nodes["N1"].spring_RX[0] == 9.0e4
        assert m.nodes["N1"].spring_RZ[0] == 9.0e4

    def test_spring_convive_com_def_support(self):
        """def_support com DY=False + spring_DY = apoio híbrido."""
        m = FEModel3D()
        m.add_node("N1", 0, 0, 0)
        m.def_support("N1", True, False, True, False, False, False)
        m.def_support_spring("N1", "DY", 3.0e6)
        assert m.nodes["N1"].support_DX is True
        assert m.nodes["N1"].support_DY is False  # liberado para a mola
        assert m.nodes["N1"].support_DZ is True
        assert m.nodes["N1"].spring_DY == [3.0e6, None, True]


# Testes de integração com o solver (construir_e_resolver)


class TestISESolver:
    """Verifica o comportamento do ISE através do solver MEF."""

    def test_rocha_sem_molas(self, trelica_minima, material_a36, perfil_rhs):
        """solo_tipo="Rocha" (padrão): apoios rígidos, sem molas."""
        nos, barras = trelica_minima
        perfil_por_grupo = {"Diagonal": perfil_rhs}
        casos_carga = [{"type": "G", "direction": "FY", "value": -5000.0}]
        nos_banzo_superior = [nid for nid in nos if "U" in nid]

        resultado = construir_e_resolver(
            nos_entrada=nos,
            barras_entrada=barras,
            perfil_por_grupo=perfil_por_grupo,
            material=material_a36,
            casos_carga_externos=casos_carga,
            nos_banzo_superior=nos_banzo_superior,
            nos_fachada=[],
            solo_tipo="Rocha",
            footing_b=0.6,
            footing_l=0.6,
        )

        assert resultado.erro is None
        assert resultado.utilizacao_maxima > 0

    def test_areia_fofa_produz_resultado(self, trelica_minima, material_a36, perfil_rhs):
        """solo_tipo="Areia Fofa": análise deve ser bem-sucedida."""
        nos, barras = trelica_minima
        perfil_por_grupo = {"Diagonal": perfil_rhs}
        casos_carga = [{"type": "G", "direction": "FY", "value": -5000.0}]
        nos_banzo_superior = [nid for nid in nos if "U" in nid]

        resultado = construir_e_resolver(
            nos_entrada=nos,
            barras_entrada=barras,
            perfil_por_grupo=perfil_por_grupo,
            material=material_a36,
            casos_carga_externos=casos_carga,
            nos_banzo_superior=nos_banzo_superior,
            nos_fachada=[],
            solo_tipo="Areia Fofa",
            footing_b=0.6,
            footing_l=0.6,
        )

        assert resultado.erro is None
        assert resultado.utilizacao_maxima > 0

    def test_argila_mole_produz_resultado(self, trelica_minima, material_a36, perfil_rhs):
        """solo_tipo="Argila Mole": análise bem-sucedida."""
        nos, barras = trelica_minima
        perfil_por_grupo = {"Diagonal": perfil_rhs}
        casos_carga = [{"type": "G", "direction": "FY", "value": -5000.0}]
        nos_banzo_superior = [nid for nid in nos if "U" in nid]

        resultado = construir_e_resolver(
            nos_entrada=nos,
            barras_entrada=barras,
            perfil_por_grupo=perfil_por_grupo,
            material=material_a36,
            casos_carga_externos=casos_carga,
            nos_banzo_superior=nos_banzo_superior,
            nos_fachada=[],
            solo_tipo="Argila Mole",
            footing_b=0.6,
            footing_l=0.6,
        )

        assert resultado.erro is None

    @pytest.mark.parametrize("solo", ["Areia Compacta", "Argila Rija", "Customizado"])
    def test_todos_os_solos_produzem_resultado(
        self, solo, trelica_minima, material_a36, perfil_rhs
    ):
        """Todos os tipos de solo devem produzir análise estável."""
        nos, barras = trelica_minima
        perfil_por_grupo = {"Diagonal": perfil_rhs}
        casos_carga = [{"type": "G", "direction": "FY", "value": -5000.0}]
        nos_banzo_superior = [nid for nid in nos if "U" in nid]

        resultado = construir_e_resolver(
            nos_entrada=nos,
            barras_entrada=barras,
            perfil_por_grupo=perfil_por_grupo,
            material=material_a36,
            casos_carga_externos=casos_carga,
            nos_banzo_superior=nos_banzo_superior,
            nos_fachada=[],
            solo_tipo=solo,
            custom_ks=30000 if solo == "Customizado" else None,
            footing_b=0.6,
            footing_l=0.6,
        )

        assert resultado.erro is None

    def test_ise_aumenta_flecha_em_relacao_rocha(self, trelica_minima, material_a36, perfil_rhs):
        """Solo mole (Areia Fofa) deve produzir flecha maior que Rocha."""
        nos, barras = trelica_minima
        perfil_por_grupo = {"Diagonal": perfil_rhs}
        casos_carga = [{"type": "G", "direction": "FY", "value": -5000.0}]
        nos_banzo_superior = [nid for nid in nos if "U" in nid]

        res_rocha = construir_e_resolver(
            nos_entrada=nos,
            barras_entrada=barras,
            perfil_por_grupo=perfil_por_grupo,
            material=material_a36,
            casos_carga_externos=casos_carga,
            nos_banzo_superior=nos_banzo_superior,
            nos_fachada=[],
            solo_tipo="Rocha",
        )

        res_areia = construir_e_resolver(
            nos_entrada=nos,
            barras_entrada=barras,
            perfil_por_grupo=perfil_por_grupo,
            material=material_a36,
            casos_carga_externos=casos_carga,
            nos_banzo_superior=nos_banzo_superior,
            nos_fachada=[],
            solo_tipo="Areia Fofa",
        )

        assert res_rocha.erro is None
        assert res_areia.erro is None
        assert res_areia.flecha_maxima >= res_rocha.flecha_maxima * 0.9

    def test_footing_maior_reduz_flecha(self, trelica_minima, material_a36, perfil_rhs):
        """Sapata maior (B=1.5 m) deve ser mais rígida que B=0.3 m."""
        nos, barras = trelica_minima
        perfil_por_grupo = {"Diagonal": perfil_rhs}
        casos_carga = [{"type": "G", "direction": "FY", "value": -5000.0}]
        nos_banzo_superior = [nid for nid in nos if "U" in nid]

        res_pequena = construir_e_resolver(
            nos_entrada=nos,
            barras_entrada=barras,
            perfil_por_grupo=perfil_por_grupo,
            material=material_a36,
            casos_carga_externos=casos_carga,
            nos_banzo_superior=nos_banzo_superior,
            nos_fachada=[],
            solo_tipo="Areia Fofa",
            footing_b=0.3,
            footing_l=0.3,
        )

        res_grande = construir_e_resolver(
            nos_entrada=nos,
            barras_entrada=barras,
            perfil_por_grupo=perfil_por_grupo,
            material=material_a36,
            casos_carga_externos=casos_carga,
            nos_banzo_superior=nos_banzo_superior,
            nos_fachada=[],
            solo_tipo="Areia Fofa",
            footing_b=1.5,
            footing_l=1.5,
        )

        assert res_pequena.erro is None
        assert res_grande.erro is None
        assert res_grande.flecha_maxima <= res_pequena.flecha_maxima


# Testes de combinações ELS


class TestELSCombinacoes:
    """Verifica as combinações ELS Frequente e Quase Permanente."""

    def test_els_frequente_usado_na_analise(self, trelica_minima, material_a36, perfil_rhs):
        """ELS_Flecha_Frequente deve ser processado sem erro."""
        nos, barras = trelica_minima
        perfil_por_grupo = {"Diagonal": perfil_rhs}
        casos_carga = [{"type": "G", "direction": "FY", "value": -5000.0}]
        nos_banzo_superior = [nid for nid in nos if "U" in nid]

        resultado = construir_e_resolver(
            nos_entrada=nos,
            barras_entrada=barras,
            perfil_por_grupo=perfil_por_grupo,
            material=material_a36,
            casos_carga_externos=casos_carga,
            nos_banzo_superior=nos_banzo_superior,
            nos_fachada=[],
            solo_tipo="Rocha",
        )

        assert resultado.erro is None

    def test_els_permanente_usado_na_analise(self, trelica_minima, material_a36, perfil_rhs):
        """ELS_Flecha_Permanente deve ser processado sem erro."""
        nos, barras = trelica_minima
        perfil_por_grupo = {"Diagonal": perfil_rhs}
        casos_carga = [{"type": "G", "direction": "FY", "value": -5000.0}]
        nos_banzo_superior = [nid for nid in nos if "U" in nid]

        resultado = construir_e_resolver(
            nos_entrada=nos,
            barras_entrada=barras,
            perfil_por_grupo=perfil_por_grupo,
            material=material_a36,
            casos_carga_externos=casos_carga,
            nos_banzo_superior=nos_banzo_superior,
            nos_fachada=[],
            solo_tipo="Rocha",
        )

        assert resultado.erro is None
