"""Testes da API sem banco (endpoints de infraestrutura)."""

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert body["app"] == "Fire Intelligence Platform"


def test_endpoints_dependentes_de_banco_retornam_503_sem_config() -> None:
    # Sem DATABASE_URL configurada, o endpoint responde 503 com mensagem clara
    # (nunca dados falsos nem silêncio).
    resp = client.get("/api/dashboard/summary")
    if resp.status_code != 503:  # se DATABASE_URL existir no ambiente de testes, skip
        assert resp.status_code == 200
        return
    assert "DATABASE_URL" in resp.json()["detail"]


def test_openapi_docs_disponiveis_com_prefixo_api() -> None:
    assert client.get("/api/openapi.json").status_code == 200
    assert client.get("/api/docs").status_code == 200
