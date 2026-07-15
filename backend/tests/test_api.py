"""
Testes de integração da API FastAPI.

Validam os endpoints REST com banco SQLite em memória.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def cliente():
    """Cliente de teste FastAPI com SQLite em memória."""
    from api.main import app
    with TestClient(app) as c:
        yield c


def test_health_check(cliente):
    """Health check deve retornar 200 e status ok."""
    r = cliente.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


def test_listar_materiais(cliente):
    """Deve retornar a lista de materiais cadastrados."""
    r = cliente.get("/api/materiais")
    assert r.status_code == 200
    mats = r.json()
    assert isinstance(mats, list)
    assert len(mats) >= 6  # 6 materiais padrão no seed.
    nomes = [m["nome"] for m in mats]
    assert "A36" in nomes
    assert "MR350" in nomes


def test_listar_perfis(cliente):
    """Deve retornar a lista de perfis cadastrados."""
    r = cliente.get("/api/perfis")
    assert r.status_code == 200
    perfis = r.json()
    assert isinstance(perfis, list)
    assert len(perfis) >= 25  # ~32 perfis padrão.


def test_listar_perfis_por_familia(cliente):
    """Deve filtrar perfis por família."""
    r = cliente.get("/api/perfis?familia=RHS")
    assert r.status_code == 200
    perfis = r.json()
    assert all(p["familia"] == "RHS" for p in perfis)
    assert len(perfis) >= 5  # Pelo menos 5 RHS no catálogo.


def test_criar_tarefa_otimizacao(cliente):
    """POST /api/otimizar deve criar uma tarefa e retornar 202."""
    payload = {
        "length": 12.0,
        "height": 2.5,
        "width": 2.0,
        "divisions": 6,
        "soil_type": "Rocha",
        "footing_b": 0.6,
        "footing_l": 0.6,
        "water_lamina": 0.0,
        "load_cases": [
            {"type": "G", "direction": "FY", "value": -2000.0},
            {"type": "Q", "direction": "FY", "value": -3000.0},
        ],
        "raw_truss": {
            "nodes": {
                "L0": {"id": "L0", "x": 0, "y": 0, "z": 0, "support": "Pinned"},
                "L1": {"id": "L1", "x": 2, "y": 0, "z": 0, "support": "Roller"},
                "U0": {"id": "U0", "x": 0, "y": 1.5, "z": 0, "support": "None"},
                "U1": {"id": "U1", "x": 2, "y": 1.5, "z": 0, "support": "None"},
            },
            "members": [
                {"id": 1, "node_start": "L0", "node_end": "L1", "group": "Banzo Inferior"},
                {"id": 2, "node_start": "U0", "node_end": "U1", "group": "Banzo Superior"},
                {"id": 3, "node_start": "L0", "node_end": "U0", "group": "Montante"},
                {"id": 4, "node_start": "L1", "node_end": "U1", "group": "Montante"},
                {"id": 5, "node_start": "L0", "node_end": "U1", "group": "Diagonal"},
            ],
        },
    }
    r = cliente.post("/api/otimizar", json=payload)
    assert r.status_code == 202
    data = r.json()
    assert "task_id" in data
    assert data["status"] in ("PENDENTE", "EM_ANDAMENTO")


def test_consultar_tarefa_inexistente(cliente):
    """GET de tarefa inexistente deve retornar 404."""
    r = cliente.get("/api/tarefas/999999")
    assert r.status_code == 404
