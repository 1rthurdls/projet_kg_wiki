"""Tests for main application endpoints."""

import pytest
from fastapi import status


def test_root_endpoint(client):
    """Test the root endpoint returns correct information."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data
    assert data["docs"] == "/docs"


def test_health_check_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert data["status"] in ["healthy", "degraded"]
    assert data["database"] in ["connected", "disconnected"]


def test_docs_endpoint(client):
    """Test that OpenAPI docs are accessible."""
    response = client.get("/docs")
    assert response.status_code == status.HTTP_200_OK


def test_openapi_endpoint(client):
    """Test that OpenAPI schema is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data
