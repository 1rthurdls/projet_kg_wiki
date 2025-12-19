from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from neo4j.exceptions import Neo4jError

from app.database import Neo4jService
from app.models.config import settings
from app.models.schemas import ErrorResponse, HealthResponse
from app.routers import advanced_router, graph_router


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Manage application lifecycle (startup and shutdown)."""
    neo4j_service = Neo4jService()
    fastapi_app.state.neo4j_service = neo4j_service
    yield
    neo4j_service.close()


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Neo4jError)
async def neo4j_exception_handler(_request: Request, exc: Neo4jError):
    """Handle Neo4j database errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="DatabaseError",
            message="Database operation failed",
            detail=str(exc),
        ).model_dump(),
    )


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError):
    """Handle value errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error="ValidationError",
            message="Invalid input provided",
            detail=str(exc),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(_request: Request, exc: Exception):
    """Handle unexpected errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred",
            detail=str(exc) if settings.debug else None,
        ).model_dump(),
    )


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(request: Request):
    """Check API and database health."""
    neo4j_service: Neo4jService = request.app.state.neo4j_service
    db_status = "connected" if neo4j_service.verify_connectivity() else "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
    )


# Include routers
app.include_router(graph_router.router, prefix="/api/v1", tags=["Graph"])
app.include_router(advanced_router.router, prefix="/api/v1/advanced", tags=["Advanced"])


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "Knowledge Graph Wiki API",
        "version": settings.api_version,
        "docs": "/docs",
    }
