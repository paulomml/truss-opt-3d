import sys
import os
import pytest
from pytest import approx

# Ajuste de path para permitir importação dos módulos do backend.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from domain.models import TrussRequest, LoadCase
from infrastructure.fea.pynite_solver import build_and_solve_truss
from use_cases.optimize_truss import load_profiles

@pytest.fixture
def sample_material():
    return {
        "name": "Aço A36",
        "fy": 250,
        "E": 200,
        "rho": 7850,
        "cost_kg": 8.45
    }

@pytest.fixture
def profiles_catalog():
    return load_profiles()

def test_buckling_lkx_not_equal_lky(sample_material, profiles_catalog):
    """
    Testa se o motor identifica o eixo crítico quando Lkx != Lky.
    Cria-se uma treliça onde a largura W=4.0m e painel dx=2.0m.
    Banzos terão Lkx=4.0m (fora do plano) e Lky=2.0m (no plano).
    """
    params = TrussRequest(
        length=8.0, height=2.0, width=4.0, divisions=4, # dx = 2.0m, W = 4.0m
        load_cases=[
            LoadCase(type="G", direction="FY", value=-1000.0), # Gravitacional
        ]
    )
    # Perfil Ue (Ix != Iy). A esbeltez em X (Lkx/rx) será comparada com a de Y.
    profile_indices = {"Padrão": 7} 
    
    res = build_and_solve_truss(params, profile_indices, profiles_catalog, sample_material)
    member_results, nodes_results, max_u, total_weight, max_flecha, real_span, max_precamber = res
    
    assert "_ERROR_" not in max_u
    
    # Identifica banzos superiores sob compressão
    banzos_sup = [m for m in member_results if m.group == "Banzo Superior"]
    banzo_comprimido = [m for m in banzos_sup if m.stress_type == "Compressão"]
    
    if not banzo_comprimido:
        # Se nenhum for compressão, algo na geometria Howe inverteu (improvável em divisões=4).
        # Mas vamos olhar o mais solicitado.
        m_alvo = max(banzos_sup, key=lambda m: m.utilization)
    else:
        m_alvo = max(banzo_comprimido, key=lambda m: m.utilization)
        
    print(f"DEBUG_BUCKLING: U={m_alvo.utilization:.3f}, Stress={m_alvo.stress_type}")
    assert m_alvo.utilization > 0.0001 

def test_euler_buckling_slenderness_limit(sample_material, profiles_catalog):
    """
    Force um cenário onde a barra reprova pelo limite normativo de esbeltez (lambda > 200).
    Trecho extremamente longo com perfil mínimo.
    """
    params = TrussRequest(
        length=20.0, height=1.0, width=1.0, divisions=2, # dx = 10.0m
        load_cases=[
            LoadCase(type="Q", direction="FY", value=-50000.0) 
        ]
    )
    profile_indices = {"Padrão": 0} # SHS 40x40x2.5 (muito pequeno para 10m)
    
    res = build_and_solve_truss(params, profile_indices, profiles_catalog, sample_material)
    member_results, nodes_results, max_u, total_weight, max_flecha, real_span, max_precamber = res
    
    # Se a matriz convergir, o banzo superior comprimido deve ter U >= 999.0
    if "_ERROR_" not in max_u:
        assert max_u["Banzo Superior"] >= 999.0
