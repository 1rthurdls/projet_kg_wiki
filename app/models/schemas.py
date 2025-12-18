from typing import Any

from pydantic import BaseModel, Field


class EntityNode(BaseModel):
    """Represents a node/entity in the knowledge graph."""

    id: str = Field(..., description="Unique identifier for the entity")
    labels: list[str] = Field(..., description="Node labels (types)")
    properties: dict[str, Any] = Field(default_factory=dict, description="Node properties")


class Relationship(BaseModel):
    """Represents a relationship between two entities."""

    id: str = Field(..., description="Unique identifier for the relationship")
    type: str = Field(..., description="Relationship type")
    start_node_id: str = Field(..., description="Starting node ID")
    end_node_id: str = Field(..., description="Ending node ID")
    properties: dict[str, Any] = Field(default_factory=dict, description="Relationship properties")


class GraphQueryRequest(BaseModel):
    """Request model for graph queries."""

    query: str = Field(..., description="Cypher query to execute", min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict, description="Query parameters")


class GraphQueryResponse(BaseModel):
    """Response model for graph queries."""

    data: list[dict[str, Any]] = Field(..., description="Query results")
    count: int = Field(..., description="Number of results returned")


class EntitySearchRequest(BaseModel):
    """Request model for entity search."""

    search_term: str = Field(..., description="Term to search for", min_length=1)
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: str | None = Field(None, description="Additional error details")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    database: str = Field(..., description="Database connection status")


# Advanced query models
class PathRequest(BaseModel):
    """Request model for pathfinding queries."""

    source_id: int = Field(..., description="Source article ID")
    target_id: int = Field(..., description="Target article ID")
    max_depth: int = Field(default=5, ge=1, le=10, description="Maximum path depth")


class PathNode(BaseModel):
    """Node in a path."""

    id: int = Field(..., description="Article ID")
    target: int | None = Field(None, description="Article target")
    community_id: int | None = Field(None, description="Community ID")


class PathResponse(BaseModel):
    """Response model for pathfinding queries."""

    path: list[PathNode] = Field(..., description="Sequence of articles in path")
    length: int = Field(..., description="Path length")
    exists: bool = Field(..., description="Whether a path exists")


class RecommendationRequest(BaseModel):
    """Request model for article recommendations."""

    article_id: int = Field(..., description="Source article ID")
    limit: int = Field(default=10, ge=1, le=50, description="Number of recommendations")
    strategy: str = Field(
        default="community",
        description="Recommendation strategy: 'community', 'references', or 'hybrid'",
    )


class RecommendedArticle(BaseModel):
    """Recommended article with score."""

    id: int = Field(..., description="Article ID")
    target: int | None = Field(None, description="Article target")
    community_id: int | None = Field(None, description="Community ID")
    score: float = Field(..., description="Recommendation score")
    reason: str = Field(..., description="Recommendation reason")


class RecommendationResponse(BaseModel):
    """Response model for recommendations."""

    source_id: int = Field(..., description="Source article ID")
    recommendations: list[RecommendedArticle] = Field(..., description="Recommended articles")
    count: int = Field(..., description="Number of recommendations")


class CommunityStats(BaseModel):
    """Statistics for a community."""

    community_id: int = Field(..., description="Community ID")
    size: int = Field(..., description="Number of articles")
    density: float = Field(..., description="Network density")
    avg_degree: float = Field(..., description="Average degree")
    avg_traffic: float = Field(..., description="Average traffic")
    median_traffic: float = Field(..., description="Median traffic")
    level: str | None = Field(None, description="Community level")
    article_count: int = Field(..., description="Actual article count in graph")
    internal_edges: int = Field(..., description="Edges within community")


class ArticleStats(BaseModel):
    """Statistics for an article."""

    article_id: int = Field(..., description="Article ID")
    degree: int = Field(..., description="Number of connections")
    community_id: int | None = Field(None, description="Community ID")
    target: int | None = Field(None, description="Article target")


class AnalyticsResponse(BaseModel):
    """Response model for analytics queries."""

    total_articles: int = Field(..., description="Total number of articles")
    total_communities: int = Field(..., description="Total number of communities")
    total_edges: int = Field(..., description="Total number of edges")
    avg_degree: float = Field(..., description="Average article degree")
    top_communities: list[CommunityStats] = Field(..., description="Top communities by size")
    top_articles: list[ArticleStats] = Field(..., description="Top articles by degree")


class SubgraphRequest(BaseModel):
    """Request model for subgraph export."""

    community_id: int = Field(..., description="Community ID to export")
    include_cross_edges: bool = Field(default=False, description="Include edges to other communities")


class SubgraphResponse(BaseModel):
    """Response model for subgraph export."""

    community_id: int = Field(..., description="Community ID")
    nodes: list[dict[str, Any]] = Field(..., description="Articles in community")
    edges: list[dict[str, Any]] = Field(..., description="Edges between articles")
    node_count: int = Field(..., description="Number of nodes")
    edge_count: int = Field(..., description="Number of edges")
