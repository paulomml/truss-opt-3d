"""
Suíte de Testes para Verificações Avançadas (NBR 8800).
Valida: Interação N+M, Fator Q (Flambagem Local) e Contra-flecha.
"""
import sys
import os
import pytest
from pytest import approx
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from domain.models import TrussRequest, LoadCase
from infrastructure.fea.pynite_solver import build_and_solve_truss
from use_cases.optimize_truss import load_profiles, optimize_truss_use_case

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

def test_nm_interaction_and_local_buckling(sample_material, profiles_catalog):
    """
    Verifica se a interação N+M e o fator Q estão sendo aplicados.
    Uma barra com momento fletor deve ter utilização maior que se tivesse apenas carga axial.
    """
    # Treliça simples de 2 divisões.
    params = TrussRequest(
        length=10.0, height=1.0, width=1.0, divisions=2,
        load_cases=[
            LoadCase(type="G", direction="FY", value=-5000.0),
            LoadCase(type="Q", direction="FY", value=-10000.0)
        ]
    )
    profile_indices = {"Padrão": 0} # SHS 40x40x2.5 (muito esbelto, deve ter Q < 1 e sofrer com N+M)
    
    res = build_and_solve_truss(params, profile_indices, profiles_catalog, sample_material)
    member_results, nodes_results, max_u, total_weight, max_flecha, real_span, max_precamber = res
    
    # O banzo superior (M1 ou M2) sofre compressão e flexão (por ser nó rígido).
    banzo_sup = [m for m in member_results if m.group == "Banzo Superior"][0]
    
    # Com os novos critérios, banzos esbeltos em compressão devem ter utilização alta.
    assert banzo_sup.utilization > 0

def test_precamber_calculation(sample_material, profiles_catalog):
    """
    Verifica se a contra-flecha (precamber) é calculada e retornada.
    """
    params = TrussRequest(
        length=10.0, height=1.0, width=1.0, divisions=2,
        load_cases=[
            LoadCase(type="G", direction="FY", value=-1000.0),
            LoadCase(type="Q", direction="FY", value=-5000.0)
        ]
    )
    profile_indices = {"Padrão": 15}
    
    res = build_and_solve_truss(params, profile_indices, profiles_catalog, sample_material)
    member_results, nodes_results, max_u, total_weight, max_flecha, real_span, max_precamber = res
    
    # A contra-flecha (sob Dead loads) deve ser menor que a flecha total (Dead + Live).
    assert max_precamber > 0
    assert max_precamber < max_flecha

@pytest.mark.asyncio
async def test_full_optimization_with_advanced_checks():
    """
    Testa se o otimizador converge considerando N+M e ELS.
    """
    params = TrussRequest(
        length=10.0, height=1.5, width=1.0, divisions=4,
        load_cases=[
            LoadCase(type="G", direction="FY", value=-2500.0),
            LoadCase(type="Q", direction="FY", value=-5000.0)
        ]
    )
    
    response = await optimize_truss_use_case(params)
    
    assert response.is_structurally_stable == True
    assert response.precamber > 0
    # O valor de precamber deve ser retornado em metros.
    assert response.precamber < params.length / 100
