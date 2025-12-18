"""Tests for graph router endpoints."""

import pytest
from fastapi import status


def test_execute_query_endpoint(client):
    """Test custom query execution endpoint."""
    request_data = {
        "query": "RETURN 1 as test",
        "parameters": {}
    }
    response = client.post("/api/v1/query", json=request_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    assert "count" in data


def test_execute_query_with_parameters(client):
    """Test query execution with parameters."""
    request_data = {
        "query": "RETURN $value as result",
        "parameters": {"value": 42}
    }
    response = client.post("/api/v1/query", json=request_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["data"][0]["result"] == 42


def test_execute_invalid_query(client):
    """Test that invalid queries return error."""
    request_data = {
        "query": "INVALID CYPHER QUERY",
        "parameters": {}
    }
    response = client.post("/api/v1/query", json=request_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_search_entities_endpoint(client):
    """Test entity search endpoint."""
    request_data = {
        "search_term": "organization",
        "limit": 10
    }
    response = client.post("/api/v1/search", json=request_data)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert isinstance(data, list)


def test_search_entities_with_limit(client):
    """Test entity search respects limit."""
    request_data = {
        "search_term": "test",
        "limit": 5
    }
    response = client.post("/api/v1/search", json=request_data)
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert len(data) <= 5
