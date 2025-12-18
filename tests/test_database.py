"""Tests for Neo4j database service."""

import pytest
from app.database import Neo4jService


def test_neo4j_service_initialization():
    """Test Neo4j service can be initialized."""
    service = Neo4jService()
    assert service is not None
    service.close()


def test_neo4j_connectivity(neo4j_service):
    """Test Neo4j database connectivity."""
    is_connected = neo4j_service.verify_connectivity()
    assert isinstance(is_connected, bool)


def test_execute_simple_query(neo4j_service):
    """Test executing a simple Cypher query."""
    query = "RETURN 1 as number"
    results = neo4j_service.execute_query(query)
    assert len(results) == 1
    assert results[0]["number"] == 1


def test_execute_query_with_parameters(neo4j_service):
    """Test executing a query with parameters."""
    query = "RETURN $value as result"
    parameters = {"value": "test"}
    results = neo4j_service.execute_query(query, parameters)
    assert len(results) == 1
    assert results[0]["result"] == "test"


def test_count_articles(neo4j_service):
    """Test counting articles in the database."""
    query = "MATCH (a:Article) RETURN count(a) as count"
    results = neo4j_service.execute_query(query)
    assert len(results) == 1
    assert "count" in results[0]
    assert results[0]["count"] >= 0


def test_count_topics(neo4j_service):
    """Test counting topics in the database."""
    query = "MATCH (t:Topic) RETURN count(t) as count"
    results = neo4j_service.execute_query(query)
    assert len(results) == 1
    assert "count" in results[0]
    assert results[0]["count"] >= 0


def test_count_authors(neo4j_service):
    """Test counting authors in the database."""
    query = "MATCH (a:Author) RETURN count(a) as count"
    results = neo4j_service.execute_query(query)
    assert len(results) == 1
    assert "count" in results[0]
    assert results[0]["count"] >= 0
