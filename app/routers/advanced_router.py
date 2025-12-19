from fastapi import APIRouter, HTTPException, Query, Request, status

from app.database import Neo4jService
from app.models.schemas import (
    AnalyticsResponse,
    ArticleStats,
    CommunityStats,
    LouvainCommunity,
    LouvainRequest,
    LouvainResponse,
    NodeSimilarityRequest,
    NodeSimilarityResponse,
    PageRankRequest,
    PageRankResponse,
    PageRankResult,
    PathNode,
    PathRequest,
    PathResponse,
    RecommendationRequest,
    RecommendationResponse,
    RecommendedArticle,
    SimilarArticle,
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


# Graph Data Science (GDS) Endpoints


@router.post("/gds/pagerank", response_model=PageRankResponse, tags=["Graph Data Science"])
async def calculate_pagerank(request: Request, pagerank_request: PageRankRequest):
    """
    Calculate PageRank scores for articles in the knowledge graph.

    **PageRank** is a link analysis algorithm that measures the importance of nodes
    based on the structure of incoming links. Articles cited by many other important
    articles will have higher PageRank scores.

    **Use Cases**:
    - Identify most influential/authoritative articles
    - Rank search results by importance
    - Discover central articles in the knowledge graph

    **Parameters**:
    - `max_iterations`: Maximum iterations for convergence (default: 20)
    - `damping_factor`: Probability of following a link vs. random jump (default: 0.85)
    - `limit`: Number of top results to return (default: 10)

    **Returns**:
    - Top-ranked articles with PageRank scores
    - Total nodes analyzed
    - Execution time in milliseconds

    **Example Request**:
    ```json
    {
        "max_iterations": 20,
        "damping_factor": 0.85,
        "limit": 10
    }
    ```

    **Note**: Requires Neo4j GDS plugin. Falls back to degree centrality if GDS unavailable.
    """
    neo4j_service: Neo4jService = request.app.state.neo4j_service

    try:
        result = neo4j_service.run_pagerank(
            max_iterations=pagerank_request.max_iterations,
            damping_factor=pagerank_request.damping_factor,
            limit=pagerank_request.limit,
        )

        # Convert results to Pydantic models
        pagerank_results = [PageRankResult(**res) for res in result["results"]]

        return PageRankResponse(
            algorithm="PageRank",
            total_nodes=result["total_nodes"],
            results=pagerank_results,
            execution_time_ms=result["execution_time_ms"],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PageRank calculation failed: {str(e)}",
        ) from e


@router.post("/gds/louvain", response_model=LouvainResponse, tags=["Graph Data Science"])
async def detect_communities_louvain(request: Request, louvain_request: LouvainRequest):
    """
    Detect communities in the article network using the Louvain algorithm.

    **Louvain** is a modularity-based community detection algorithm that identifies
    densely connected groups of articles. It works by optimizing modularity scores
    through hierarchical agglomeration.

    **Use Cases**:
    - Discover topical clusters in the knowledge graph
    - Identify research areas or subject domains
    - Group related articles for recommendation systems
    - Analyze knowledge graph structure

    **Parameters**:
    - `max_levels`: Maximum hierarchy levels to explore (default: 10)
    - `include_intermediate_communities`: Return intermediate levels (default: false)

    **Returns**:
    - List of detected communities with sizes
    - Overall modularity score (higher = better community structure)
    - Total number of communities detected
    - Execution time in milliseconds

    **Modularity Score**:
    - Range: -0.5 to 1.0
    - > 0.3: Strong community structure
    - 0.1 - 0.3: Moderate community structure
    - < 0.1: Weak community structure

    **Example Request**:
    ```json
    {
        "max_levels": 10,
        "include_intermediate_communities": false
    }
    ```

    **Note**: Requires Neo4j GDS plugin. Falls back to existing Community nodes if unavailable.
    """
    neo4j_service: Neo4jService = request.app.state.neo4j_service

    try:
        result = neo4j_service.run_louvain(
            max_levels=louvain_request.max_levels,
            include_intermediate=louvain_request.include_intermediate_communities,
        )

        # Convert results to Pydantic models
        communities = [LouvainCommunity(**comm) for comm in result["communities"]]

        return LouvainResponse(
            algorithm="Louvain",
            total_communities=result["total_communities"],
            modularity=result["modularity"],
            communities=communities,
            execution_time_ms=result["execution_time_ms"],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Louvain community detection failed: {str(e)}",
        ) from e


@router.post("/gds/similarity", response_model=NodeSimilarityResponse, tags=["Graph Data Science"])
async def find_similar_articles(request: Request, similarity_request: NodeSimilarityRequest):
    """
    Find similar articles using the Node Similarity algorithm.

    **Node Similarity** computes pairwise similarity scores between articles based on
    their neighborhood overlap. Articles that cite similar references are considered similar.

    **Algorithm**: Uses Jaccard similarity on node neighborhoods:
    - Jaccard(A, B) = |neighbors(A) ∩ neighbors(B)| / |neighbors(A) ∪ neighbors(B)|

    **Use Cases**:
    - Content-based article recommendations
    - Finding related research papers
    - Duplicate detection
    - Link prediction

    **Parameters**:
    - `article_id`: Source article ID to find similar articles for
    - `limit`: Number of similar articles to return (default: 10)
    - `similarity_cutoff`: Minimum similarity threshold 0-1 (default: 0.1)

    **Returns**:
    - List of similar articles with similarity scores
    - Common neighbor counts
    - Execution time in milliseconds

    **Similarity Score Interpretation**:
    - 1.0: Identical neighborhood (same references)
    - 0.7-1.0: Very similar articles
    - 0.3-0.7: Moderately similar
    - < 0.3: Weakly similar

    **Example Request**:
    ```json
    {
        "article_id": "A000000",
        "limit": 10,
        "similarity_cutoff": 0.1
    }
    ```

    **Note**: Requires Neo4j GDS plugin. Falls back to Cypher-based Jaccard similarity if unavailable.
    """
    neo4j_service: Neo4jService = request.app.state.neo4j_service

    try:
        result = neo4j_service.run_node_similarity(
            article_id=similarity_request.article_id,
            limit=similarity_request.limit,
            similarity_cutoff=similarity_request.similarity_cutoff,
        )

        # Convert results to Pydantic models
        similar_articles = [SimilarArticle(**article) for article in result["similar_articles"]]

        return NodeSimilarityResponse(
            algorithm="Node Similarity",
            source_article_id=result["source_article_id"],
            source_article_title=result["source_article_title"],
            similar_articles=similar_articles,
            execution_time_ms=result["execution_time_ms"],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Node similarity calculation failed: {str(e)}",
        ) from e
