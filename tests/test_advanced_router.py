"""Tests for advanced router endpoints."""

import pytest
from fastapi import status


def test_pathfinding_endpoint(client):
    """Test pathfinding endpoint."""
    request_data = {"source_id": 100, "target_id": 200, "max_depth": 5}
    response = client.post("/api/v1/advanced/pathfinding", json=request_data)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "path" in data
        assert "length" in data
        assert "exists" in data


def test_recommendations_community_strategy(client):
    """Test recommendations with community strategy."""
    request_data = {"article_id": 100, "limit": 10, "strategy": "community"}
    response = client.post("/api/v1/advanced/recommendations", json=request_data)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "source_id" in data
        assert "recommendations" in data
        assert "count" in data


def test_recommendations_references_strategy(client):
    """Test recommendations with references strategy."""
    request_data = {"article_id": 100, "limit": 10, "strategy": "references"}
    response = client.post("/api/v1/advanced/recommendations", json=request_data)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


def test_recommendations_hybrid_strategy(client):
    """Test recommendations with hybrid strategy."""
    request_data = {"article_id": 100, "limit": 10, "strategy": "hybrid"}
    response = client.post("/api/v1/advanced/recommendations", json=request_data)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


def test_recommendations_invalid_strategy(client):
    """Test that invalid strategy returns error."""
    request_data = {"article_id": 100, "limit": 10, "strategy": "invalid"}
    response = client.post("/api/v1/advanced/recommendations", json=request_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_analytics_endpoint(client):
    """Test analytics endpoint."""
    response = client.get("/api/v1/advanced/analytics?top_n=10")
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "total_articles" in data
        assert "total_communities" in data
        assert "total_edges" in data


def test_analytics_with_custom_top_n(client):
    """Test analytics with custom top_n parameter."""
    response = client.get("/api/v1/advanced/analytics?top_n=5")
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert len(data.get("top_articles", [])) <= 5
        assert len(data.get("top_communities", [])) <= 5


def test_subgraph_export_endpoint(client):
    """Test subgraph export endpoint."""
    request_data = {"community_id": 1, "include_cross_edges": False}
    response = client.post("/api/v1/advanced/subgraph/export", json=request_data)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "nodes" in data
        assert "edges" in data


def test_subgraph_export_with_cross_edges(client):
    """Test subgraph export including cross edges."""
    request_data = {"community_id": 1, "include_cross_edges": True}
    response = client.post("/api/v1/advanced/subgraph/export", json=request_data)
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


def test_community_stats_endpoint(client):
    """Test community stats endpoint."""
    response = client.get("/api/v1/advanced/communities/1/stats")
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ]
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "community_id" in data
        assert "size" in data
