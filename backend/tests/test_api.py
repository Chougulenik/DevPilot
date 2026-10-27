from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert data["api_v1"] == "/api/v1"


def test_health_endpoints():
    res1 = client.get("/api/v1/health")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "healthy"
    assert "document_count" in data1
    assert "chunk_count" in data1

    res2 = client.get("/api/v1/health/stats")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "online"
    assert "active_embedding_model" in data2


def test_documents_list_endpoint():
    res = client.get("/api/v1/documents")
    assert res.status_code == 200
    data = res.json()
    assert "documents" in data
    assert "total_documents" in data
    assert isinstance(data["documents"], list)


def test_retrieval_validation():
    # Empty query should fail with 400
    res = client.post("/api/v1/retrieval/query", json={"query": "", "strategy": "vector"})
    assert res.status_code == 400


def test_chat_validation():
    # Empty message should fail with 400
    res = client.post("/api/v1/chat/completions", json={"message": "", "history": []})
    assert res.status_code == 400
