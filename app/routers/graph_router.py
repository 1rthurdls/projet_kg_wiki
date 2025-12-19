from fastapi import APIRouter, HTTPException, Request, status

from app.database import Neo4jService
from app.models.schemas import EntityNode, EntitySearchRequest, GraphQueryRequest, GraphQueryResponse, Relationship

router = APIRouter()


@router.post("/query", response_model=GraphQueryResponse)
async def execute_query(request: Request, query_request: GraphQueryRequest):
    """
    Execute a custom Cypher query.

    Args:
        query_request: Query request containing Cypher query and parameters

    Returns:
        Query results and count
    """
    neo4j_service: Neo4jService = request.app.state.neo4j_service

    try:
        results = neo4j_service.execute_query(query_request.query, query_request.parameters)
        return GraphQueryResponse(data=results, count=len(results))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query execution failed: {str(e)}",
        ) from e


@router.post("/search", response_model=list[EntityNode])
async def search_entities(request: Request, search_request: EntitySearchRequest):
    """
    Search for entities in the knowledge graph.

    Args:
        search_request: Search request containing search term and limit

    Returns:
        List of matching entities
    """
    neo4j_service: Neo4jService = request.app.state.neo4j_service

    try:
        results = neo4j_service.search_entities(search_request.search_term, search_request.limit)
        return [
            EntityNode(
                id=str(result["id"]),
                labels=result["labels"],
                properties=result["properties"],
            )
            for result in results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        ) from e


@router.get("/entities/{entity_id}", response_model=EntityNode)
async def get_entity(request: Request, entity_id: str):
    """
    Get entity details by ID.

    Args:
        entity_id: Entity ID

    Returns:
        Entity data
    """
    neo4j_service: Neo4jService = request.app.state.neo4j_service

    try:
        result = neo4j_service.get_entity_by_id(entity_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity with ID {entity_id} not found",
            )

        return EntityNode(
            id=str(result["id"]),
            labels=result["labels"],
            properties=result["properties"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve entity: {str(e)}",
        ) from e


@router.get("/entities/{entity_id}/relationships", response_model=list[Relationship])
async def get_entity_relationships(request: Request, entity_id: str, direction: str = "both"):
    """
    Get relationships for an entity.

    Args:
        entity_id: Entity ID
        direction: Relationship direction ('incoming', 'outgoing', or 'both')

    Returns:
        List of relationships
    """
    if direction not in ["incoming", "outgoing", "both"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direction must be 'incoming', 'outgoing', or 'both'",
        )

    neo4j_service: Neo4jService = request.app.state.neo4j_service

    try:
        results = neo4j_service.get_entity_relationships(entity_id, direction)
        return [
            Relationship(
                id=str(result["id"]),
                type=result["type"],
                start_node_id=str(result["start_node_id"]),
                end_node_id=str(result["end_node_id"]),
                properties=result["properties"],
            )
            for result in results
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve relationships: {str(e)}",
        ) from e
