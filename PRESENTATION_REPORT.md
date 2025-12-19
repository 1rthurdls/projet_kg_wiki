# Knowledge Graph Wiki System - Presentation Report

## Executive Summary

This project implements a **Wikipedia Knowledge Graph System** using Neo4j graph database and FastAPI. It retrieves real Wikipedia data about organizations, stores it in a graph structure, and provides intelligent recommendations and analytics through a REST API.

**Key Achievement**: Built a full-stack graph database application with 3-tier architecture, real Wikipedia data integration, and advanced graph algorithms for article recommendations.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Data Collection & Processing](#3-data-collection--processing)
4. [Database Design](#4-database-design)
5. [API Implementation](#5-api-implementation)
6. [Docker Infrastructure](#6-docker-infrastructure)
7. [Testing & Quality Assurance](#7-testing--quality-assurance)
8. [Key Features Demonstrated](#8-key-features-demonstrated)
9. [Development Timeline](#9-development-timeline)

---

## 1. Project Overview

### What Was Built

A complete knowledge graph system that:
- Extracts Wikipedia data about organizations from Wikidata
- Stores article relationships in a Neo4j graph database
- Provides a REST API for querying and recommendations
- Runs in Docker containers for easy deployment
- Includes comprehensive testing and CI/CD

### Technologies Used

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend/Access** | Nginx | Reverse proxy, rate limiting, security |
| **Backend** | FastAPI (Python 3.12) | REST API with auto-documentation |
| **Database** | Neo4j 5 | Graph database for storing relationships |
| **Data Validation** | Pydantic 2.0 | Request/response schemas |
| **Infrastructure** | Docker Compose | Container orchestration |
| **Testing** | Pytest | Unit and integration tests |
| **CI/CD** | GitHub Actions | Automated testing and linting |

---

## 2. System Architecture

### Three-Tier Architecture

```
┌─────────────┐
│   Nginx     │  Port 80 - Entry point with security
│  (Proxy)    │  - Rate limiting (10 req/s)
└──────┬──────┘  - Security headers
       │
┌──────▼──────┐
│   FastAPI   │  Port 8000 - Business logic
│  (Backend)  │  - Request validation
└──────┬──────┘  - Graph queries
       │
┌──────▼──────┐
│   Neo4j     │  Ports 7474/7687 - Data storage
│ (Database)  │  - Graph relationships
└─────────────┘  - Cypher queries
```

### Why This Architecture?

1. **Nginx Layer**: Protects the API from abuse (rate limiting) and adds security headers
2. **FastAPI Layer**: Validates all inputs/outputs, provides automatic API documentation
3. **Neo4j Layer**: Efficiently stores and queries graph relationships between articles

### Communication Flow

```
User Request → Nginx → FastAPI → Neo4j Service → Database
                                      ↓
User Response ← JSON ← Pydantic Model ← Query Results
```

---

## 3. Data Collection & Processing

### File: `data/query_wikiperdia/retrieve.py`

This Python script fetches real Wikipedia data from two sources:

#### 3.1 Wikidata SPARQL Queries

**What it does:**
- Queries Wikidata for all organizations (root concept: Q43229)
- Fetches article titles, descriptions, and hierarchies
- Retrieves semantic relationships between articles
- Collects topic categories and tags

**Key Functions:**

1. **`fetch_all_data()`** - Main data retrieval
   - Gets Wikipedia articles about organizations
   - Pagination to handle large datasets (up to 2000 articles)
   - Retry logic for failed requests

2. **`fetch_article_links()`** - Article relationships
   - Finds connections between articles using Wikidata properties:
     - "part of" (wdt:P361)
     - "has part" (wdt:P527)
     - "facet of" (wdt:P1269)
     - "subclass of" (wdt:P279)
   - Creates the graph edges for recommendations

3. **`fetch_categories()`** - Topic tagging
   - Gets "instance of" (wdt:P31) relationships
   - Creates tags for topic classification

#### 3.2 XTools API Integration

**What it does:**
- Fetches **real Wikipedia authors** for each article
- Gets top 10 editors per article with their edit counts
- Tracks total contributions across the knowledge base

**Function: `fetch_authors_from_xtools()`**
- Queries XTools API: `https://xtools.wmcloud.org/api/page/top_editors/`
- Rate limiting (1.5s between requests) to respect the service
- Creates author nodes and article-author relationships

#### 3.3 Output Files

The script generates 10 CSV files in `data/query_wikiperdia/import/`:

| File | Content | Example |
|------|---------|---------|
| `articles.csv` | Article metadata | A000000, "Organization", url |
| `topics.csv` | Concept definitions | Q43229, "organization", desc |
| `article_links.csv` | Article→Article edges | A000000 → A000123 |
| `authors.csv` | Wikipedia contributors | AUTH00001, "JohnDoe", 1542 |
| `article_authors.csv` | Who wrote what | A000000 authored by AUTH00001 |
| `tags.csv` | Category labels | Q8563, "company" |
| `topic_hierarchy.csv` | Parent-child topics | Q43229 → Q783794 |
| `related_topics.csv` | Topic associations | Q43229 related to Q8148 |
| `article_topics.csv` | Article categorization | A000000 has topic Q43229 |
| `topic_tags.csv` | Topic labeling | Q43229 tagged with Q8563 |

**Real-world example:**
```
Article: "High reliability organization"
  → Author: WikiEditor123 (42 edits)
  → Topic: Q43229 (organization)
  → Links to: "Risk management", "Safety culture"
  → Tags: "management theory", "organizational studies"
```

---

## 4. Database Design

### Graph Schema

The Neo4j database has **5 node types** and **6 relationship types**:

#### Nodes (Entities)

```cypher
(:Article {
  article_id: "A000000",          // Unique ID
  article_title: "Organization",  // Display name
  article_url: "https://..."      // Wikipedia URL
})

(:Topic {
  topic_id: "Q43229",             // Wikidata QID
  topic_name: "organization",     // Human-readable
  topic_description: "..."        // Definition
})

(:Author {
  author_id: "AUTH00001",         // Generated ID
  author_name: "JohnDoe",         // Wikipedia username
  total_edits: 1542               // Contribution count
})

(:Tag {
  tag_name: "company"             // Category label
})

(:Community {
  community_id: 1,                // Cluster ID
  size: 150,                      // Number of articles
  density: 0.42,                  // Connection ratio
  avg_degree: 8.5                 // Avg connections per node
})
```

#### Relationships (Edges)

```cypher
(:Article)-[:REFERS_TO]->(:Article)        // Article citations
(:Article)-[:HAS_TOPIC]->(:Topic)          // Article categorization
(:Author)-[:AUTHORED]->(:Article)          // Authorship
(:Topic)-[:TAGGED_WITH]->(:Tag)            // Topic labeling
(:Article)-[:BELONGS_TO]->(:Community)     // Cluster membership
(:Topic)-[:PARENT_OF]->(:Topic)            // Hierarchy
```

### Database Loading Script

**File: `data/query_wikiperdia/db_modelisation/01_load_db.cypher`**

This Cypher script:

1. **Creates Constraints** (data integrity)
   ```cypher
   CREATE CONSTRAINT article_id IF NOT EXISTS
   FOR (a:Article) REQUIRE a.article_id IS UNIQUE;
   ```

2. **Creates Indexes** (query performance)
   ```cypher
   CREATE INDEX article_title IF NOT EXISTS
   FOR (a:Article) ON (a.article_title);
   ```

3. **Loads Nodes** from CSV files
   ```cypher
   LOAD CSV WITH HEADERS FROM 'file:///articles.csv' AS row
   MERGE (a:Article {article_id: row.article_id})
   SET a.article_url = row.article_url,
       a.article_title = row.article_title;
   ```

4. **Creates Relationships**
   ```cypher
   LOAD CSV WITH HEADERS FROM 'file:///article_links.csv' AS row
   MATCH (a:Article {article_id: row.source_article_id})
   MATCH (b:Article {article_id: row.target_article_id})
   MERGE (a)-[:REFERS_TO]->(b);
   ```

**Execution:** Run via `make load-db` or `./load_database.sh`

---

## 5. API Implementation

### 5.1 Application Entry Point

**File: `app/main.py`**

**Key Components:**

1. **Lifespan Management**
   ```python
   @asynccontextmanager
   async def lifespan(fastapi_app: FastAPI):
       # Startup: Create Neo4j connection once
       neo4j_service = Neo4jService()
       fastapi_app.state.neo4j_service = neo4j_service

       yield  # App runs here

       # Shutdown: Close connection properly
       neo4j_service.close()
   ```
   - Creates a **single database connection** at startup
   - Shares it across all requests (efficient)
   - Ensures proper cleanup on shutdown

2. **CORS Middleware**
   - Allows web browsers to call the API
   - Configurable origins for security

3. **Exception Handlers**
   - Catches database errors (Neo4jError)
   - Validates user input (ValueError)
   - Returns clean JSON error messages

4. **Health Check Endpoint**
   ```python
   @app.get("/health")
   async def health_check(request: Request):
       neo4j_service = request.app.state.neo4j_service
       db_status = "connected" if neo4j_service.verify_connectivity() else "disconnected"
       return {"status": "healthy", "database": db_status}
   ```

### 5.2 Basic Graph Operations

**File: `app/routers/graph_router.py`**

Provides core graph functionality:

#### Endpoint 1: Custom Cypher Queries
```python
POST /api/v1/query
{
  "query": "MATCH (a:Article) RETURN a LIMIT 10",
  "parameters": {}
}
```
- Execute any Cypher query
- Used for exploration and testing

#### Endpoint 2: Entity Search
```python
POST /api/v1/search
{
  "search_term": "organization",
  "limit": 10
}
```
- Search articles by title
- Full-text search across properties

#### Endpoint 3: Get Entity by ID
```python
GET /api/v1/entities/A000000
```
- Retrieve complete entity details

#### Endpoint 4: Get Relationships
```python
GET /api/v1/entities/A000000/relationships?direction=both
```
- Find all connections for an article
- Filter by direction: incoming, outgoing, or both

### 5.3 Advanced Graph Algorithms

**File: `app/routers/advanced_router.py`**

Implements sophisticated graph operations:

#### Feature 1: Shortest Path Finding
```python
POST /api/v1/advanced/pathfinding
{
  "source_id": 100,
  "target_id": 500,
  "max_depth": 5
}
```

**What it does:**
- Finds the minimum number of article references to connect two articles
- Uses Neo4j's `shortestPath()` algorithm
- Example: "Organization" → "Management" → "Leadership"

**Use case:** Discover how concepts are related through intermediate articles

#### Feature 2: Article Recommendations
```python
POST /api/v1/advanced/recommendations
{
  "article_id": 100,
  "limit": 10,
  "strategy": "community"
}
```

**Three strategies:**

1. **Community-based** (clustering)
   - Recommends articles from the same community cluster
   - "People who read articles in this group also read..."

2. **References-based** (collaborative filtering)
   - Finds articles connected through common citations
   - Uses graph patterns like: `(a)-[:REFERS_TO]->(shared)<-[:REFERS_TO]-(recommended)`

3. **Hybrid**
   - Combines both strategies
   - Weighted scoring for best results

**Use case:** "Related articles" feature for a knowledge base

#### Feature 3: Graph Analytics
```python
GET /api/v1/advanced/analytics?top_n=10
```

**Returns:**
- Total articles, communities, edges
- Average connectivity (degree)
- Top communities by size
- Most connected articles (hubs)

**Use case:** Dashboard statistics for knowledge base health

#### Feature 4: Community Subgraph Export
```python
POST /api/v1/advanced/subgraph/export
{
  "community_id": 5,
  "include_cross_edges": false
}
```

**What it does:**
- Exports all articles in a community cluster
- Optionally includes edges to other communities
- Returns nodes and edges in JSON format

**Use case:** Visualize article clusters in graph visualization tools

### 5.4 Data Models

**File: `app/models/schemas.py`**

Pydantic models define the API contract:

```python
class EntitySearchRequest(BaseModel):
    search_term: str
    limit: int = 10

class PathRequest(BaseModel):
    source_id: int
    target_id: int
    max_depth: int = 5

class RecommendationRequest(BaseModel):
    article_id: int
    limit: int = 10
    strategy: str = "community"  # or "references" or "hybrid"
```

**Benefits:**
- Automatic input validation
- Auto-generated API documentation (Swagger)
- Type safety in Python code

### 5.5 Database Service Layer

**File: `app/database/neo4j.py`**

Centralizes all database operations:

```python
class Neo4jService:
    def verify_connectivity() -> bool
        # Check if database is reachable

    def execute_query(query: str, parameters: dict) -> list
        # Run any Cypher query safely

    def search_entities(term: str, limit: int) -> list
        # Find entities by text search

    def find_shortest_path(source, target, max_depth) -> dict
        # Pathfinding algorithm

    def get_recommendations(article_id, limit, strategy) -> list
        # ML-based recommendations

    def get_analytics(top_n) -> dict
        # Graph statistics
```

**Design pattern:** Separation of concerns
- Routers handle HTTP requests
- Service handles database logic
- Clean, testable architecture

---

## 6. Docker Infrastructure

### 6.1 Docker Compose Configuration

**File: `docker-compose.yml`**

Orchestrates 3 services:

#### Service 1: Neo4j Database
```yaml
neo4j:
  image: neo4j:5
  ports:
    - "7474:7474"  # Browser UI
    - "7687:7687"  # Bolt protocol
  environment:
    - NEO4J_AUTH=neo4j/password
    - NEO4J_PLUGINS=["graph-data-science"]
  volumes:
    - neo4j_data:/data  # Persistent storage
    - ./data/query_wikiperdia/import:/var/lib/neo4j/import  # CSV files
  healthcheck:
    test: ["CMD-SHELL", "wget --spider localhost:7474"]
    interval: 10s
```

**Key features:**
- Persistent data storage (survives container restarts)
- CSV import folder mounted from host
- Health checks ensure database is ready before API starts

#### Service 2: FastAPI Application
```yaml
api:
  build:
    context: .
    dockerfile: Dockerfile
  ports:
    - "8000:8000"
  environment:
    - NEO4J_URI=bolt://neo4j:7687  # Uses Docker network
  depends_on:
    neo4j:
      condition: service_healthy  # Waits for Neo4j
```

**Key features:**
- Built from custom Dockerfile
- Waits for Neo4j health check before starting
- Environment-based configuration

#### Service 3: Nginx Reverse Proxy
```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
  depends_on:
    - api
```

### 6.2 FastAPI Dockerfile

**File: `Dockerfile`**

Multi-stage build for efficiency:

```dockerfile
FROM python:3.12-slim

# Security: Non-root user
RUN useradd -m -u 1000 appuser

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ /app/app/

# Switch to non-root user
USER appuser

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Security best practices:**
- Runs as non-root user
- Minimal base image (slim)
- No unnecessary packages

### 6.3 Nginx Configuration

**File: `nginx.conf`**

Provides security and performance:

```nginx
http {
    # Rate limiting: 10 requests/second per IP
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    server {
        listen 80;

        location / {
            limit_req zone=api_limit burst=20 nodelay;

            # Proxy to FastAPI
            proxy_pass http://api:8000;

            # Security headers
            add_header X-Frame-Options SAMEORIGIN;
            add_header X-Content-Type-Options nosniff;
        }
    }
}
```

**Protection features:**
- Rate limiting (prevents abuse)
- Security headers (prevents XSS, clickjacking)
- Single entry point (API not directly accessible)

### 6.4 Docker Networking

All services are in a **custom bridge network** (`kg-wiki-network`):

```
Internet → Nginx:80 → API:8000 → Neo4j:7687
           (public)   (internal)  (internal)
```

**Benefits:**
- Services communicate via names (not localhost)
- Only Nginx port exposed to internet
- Database isolated from external access

---

## 7. Testing & Quality Assurance

### 7.1 Test Structure

**File: `tests/conftest.py`**

Pytest fixtures provide test infrastructure:

```python
@pytest.fixture(scope="module")
def client():
    """Test client for API calls"""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(scope="module")
def neo4j_service():
    """Database connection for tests"""
    service = Neo4jService()
    yield service
    service.close()
```

### 7.2 Test Coverage

**Test files:**

1. **`tests/test_main.py`** - Application tests
   - Health check endpoint
   - Root endpoint
   - Error handling

2. **`tests/test_database.py`** - Database tests
   - Connection verification
   - Query execution
   - Error handling

3. **`tests/test_graph_router.py`** - Basic operations
   - Custom query endpoint
   - Entity search
   - Relationship retrieval

4. **`tests/test_advanced_router.py`** - Advanced features
   - Pathfinding algorithm
   - Recommendation strategies
   - Analytics generation

**Configuration: `pytest.ini`**
```ini
[pytest]
testpaths = tests
addopts = -v --cov=app --cov-report=html --cov-fail-under=60
```
- Minimum 60% code coverage required
- HTML reports for detailed analysis

### 7.3 CI/CD Pipeline

**GitHub Actions workflows in `.github/workflows/`:**

#### Workflow 1: Lint (`lint.yml`)
```yaml
- Runs Pylint for code quality
- Checks Black formatting
- Ensures isort import order
```

#### Workflow 2: Test (`test.yml`)
```yaml
- Spins up Neo4j database
- Installs dependencies
- Runs full test suite
- Reports coverage to Codecov
- Fails if coverage < 60%
```

#### Workflow 3: Docker Build (`docker.yml`)
```yaml
- Builds FastAPI Docker image
- Verifies successful build
- Optional: Push to registry
```

**Badges in README.md** show build status:
- [![Lint](badge)] - Code quality passing
- [![Test](badge)] - Tests passing
- [![Docker](badge)] - Build successful

### 7.4 Code Quality Tools

**File: `.pylintrc`**
- Configures code quality standards
- Enforces PEP 8 style guide
- Checks for common errors

**File: `pyproject.toml`**
- Project metadata
- Black formatter configuration
- Build system specification

---

## 8. Key Features Demonstrated

### 8.1 Graph Database Expertise

**Cypher Query Examples:**

1. **Pattern Matching** - Find articles with common topics
```cypher
MATCH (source:Article)-[:HAS_TOPIC]->(t:Topic)<-[:HAS_TOPIC]-(related:Article)
WHERE source <> related
RETURN related, count(t) as common_topics
ORDER BY common_topics DESC
```

2. **Path Finding** - Shortest connection between articles
```cypher
MATCH path = shortestPath(
  (source:Article)-[:REFERS_TO*..5]-(target:Article)
)
RETURN path
```

3. **Aggregation** - Graph analytics
```cypher
MATCH (a:Article)-[r:REFERS_TO]-()
RETURN avg(count(r)) as avg_degree
```

### 8.2 API Design Best Practices

1. **OpenAPI Documentation** - Auto-generated at `/docs`
2. **Pydantic Validation** - Type-safe request/response
3. **Error Handling** - Structured error responses
4. **Health Checks** - Kubernetes-ready monitoring
5. **CORS Configuration** - Web-friendly API

### 8.3 Production-Ready Features

1. **Docker Deployment** - Containerized for consistency
2. **Environment Configuration** - `.env` for secrets
3. **Logging** - Structured logs for debugging
4. **Rate Limiting** - Protection against abuse
5. **Health Checks** - Automatic failover support
6. **Non-root Containers** - Security best practices

### 8.4 Data Engineering

1. **ETL Pipeline** - Extract (Wikidata) → Transform (Python) → Load (Cypher)
2. **API Integration** - Wikidata SPARQL + XTools REST
3. **Data Validation** - Clean CSV generation
4. **Relationship Mapping** - URL to ID mapping
5. **Deduplication** - `drop_duplicates()` on relationships

---

## 9. Development Timeline

### Phase 1: Initial Setup (Commits: 53d43a3 - 5a02f2c)
- Created Git repository
- Added initial dataset (WikiGraphs)
- Set up project structure

### Phase 2: Data Exploration (Commits: a5b8174 - bb1d4e9)
- Jupyter notebook EDA (`eda.ipynb`)
- Database schema design (`db_modelisation/`)
- Initial Cypher queries

### Phase 3: Docker Infrastructure (Commits: c6fc1ea - 3177df9)
- Neo4j Docker setup
- Docker Compose with 3 services
- Volume mounts for CSV import

### Phase 4: Data Pipeline (Commits: 2e4d832 - b174062)
- Cypher load script (`01_load_db.cypher`)
- Python data retrieval (`retrieve.py`)
- Article-to-article relationship mapping

### Phase 5: Enhanced Data Collection (Commits: aef845e - 76662b7)
- XTools integration for real authors
- Wikidata semantic link extraction
- Updated ER schema

### Phase 6: Application Development (Commits: 8fedf4d - c2ad1aa)
- `.gitignore` for Python projects
- FastAPI application structure
- Basic and advanced routers
- Pydantic schemas
- Neo4j service layer

### Phase 7: DevOps & Testing (Commits: e18aa39 - fa97f74)
- Automation scripts (`Makefile`)
- Pytest test suite (67% coverage)
- GitHub Actions workflows
- Comprehensive documentation

### Phase 8: Production Readiness (Commits: 4e89c87 - 31b3910)
- README with full instructions
- Architecture documentation
- Updated dependencies
- Docker workflow fixes

---

## Key Takeaways for Presentation

### Technical Achievements

1. **Full-Stack Development**
   - Backend API (FastAPI)
   - Database (Neo4j)
   - Infrastructure (Docker)
   - CI/CD (GitHub Actions)

2. **Real-World Data Integration**
   - Wikidata SPARQL queries
   - XTools API for authors
   - Robust error handling and retries

3. **Graph Algorithms**
   - Shortest path finding
   - Community detection
   - Collaborative filtering recommendations

4. **Production-Ready Code**
   - 60%+ test coverage
   - Automated linting
   - Health checks
   - Rate limiting
   - Security headers

### Business Value

1. **Knowledge Discovery**
   - Find related articles automatically
   - Discover connections between concepts
   - Identify expert contributors

2. **Content Recommendations**
   - Multiple recommendation strategies
   - Community-based clustering
   - Reference-based similarity

3. **Analytics Dashboard**
   - Graph statistics
   - Community metrics
   - Article connectivity

### Scalability Considerations

1. **Horizontal Scaling**
   - Multiple API containers behind Nginx
   - Connection pooling in Neo4j

2. **Performance Optimization**
   - Database indexes on frequently queried fields
   - Constraints for data integrity
   - Parameterized queries for caching

3. **Future Enhancements**
   - Redis caching layer
   - GraphQL alternative API
   - Neo4j GDS algorithms (PageRank, Louvain)
   - LLM integration for natural language queries

---

## Demonstration Flow

### 1. Show the Infrastructure (2 minutes)
```bash
# Start all services
make docker-run

# Show running containers
docker ps

# Access points:
# - Nginx: http://localhost:80
# - API: http://localhost:8000/docs
# - Neo4j: http://localhost:7474
```

### 2. Show the Data (3 minutes)
```cypher
// Neo4j Browser (localhost:7474)

// Show database schema
CALL db.schema.visualization()

// Count entities
MATCH (n) RETURN labels(n)[0] as Type, count(*) as Count

// Show sample article with relationships
MATCH (a:Article)-[r]-(connected)
WHERE a.article_id = 'A000000'
RETURN a, r, connected
LIMIT 20
```

### 3. Demo API Endpoints (5 minutes)

Use Swagger UI at `http://localhost:80/docs`:

1. **Health Check** - Verify system is running
2. **Search** - Find articles about "organization"
3. **Recommendations** - Get related articles
4. **Analytics** - Show graph statistics
5. **Pathfinding** - Connect two articles

### 4. Show the Code (5 minutes)

Walk through key files:
- `retrieve.py` - Data collection logic
- `app/main.py` - Application entry point
- `app/routers/advanced_router.py` - Recommendation algorithm
- `docker-compose.yml` - Infrastructure as code
- `.github/workflows/test.yml` - CI/CD pipeline

### 5. Discuss Challenges & Solutions (3 minutes)

**Challenge 1:** Getting real Wikipedia authors
- **Solution:** XTools API integration with rate limiting

**Challenge 2:** Article-to-article relationships
- **Solution:** Wikidata semantic properties (P361, P527, etc.)

**Challenge 3:** Recommendation quality
- **Solution:** Multiple strategies (community, references, hybrid)

**Challenge 4:** Database performance
- **Solution:** Indexes, constraints, parameterized queries

---

## Conclusion

This project demonstrates:
- **Graph database expertise** with Neo4j and Cypher
- **Backend development** with FastAPI and Python
- **Data engineering** with ETL pipelines and API integration
- **DevOps practices** with Docker, CI/CD, and testing
- **Production-ready code** with security, monitoring, and documentation

The system is fully functional, well-tested, and ready for deployment.

---

**Generated on:** 2025-12-19
**Project:** Knowledge Graph Wiki System
**Technologies:** Neo4j, FastAPI, Docker, Python 3.12
