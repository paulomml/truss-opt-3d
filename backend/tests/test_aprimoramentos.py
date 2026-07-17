"""
Testes dos novos endpoints e funcionalidades adicionadas.

Cobre:
- /api/health com cpu_count
- /api/health/worker (diagnóstico do Celery)
- /api/normas (referência de constantes NBR)
- /api/tarefas (listagem de histórico)
- /api/tarefas/{id}/cancelar via REST
- Campo n_parallel no schema RequisicaoOtimizacao
- Parâmetros avançados do GA no schema
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def cliente():
    """Cliente de teste FastAPI com SQLite em memória."""
    from api.main import app

    with TestClient(app) as c:
        yield c


# /api/health com cpu_count


def test_health_inclui_cpu_count(cliente):
    """/api/health deve retornar cpu_count (inteiro positivo)."""
    r = cliente.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert "cpu_count" in data
    assert isinstance(data["cpu_count"], int)
    assert data["cpu_count"] >= 1
    # Também deve incluir ambiente e celery_max_concorrencia.
    assert "ambiente" in data
    assert "celery_max_concorrencia" in data


# /api/health/worker (diagnóstico)


def test_health_worker_retorna_status(cliente):
    """/api/health/worker deve retornar worker_disponivel booleano.

    Em testes (sem Celery real) o worker não responde, então esperamos
    worker_disponivel=False. O importante é que o endpoint não crasha.
    """
    r = cliente.get("/api/health/worker")
    assert r.status_code == 200
    data = r.json()
    assert "worker_disponivel" in data
    assert isinstance(data["worker_disponivel"], bool)
    # Se indisponível, deve incluir erro explicativo.
    if not data["worker_disponivel"]:
        assert "erro" in data


# /api/normas


def test_normas_retorna_referencia_completa(cliente):
    """/api/normas deve retornar constante das três NBRs + defaults do GA."""
    r = cliente.get("/api/normas")
    assert r.status_code == 200
    data = r.json()

    # NBR 6120
    assert "nbr_6120" in data
    assert data["nbr_6120"]["nome"] == "NBR 6120:2019"
    assert "constantes" in data["nbr_6120"]
    assert "psi_0" in data["nbr_6120"]["constantes"]
    assert "gamma_g" in data["nbr_6120"]["constantes"]
    assert "combinacoes_elu" in data["nbr_6120"]
    assert "combinacoes_els" in data["nbr_6120"]

    # NBR 6123
    assert "nbr_6123" in data
    assert data["nbr_6123"]["nome"] == "NBR 6123:1988"
    assert "pressao_dinamica_coeficiente" in data["nbr_6123"]["constantes"]
    assert "vento_default" in data["nbr_6123"]

    # NBR 8800
    assert "nbr_8800" in data
    assert data["nbr_8800"]["nome"] == "NBR 8800:2008"
    assert "gamma_a1" in data["nbr_8800"]["constantes"]
    assert "flecha_limite_divisor" in data["nbr_8800"]["constantes"]
    assert "equacoes" in data["nbr_8800"]
    assert len(data["nbr_8800"]["equacoes"]) >= 8  # 8 equações esperadas.

    # GA defaults
    assert "ga" in data
    assert "defaults" in data["ga"]
    assert "geracoes" in data["ga"]["defaults"]
    assert "usar_refinamento_local" in data["ga"]["defaults"]


# /api/tarefas (listagem de histórico)


def test_listar_tarefas_vazio_inicialmente(cliente):
    """/api/tarefas deve retornar lista (possivelmente vazia)."""
    r = cliente.get("/api/tarefas")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_listar_tarefas_apos_criacao(cliente):
    """Após criar uma tarefa, ela deve aparecer na listagem."""
    # Cria uma tarefa via POST /api/otimizar.
    payload = {
        "length": 10.0,
        "height": 2.0,
        "width": 0.0,
        "divisions": 4,
        "raw_truss": {
            "nodes": {
                "L0": {"id": "L0", "x": 0, "y": 0, "z": 0, "support": "Pinned"},
                "L1": {"id": "L1", "x": 10, "y": 0, "z": 0, "support": "Roller"},
                "U0": {"id": "U0", "x": 5, "y": 2, "z": 0, "support": "None"},
            },
            "members": [
                {"id": 1, "node_start": "L0", "node_end": "U0", "group": "Diagonal"},
                {"id": 2, "node_start": "L1", "node_end": "U0", "group": "Diagonal"},
                {"id": 3, "node_start": "L0", "node_end": "L1", "group": "Banzo Inferior"},
            ],
        },
    }
    r_post = cliente.post("/api/otimizar", json=payload)
    assert r_post.status_code == 202
    task_id = r_post.json()["task_id"]

    # Lista histórico.
    r = cliente.get("/api/tarefas")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(t["task_id"] == task_id for t in data)

    # Cada item deve ter os campos esperados.
    tarefa = next(t for t in data if t["task_id"] == task_id)
    assert "status" in tarefa
    assert "progresso" in tarefa
    assert "tem_resultado" in tarefa
    assert tarefa["tem_resultado"] is False  # acabou de criar, sem resultado.


def test_listar_tarefas_filtro_por_status(cliente):
    """/api/tarefas?status_filtro=PENDENTE deve filtrar corretamente."""
    r = cliente.get("/api/tarefas?status_filtro=PENDENTE")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # Todos os itens retornados devem ter status PENDENTE.
    for t in data:
        assert t["status"] == "PENDENTE"


# Cancelamento via REST


def test_cancelar_tarefa_via_rest(cliente, monkeypatch):
    """POST /api/tarefas/{id}/cancelar deve marcar como CANCELADO."""
    # Mocka app_celery.control.revoke para não tentar conectar ao Redis real.
    from core import celery_app as celery_module

    def _revoke_mock(task_id, terminate=False):
        return None

    monkeypatch.setattr(celery_module.app_celery.control, "revoke", _revoke_mock)

    # Cria tarefa.
    payload = {
        "length": 10.0,
        "height": 2.0,
        "width": 0.0,
        "divisions": 4,
        "raw_truss": {
            "nodes": {
                "L0": {"id": "L0", "x": 0, "y": 0, "z": 0, "support": "Pinned"},
                "L1": {"id": "L1", "x": 10, "y": 0, "z": 0, "support": "Roller"},
                "U0": {"id": "U0", "x": 5, "y": 2, "z": 0, "support": "None"},
            },
            "members": [
                {"id": 1, "node_start": "L0", "node_end": "U0", "group": "Diagonal"},
                {"id": 2, "node_start": "L1", "node_end": "U0", "group": "Diagonal"},
                {"id": 3, "node_start": "L0", "node_end": "L1", "group": "Banzo Inferior"},
            ],
        },
    }
    r_post = cliente.post("/api/otimizar", json=payload)
    assert r_post.status_code == 202
    task_id = r_post.json()["task_id"]

    # Cancela via REST.
    r_cancel = cliente.post(f"/api/tarefas/{task_id}/cancelar")
    assert r_cancel.status_code == 200
    data = r_cancel.json()
    assert data["status"] == "CANCELADO"

    # Confirma via GET.
    r_get = cliente.get(f"/api/tarefas/{task_id}")
    assert r_get.status_code == 200
    assert r_get.json()["status"] == "CANCELADO"


def test_cancelar_tarefa_inexistente_404(cliente, monkeypatch):
    """Cancelamento de tarefa inexistente deve retornar 404."""
    # Mocka revoke para não tentar conectar ao Redis.
    from core import celery_app as celery_module

    monkeypatch.setattr(
        celery_module.app_celery.control, "revoke", lambda *a, **kw: None
    )

    r = cliente.post("/api/tarefas/999999/cancelar")
    assert r.status_code == 404


# Campo n_parallel e parâmetros avançados do GA no schema


def test_schema_aceita_n_parallel(cliente):
    """POST /api/otimizar deve aceitar n_parallel no payload."""
    payload = {
        "length": 10.0,
        "height": 2.0,
        "width": 0.0,
        "divisions": 4,
        "n_parallel": 2,
        "raw_truss": {
            "nodes": {
                "L0": {"id": "L0", "x": 0, "y": 0, "z": 0, "support": "Pinned"},
                "L1": {"id": "L1", "x": 10, "y": 0, "z": 0, "support": "Roller"},
                "U0": {"id": "U0", "x": 5, "y": 2, "z": 0, "support": "None"},
            },
            "members": [
                {"id": 1, "node_start": "L0", "node_end": "U0", "group": "Diagonal"},
                {"id": 2, "node_start": "L1", "node_end": "U0", "group": "Diagonal"},
                {"id": 3, "node_start": "L0", "node_end": "L1", "group": "Banzo Inferior"},
            ],
        },
    }
    r = cliente.post("/api/otimizar", json=payload)
    assert r.status_code == 202


def test_schema_aceita_parametros_avancados_ga(cliente):
    """POST /api/otimizar deve aceitar todos os parâmetros avançados do GA."""
    payload = {
        "length": 10.0,
        "height": 2.0,
        "width": 0.0,
        "divisions": 4,
        "ag_geracoes": 5,
        "ag_populacao": 8,
        "ag_usar_refinamento_local": False,
        "ag_probabilidade_cruzamento": 0.6,
        "ag_probabilidade_mutacao": 0.15,
        "ag_indice_torneio": 5,
        "ag_max_perfis_distintos": 3,
        "raw_truss": {
            "nodes": {
                "L0": {"id": "L0", "x": 0, "y": 0, "z": 0, "support": "Pinned"},
                "L1": {"id": "L1", "x": 10, "y": 0, "z": 0, "support": "Roller"},
                "U0": {"id": "U0", "x": 5, "y": 2, "z": 0, "support": "None"},
            },
            "members": [
                {"id": 1, "node_start": "L0", "node_end": "U0", "group": "Diagonal"},
                {"id": 2, "node_start": "L1", "node_end": "U0", "group": "Diagonal"},
                {"id": 3, "node_start": "L0", "node_end": "L1", "group": "Banzo Inferior"},
            ],
        },
    }
    r = cliente.post("/api/otimizar", json=payload)
    assert r.status_code == 202


def test_schema_rejeita_n_parallel_invalido(cliente):
    """n_parallel=0 deve ser rejeitado pela validação Pydantic."""
    payload = {
        "length": 10.0,
        "height": 2.0,
        "width": 0.0,
        "divisions": 4,
        "n_parallel": 0,  # inválido: deve ser >= 1
        "raw_truss": {
            "nodes": {
                "L0": {"id": "L0", "x": 0, "y": 0, "z": 0, "support": "Pinned"},
                "L1": {"id": "L1", "x": 10, "y": 0, "z": 0, "support": "Roller"},
                "U0": {"id": "U0", "x": 5, "y": 2, "z": 0, "support": "None"},
            },
            "members": [
                {"id": 1, "node_start": "L0", "node_end": "U0", "group": "Diagonal"},
            ],
        },
    }
    r = cliente.post("/api/otimizar", json=payload)
    assert r.status_code == 422  # Unprocessable Entity (validação falhou).


# Rota Celery: padrão corrigido (não-glob)


def test_celery_rota_corrigida():
    """Confirma que o padrão de rota foi corrigido para o nome exato."""
    from core.celery_app import app_celery

    routes = app_celery.conf.task_routes
    assert "worker.tarefas.otimizar_trelice" in routes
    # Não deve mais conter o padrão antigo com glob.
    assert "worker.tarefas.otimizar_trelice_*" not in routes
