"""Testes do endpoint administrativo (sem banco).

Verifica: desabilitado por padrão, token inválido e exigência de token.
(O caminho de sucesso exige banco real — testado no deploy.)"""

from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.app.main import app

client = TestClient(app)


def test_migrate_disabled_by_default() -> None:
    resp = client.post("/api/admin/migrate", headers={"X-Admin-Token": "qualquer"})
    assert resp.status_code == 403
    assert "ADMIN_ENABLED" in resp.json()["detail"]


def test_migrate_requer_token() -> None:
    with patch("backend.app.api.admin.get_settings") as mock:
        settings = mock.return_value
        settings.admin_enabled = True
        settings.admin_token = "FRUTA"
        resp = client.post("/api/admin/migrate", headers={"X-Admin-Token": "errado"})
        assert resp.status_code == 401
