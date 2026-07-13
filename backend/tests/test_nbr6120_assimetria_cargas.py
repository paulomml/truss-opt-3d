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

def test_concentrated_asymmetric_load(sample_material, profiles_catalog):
    """
    Testa a carga concentrada gravitacional (FY negativo) em um único nó fora do centro (FU1).
    Valida se a força axial na diagonal do painel carregado é substancialmente 
    maior que na diagonal do lado oposto simétrico (FU3).
    """
    params = TrussRequest(
        length=10.0, height=1.0, width=1.0, divisions=4,
        load_cases=[
            LoadCase(type="Q", direction="FY", value=-20000.0, nodes=["FU1"]) 
        ]
    )
    profile_indices = {"Padrão": 10} # Ue100x40x15x2.65
    
    res = build_and_solve_truss(params, profile_indices, profiles_catalog, sample_material)
    member_results, nodes_results, max_u, total_weight, max_flecha, real_span, max_precamber = res
    
    assert "_ERROR_" not in max_u
    
    # Isolar diagonais. Em divisões=4, costumam ser as barras de IDs médios.
    # Vamos identificar pela posição X dos nós de início/fim.
    diag_esquerda = [m for m in member_results if m.group == "Diagonal" and nodes_results[m.node_start].x < 3.0][0]
    diag_direita = [m for m in member_results if m.group == "Diagonal" and nodes_results[m.node_start].x > 7.0][0]
    
    force_esq = abs(diag_esquerda.axial_force)
    force_dir = abs(diag_direita.axial_force)
    
    # A carga no nó 1 deve gerar um cortante muito maior na diagonal do primeiro painel.
    assert force_esq > force_dir * 2.0

def test_partial_distributed_load(sample_material, profiles_catalog):
    """
    Simula uma sobrecarga Q (FY negativo) ocupando apenas a metade esquerda do vão.
    Verifica se a reação de apoio e os esforços nos banzos refletem essa assimetria.
    """
    params = TrussRequest(
        length=12.0, height=1.5, width=1.0, divisions=6,
        load_cases=[
            LoadCase(
                type="Q", direction="FY", value=-30000.0, 
                nodes=["FU0", "FU1", "FU2", "FU3", "BU0", "BU1", "BU2", "BU3"] # Metade esquerda, ambos os lados
            )
        ]
    )
    profile_indices = {"Padrão": 5}
    
    res = build_and_solve_truss(params, profile_indices, profiles_catalog, sample_material)
    member_results, nodes_results, max_u, total_weight, max_flecha, real_span, max_precamber = res
    
    assert "_ERROR_" not in max_u
    
    # Envoltória de banzos inferiores.
    banzos_inf = [m for m in member_results if m.group == "Banzo Inferior"]
    
    # Pegamos o primeiro (esquerda) e o último (direita).
    banzo_esq = sorted(banzos_inf, key=lambda m: nodes_results[m.node_start].x)[0]
    banzo_dir = sorted(banzos_inf, key=lambda m: nodes_results[m.node_start].x)[-1]
    
    print(f"DEBUG_ASYM: Esq={banzo_esq.axial_force:.1f}, Dir={banzo_dir.axial_force:.1f}")
    
    # Esforços devem ser diferentes. 
    # Em uma treliça Howe carregada na metade esquerda, as reações e esforços de banzos nos extremos
    # são simétricos se as reações forem iguais? No, reações são diferentes!
    # Reação em FL0 (esquerda) deve ser maior que em FL6 (direita).
    diff = abs(abs(banzo_esq.axial_force) - abs(banzo_dir.axial_force))
    assert diff > 500.0 # Diferença significativa esperada (1.1 kN)
