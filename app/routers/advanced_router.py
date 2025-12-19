from fastapi import APIRouter, HTTPException, Query, Request, status

from app.database import Neo4jService
from app.models.schemas import (
    AnalyticsResponse,
    ArticleStats,
    CommunityStats,
    PathNode,
    PathRequest,
    PathResponse,
    RecommendationRequest,
    RecommendationResponse,
    RecommendedArticle,
    SubgraphRequest,
    SubgraphResponse,
)

router = APIRouter()


@router.post("/pathfinding", response_model=PathResponse)
async def find_shortest_path(request: Request, path_request: PathRequest):
    """
    Find the shortest path between two articles using graph traversal.

    This endpoint uses the shortestPath algorithm to find the minimum number
    of article references needed to connect two articles.

    Args:
        path_request: Source and target article IDs with max depth

    Returns:
        Path information including sequence of articles and path length

    Example:
        ```json
        {
            "source_id": 100,
            "target_id": 500,
            "max_depth": 5
        }
        ```
    """
    neo4j_service: Neo4jService = request.app.state.neo4j_service

    try:
        result = neo4j_service.find_shortest_path(
            path_request.source_id, path_request.target_id, path_request.max_depth
        )

        path_nodes = [PathNode(**node) for node in result["path"]]

        return PathResponse(path=path_nodes, length=result["length"], exists=result["exists"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pathfinding failed: {str(e)}",
        ) from e


@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: Request, rec_request: RecommendationRequest):
    """
    Get personalized article recommendations based on different strategies.

    Strategies:
    - **community**: Recommend articles from the same community
    - **references**: Recommend articles connected through common references (collaborative filtering)
    - **hybrid**: Combine both community and reference-based recommendations

    Args:
        rec_request: Article ID, limit, and recommendation strategy

    Returns:
        List of recommended articles with scores and reasons

    Example:
        ```json
        {
            "article_id": 100,
            "limit": 10,
            "strategy": "community"
        }
        ```
    """
    if rec_request.strategy not in ["community", "references", "hybrid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy must be 'community', 'references', or 'hybrid'",
        )

    neo4j_service: Neo4jService = request.app.state.neo4j_service

    try:
        results = neo4j_service.get_recommendations(rec_request.article_id, rec_request.limit, rec_request.strategy)

        recommendations = [RecommendedArticle(**rec) for rec in results]

        return RecommendationResponse(
            source_id=rec_request.article_id,
            recommendations=recommendations,
            count=len(recommendations),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recommendation generation failed: {str(e)}",
        ) from e


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(request: Request, top_n: int = Query(default=10, ge=1, le=50)):
    """
    Get comprehensive analytics about the knowledge graph.

    Provides:
    - Overall graph statistics (total articles, communities, edges)
    - Average degree (connectivity)
    - Top communities by size and metrics
    - Top articles by degree (most connected)

    Args:
        top_n: Number of top items to return (1-50)

    Returns:
        Analytics data including global stats and top entities

    Example response shows network structure, community distribution,
    and identifies hub articles.
    """
    neo4j_service: Neo4jService = request.app.state.neo4j_service

    try:
        analytics = neo4j_service.get_analytics(top_n)

        return AnalyticsResponse(
            total_articles=analytics["total_articles"],
            total_communities=analytics["total_communities"],
            total_edges=analytics["total_edges"],
            avg_degree=analytics["avg_degree"],
            top_communities=[CommunityStats(**comm) for comm in analytics["top_communities"]],
            top_articles=[ArticleStats(**article) for article in analytics["top_articles"]],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analytics generation failed: {str(e)}",
        ) from e


@router.post("/subgraph/export", response_model=SubgraphResponse)
async def export_subgraph(request: Request, subgraph_request: SubgraphRequest):
    """
    Export a subgraph for a specific community.

    Useful for:
    - Visualizing community structure
    - Analyzing intra-community connections
    - Exporting data for external analysis

    Args:
        subgraph_request: Community ID and edge inclusion options

    Returns:
        Nodes and edges for the community subgraph

    Example:
        ```json
        {
            "community_id": 5,
            "include_cross_edges": false
        }
        ```

    When `include_cross_edges` is true, edges pointing to other communities
    are included, allowing analysis of inter-community relationships.
    """
    neo4j_service: Neo4jService = request.app.state.neo4j_service

    try:
        result = neo4j_service.export_subgraph(subgraph_request.community_id, subgraph_request.include_cross_edges)

        return SubgraphResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Subgraph export failed: {str(e)}",
        ) from e


@router.get("/communities/{community_id}/stats", response_model=CommunityStats)
async def get_community_stats(request: Request, community_id: int):
    """
    Get detailed statistics for a specific community.

    Args:
        community_id: Community ID

    Returns:
        Community statistics including size, density, and traffic metrics
    """
    neo4j_service: Neo4jService = request.app.state.neo4j_service

    try:
        query = """
        MATCH (c:Community {community_id: $community_id})
        OPTIONAL MATCH (a:Article)-[:BELONGS_TO]->(c)
        WITH c, count(a) as article_count
        OPTIONAL MATCH (a1:Article)-[:BELONGS_TO]->(c)
        OPTIONAL MATCH (a1)-[r:REFERS_TO]-(a2:Article)-[:BELONGS_TO]->(c)
        WITH c, article_count, count(DISTINCT r)/2 as internal_edges
        RETURN c.community_id as community_id,
               c.size as size,
               c.density as density,
               c.avg_degree as avg_degree,
               c.avg_traffic as avg_traffic,
               c.median_traffic as median_traffic,
               c.level as level,
               article_count,
               internal_edges
        """
        results = neo4j_service.execute_query(query, {"community_id": community_id})

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Community with ID {community_id} not found",
            )

        return CommunityStats(**results[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve community stats: {str(e)}",
        ) from e
