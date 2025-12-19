# How the Knowledge Graph Wiki System Works Together

This document explains how all components of the Knowledge Graph Wiki System integrate and work together to create a complete application.

## Table of Contents
1. [System Flow](#system-flow)
2. [Request Lifecycle](#request-lifecycle)
3. [Component Integration](#component-integration)
4. [Data Flow](#data-flow)
5. [Deployment Process](#deployment-process)
6. [Testing Pipeline](#testing-pipeline)

---

## System Flow

### High-Level Overview

```
User Request
    ↓
Nginx (Port 80) - Rate limiting, security headers
    ↓
FastAPI (Port 8000) - API logic, validation
    ↓
Neo4j (Port 7687) - Graph database queries
    ↓
Response back through the stack
```

### Detailed Component Interaction

1. **Client makes HTTP request** → `http://localhost:80/api/v1/search`

2. **Nginx receives request**:
   - Checks rate limits (max 10 req/s per IP)
   - Adds security headers
   - Forwards to FastAPI at `api:8000`

3. **FastAPI processes request**:
   - Routes request to appropriate handler (`app/routers/graph_router.py`)
   - Validates input using Pydantic models (`app/models/schemas.py`)
   - Calls Neo4jService (`app/database/neo4j.py`)

4. **Neo4jService queries database**:
   - Constructs parameterized Cypher query
   - Executes against Neo4j
   - Transforms results to Python dicts

5. **Response flows back**:
   - Service → Router → FastAPI → Nginx → Client
   - Each layer adds its processing (validation, headers, etc.)

---

## Request Lifecycle

### Example: Search for Articles

#### 1. Client Request
```bash
curl -X POST http://localhost:80/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"search_term": "organization", "limit": 10}'
```

#### 2. Nginx Processing
File: `nginx.conf`
```nginx
# Rate limiting applied
limit_req zone=api_limit burst=20 nodelay;

# Proxy to FastAPI
proxy_pass http://api:8000;
```

#### 3. FastAPI Routing
File: `app/main.py`
```python
# Request hits this import
from app.routers import graph_router
app.include_router(graph_router.router, prefix="/api/v1")
```

File: `app/routers/graph_router.py`
```python
@router.post("/search", response_model=list[EntityNode])
async def search_entities(request: Request, search_request: EntitySearchRequest):
    # Pydantic validates search_request automatically
    neo4j_service = request.app.state.neo4j_service
    results = neo4j_service.search_entities(
        search_request.search_term,
        search_request.limit
    )
    # Transform to Pydantic models
    return [EntityNode(**result) for result in results]
```

#### 4. Service Layer
File: `app/database/neo4j.py`
```python
def search_entities(self, term: str, limit: int) -> list:
    query = """
        MATCH (n)
        WHERE any(prop in keys(n) WHERE toString(n[prop]) CONTAINS $term)
        RETURN id(n) as id, labels(n) as labels, properties(n) as properties
        LIMIT $limit
    """
    return self.execute_query(query, {"term": term, "limit": limit})
```

#### 5. Neo4j Execution
- Query executed with parameters (prevents injection)
- Results returned as records
- Converted to Python dictionaries

#### 6. Response
```json
[
  {
    "id": "12345",
    "labels": ["Article"],
    "properties": {
      "article_id": "A000000",
      "article_title": "High reliability organization",
      "article_url": "https://en.wikipedia.org/wiki/..."
    }
  }
]
```

---

## Component Integration

### 1. Docker Compose Orchestration

File: `docker-compose.yml`

```yaml
services:
  neo4j:
    # Starts first with health checks
    healthcheck:
      test: ["CMD-SHELL", "wget --spider localhost:7474"]

  api:
    # Waits for Neo4j to be healthy
    depends_on:
      neo4j:
        condition: service_healthy

  nginx:
    # Waits for API to start
    depends_on:
      - api
```

**Startup sequence**:
1. Neo4j starts and initializes
2. Health check passes (HTTP 200 on port 7474)
3. FastAPI builds and starts
4. Nginx starts and begins proxying

### 2. Environment Configuration

File: `.env`
```bash
NEO4J_URI=bolt://neo4j:7687  # Uses Docker service name
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

File: `app/models/config.py`
```python
class Settings(BaseSettings):
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

    class Config:
        env_file = ".env"  # Automatically loads from .env

settings = Settings()  # Available throughout app
```

File: `app/database/neo4j.py`
```python
from app.models.config import settings

class Neo4jService:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,  # From .env
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
```

### 3. Application Lifecycle

File: `app/main.py`
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create Neo4j connection
    neo4j_service = Neo4jService()
    app.state.neo4j_service = neo4j_service

    yield  # App runs here

    # Shutdown: Close connection
    neo4j_service.close()

app = FastAPI(lifespan=lifespan)
```

This ensures:
- Neo4j connection created once at startup
- Shared across all requests via `request.app.state`
- Properly closed on shutdown

---

## Data Flow

### 1. Initial Data Load

```
CSV Files → Cypher Script → Neo4j Database
```

File: `data/query_wikiperdia/db_modelisation/01_load_db.cypher`
```cypher
// 1. Create constraints
CREATE CONSTRAINT article_id_unique IF NOT EXISTS
FOR (a:Article) REQUIRE a.article_id IS UNIQUE;

// 2. Load CSV data
LOAD CSV WITH HEADERS FROM 'file:///articles.csv' AS row
CREATE (a:Article {
  article_id: row.article_id,
  article_title: row.article_title,
  article_url: row.article_url
});

// 3. Create relationships
LOAD CSV WITH HEADERS FROM 'file:///article_links.csv' AS row
MATCH (a:Article {article_id: row.source_id})
MATCH (b:Article {article_id: row.target_id})
CREATE (a)-[:REFERS_TO]->(b);
```

Script: `load_database.sh`
```bash
# Waits for Neo4j to be ready
until docker exec neo4j cypher-shell -u neo4j -p password "RETURN 1;" > /dev/null 2>&1; do
  sleep 2
done

# Executes the Cypher script
docker exec -i neo4j cypher-shell -u neo4j -p password < data/.../01_load_db.cypher
```

### 2. Query Execution Flow

```
User → API Endpoint → Service Method → Cypher Query → Neo4j
                                                           ↓
User ← JSON Response ← Pydantic Model ← Python Dict ← Query Result
```

Example transformation:

**Neo4j Result**:
```
Record(article=Node(id=123, labels={'Article'}, properties={...}))
```

**Service Layer** (`neo4j.py`):
```python
{
  "id": "123",
  "labels": ["Article"],
  "properties": {"article_id": "A000000", ...}
}
```

**Router Layer** (`graph_router.py`):
```python
EntityNode(
  id="123",
  labels=["Article"],
  properties={"article_id": "A000000", ...}
)
```

**API Response**:
```json
{
  "id": "123",
  "labels": ["Article"],
  "properties": {"article_id": "A000000", ...}
}
```

---

## Deployment Process

### Local Development

```bash
# 1. Setup environment
make install          # Creates venv, installs dependencies

# 2. Start infrastructure
make docker-up        # Starts Neo4j container

# 3. Initialize data
make load-db          # Loads graph from CSV files

# 4. Run application
make run              # Starts FastAPI with hot-reload

# 5. Test
make test             # Runs pytest suite
make lint             # Checks code quality
```

### Full Docker Deployment

```bash
# 1. Build all images
make docker-build     # Builds FastAPI image

# 2. Start all services
make docker-up        # Neo4j + API + Nginx

# 3. Load data
make load-db          # Populates database

# 4. Verify
curl http://localhost:80/health

# 5. Monitor
make docker-logs      # View all container logs
```

### File Locations in Containers

**Neo4j Container**:
- Data: `/var/lib/neo4j/data` (volume: `neo4j_data`)
- Logs: `/var/lib/neo4j/logs` (volume: `neo4j_logs`)
- Import: `/var/lib/neo4j/import` (mounted from `./data/query_wikiperdia/import`)

**API Container**:
- Code: `/app` (copied from build context)
- Runs as user: `appuser` (non-root for security)

**Nginx Container**:
- Config: `/etc/nginx/nginx.conf` (mounted from `./nginx.conf`)

---

## Testing Pipeline

### 1. Local Testing

File: `pytest.ini`
```ini
[pytest]
testpaths = tests
addopts = -v --cov=app --cov-report=html --cov-fail-under=60
```

Run:
```bash
make test
```

### 2. Test Structure

File: `tests/conftest.py`
```python
@pytest.fixture(scope="module")
def client():
    # Creates test client that wraps FastAPI app
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(scope="module")
def neo4j_service():
    # Provides Neo4j connection for tests
    service = Neo4jService()
    yield service
    service.close()
```

File: `tests/test_main.py`
```python
def test_health_check_endpoint(client):
    # Uses fixture above
    response = client.get("/health")
    assert response.status_code == 200
```

### 3. CI/CD Pipeline

File: `.github/workflows/test.yml`

```yaml
jobs:
  test:
    services:
      neo4j:
        # Spins up Neo4j in GitHub Actions
        image: neo4j:5

    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
      - name: Run tests with coverage
      - name: Upload coverage to Codecov
```

**Flow**:
1. Push to GitHub triggers workflow
2. GitHub Actions starts Neo4j service
3. Checks out code
4. Installs dependencies
5. Runs full test suite
6. Reports coverage
7. Fails if coverage < 60%

---

## Key Integration Points

### 1. Pydantic Models Bridge Code and API

File: `app/models/schemas.py`
```python
class EntitySearchRequest(BaseModel):
    search_term: str
    limit: int = 10

class EntityNode(BaseModel):
    id: str
    labels: list[str]
    properties: dict
```

Used in:
- **Router**: Type hints ensure validation
- **OpenAPI**: Auto-generates docs
- **Response**: Serializes to JSON

### 2. Dependency Injection via FastAPI State

```python
# Startup (main.py)
app.state.neo4j_service = Neo4jService()

# Usage (router)
def endpoint(request: Request):
    service = request.app.state.neo4j_service
    # Use service...
```

Benefits:
- Single database connection pool
- Easy to mock in tests
- Clean separation of concerns

### 3. Docker Networks Enable Service Discovery

```yaml
networks:
  kg-wiki-network:
    driver: bridge
```

Services communicate via names:
- API connects to `bolt://neo4j:7687` (not `localhost`)
- Nginx proxies to `http://api:8000`

---

## Troubleshooting Integration

### Problem: API can't connect to Neo4j

**Check**:
```bash
# 1. Verify Neo4j is running
docker ps | grep neo4j

# 2. Check network
docker network inspect projet_kg_wiki_kg-wiki-network

# 3. Test from API container
docker exec -it kg-wiki-api ping neo4j

# 4. Verify URI
echo $NEO4J_URI  # Should be bolt://neo4j:7687, not localhost
```

### Problem: Tests fail but app works

**Cause**: Tests use `localhost`, app uses `neo4j`

**Fix**: Environment variables
```python
# tests/conftest.py
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
```

---

## Summary

The system integrates through:

1. **Docker Compose**: Orchestrates startup order and networking
2. **Environment Variables**: Configure connections and settings
3. **FastAPI State**: Share Neo4j connection across requests
4. **Pydantic Models**: Validate data and generate documentation
5. **Nginx**: Provide security and load balancing
6. **Pytest Fixtures**: Enable isolated testing
7. **GitHub Actions**: Automate quality checks

Each component has a specific responsibility, and they communicate through well-defined interfaces (HTTP, Bolt protocol, Docker networks).
