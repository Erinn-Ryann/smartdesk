import pytest
from fastapi.testclient import TestClient
from main import app, heuristic


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return TestClient(app)


def make_ticket(client, msg="Ma facture est erronée, c'est urgent"):
    cid = client.post("/customers", json={"name": "Léa", "email": "lea@ex.fr"}).json()["id"]
    return client.post("/tickets", json={"customer_id": cid, "subject": "Facture", "message": msg}).json()


def test_customer_crud(client):
    cid = client.post("/customers", json={"name": "A", "email": "a@a.fr"}).json()["id"]
    assert client.put(f"/customers/{cid}", json={"name": "B", "email": "a@a.fr"}).json()["name"] == "B"
    assert client.delete(f"/customers/{cid}").status_code == 204
    assert client.get(f"/customers/{cid}").status_code == 404


def test_ticket_requires_existing_customer(client):
    r = client.post("/tickets", json={"customer_id": 99, "subject": "x", "message": "y"})
    assert r.status_code == 404


def test_invalid_status_rejected(client):
    t = make_ticket(client)
    assert client.patch(f"/tickets/{t['id']}", json={"status": "nimporte"}).status_code == 422


def test_analyze_sets_priority_and_stats(client):
    t = make_ticket(client)
    res = client.post(f"/tickets/{t['id']}/analyze").json()
    assert res["priority"] == "haute" and res["topic"] == "facturation"
    assert client.get("/stats").json()["urgentes_a_traiter"] == 1


def test_heuristic_defaults():
    assert heuristic("Bonjour")["priority"] == "normale"
