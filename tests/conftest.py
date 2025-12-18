"""Pytest configuration and fixtures for testing."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Neo4jService


@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def neo4j_service():
    """Create a Neo4j service instance for testing."""
    service = Neo4jService()
    yield service
    service.close()


@pytest.fixture
def sample_article_id():
    """Return a sample article ID for testing."""
    return "A000000"


@pytest.fixture
def sample_topic_id():
    """Return a sample topic ID for testing."""
    return 1


@pytest.fixture
def sample_author_id():
    """Return a sample author ID for testing."""
    return 1
