import sys
import os
import pytest
from pytest import approx
import asyncio

# Ajuste de path para permitir importação dos módulos do backend.
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

def test_dynamic_span_calculation(sample_material, profiles_catalog):
    """
    Valida se o motor calcula o vão livre real L com base na distância entre apoios.
    """
    params = TrussRequest(
        length=15.0, height=2.0, width=1.0, divisions=3,
        load_cases=[]
    )
    profile_indices = {"Padrão": 4}
    
    res = build_and_solve_truss(params, profile_indices, profiles_catalog, sample_material)
    member_results, nodes_results, max_u, total_weight, max_flecha, real_span, max_precamber = res
    
    # O vão deve ser exatamente 15.0 conforme definido na parametrização Howe.
    assert real_span == approx(15.0, rel=1e-4)

@pytest.mark.asyncio
async def test_els_deflection_rejection_and_upscale():
    """
    Cria um cenário onde as barras passam no ELU (U <= 1.0) mas a flecha excede L/250.
    O otimizador deve realizar o upscale automático dos banzos.
    """
    params = TrussRequest(
        length=20.0, height=0.4, width=1.0, divisions=10,
        load_cases=[
            LoadCase(type="G", direction="FY", value=-5000.0),
            LoadCase(type="Q", direction="FY", value=-15000.0)
        ]
    )
    
    response = await optimize_truss_use_case(params)
    
    assert response.is_structurally_stable == True
    for m in response.members:
        if "Banzo" in m.group:
            assert m.profile != "L19x3.18"
