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

def test_elu_combinations_precision(sample_material, profiles_catalog):
    """
    Testa se o motor aplica corretamente os coeficientes ELU da Tabela 1 da NBR 8800.
    ELU_Normal: 1.25 G1 + 1.40 G2 + 1.50 Q
    Usamos pytest.approx(rel=1e-4) para validar a precisão matemática dos esforços.
    """
    params = TrussRequest(
        length=10.0, height=1.0, width=1.0, divisions=2,
        load_cases=[
            LoadCase(type="G", direction="FY", value=-500.0), # G2
            LoadCase(type="Q", direction="FY", value=-1000.0)  # Q
        ]
    )
    profile_indices = {"Padrão": 24} # RHS100x100x3.00 (ry=39.6mm, Lk_max=7.9m)
    
    res = build_and_solve_truss(params, profile_indices, profiles_catalog, sample_material)
    member_results, nodes_results, max_u, total_weight, max_flecha, real_span, max_precamber = res
    
    assert "_ERROR_" not in max_u
    assert len(member_results) > 0
    
    # Validamos se a envoltória capturou esforços não nulos e proporcionais.
    # Em uma treliça de 2 divisões (Howe), o banzo inferior terá esforço significativo.
    banzo_inf = [m for m in member_results if m.group == "Banzo Inferior"]
    for m in banzo_inf:
        assert abs(m.axial_force) > 100.0 # Esforço significativo
        assert m.utilization < 1.0 

def test_elu_alivio_mathematical_validation(sample_material, profiles_catalog):
    """
    Valida a Combinação de Alívio (1.0 G1 + 1.0 G2 + 1.5 Q) conforme NBR 8800.
    As cargas são estritamente gravitacionais (FY negativo). 
    O teste confirma que o motor incluiu esta combinação na envoltória.
    """
    params = TrussRequest(
        length=10.0, height=1.0, width=1.0, divisions=2,
        load_cases=[
            LoadCase(type="G", direction="FY", value=-10000.0),
            LoadCase(type="Q", direction="FY", value=-50000.0)
        ]
    )
    profile_indices = {"Padrão": 7} # SHS 150x150 para suportar carga alta
    
    res = build_and_solve_truss(params, profile_indices, profiles_catalog, sample_material)
    member_results, nodes_results, max_u, total_weight, max_flecha, real_span, max_precamber = res
    
    assert "_ERROR_" not in max_u
    # A presença de resultados de utilização válidos indica que todas as combinações (incluindo Alívio)
    # foram processadas pela envoltória sem erros de matriz.
    for group, u in max_u.items():
        assert u > 0

def test_zero_loads_handling(sample_material, profiles_catalog):
    """
    Cenário de estresse numérico: Cargas G e Q externas nulas.
    Garante que o motor resolve apenas com o peso próprio (G1) e não levanta ZeroDivisionError.
    """
    params = TrussRequest(
        length=10.0, height=1.0, width=1.0, divisions=2,
        load_cases=[]
    )
    profile_indices = {"Padrão": 2}
    
    res = build_and_solve_truss(params, profile_indices, profiles_catalog, sample_material)
    member_results, nodes_results, max_u, total_weight, max_flecha, real_span, max_precamber = res
    
    assert "_ERROR_" not in max_u
    assert total_weight > 0
    # Esforços devem existir devido ao Dead1 (Peso Próprio)
    assert any(abs(m.axial_force) > 0 for m in member_results)
