# Architecture Documentation - Knowledge Graph Wiki System

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Technology Stack](#technology-stack)
4. [Component Design](#component-design)
5. [Data Model](#data-model)
6. [API Design](#api-design)
7. [Database Schema](#database-schema)
8. [Deployment Architecture](#deployment-architecture)
9. [Security Considerations](#security-considerations)
10. [Performance Optimizations](#performance-optimizations)

---

## System Overview

The Knowledge Graph Wiki System is a full-stack application that provides a RESTful API for querying and exploring Wikipedia article relationships stored in a Neo4j graph database. The system implements Project #6 from the GraphDB course requirements.

### Key Features

- **Semantic Search**: Find articles through connected concepts
- **Related Articles**: Discover similar content through graph relationships
- **Topic Exploration**: Navigate topic hierarchies and relationships
- **Author Tracking**: Monitor contributions across the knowledge base
- **Community Detection**: Identify article clusters using graph algorithms
- **Advanced Analytics**: Comprehensive graph statistics and insights

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│  (Web Browser, API Clients, Jupyter Notebooks)              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Nginx Reverse Proxy                      │
│  • Rate Limiting (10 req/s)                                 │
│  • Load Balancing                                           │
│  • Security Headers                                         │
│  • SSL Termination (production)                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              API Layer (Routers)                     │   │
│  │  • /api/v1/query - Custom Cypher execution          │   │
│  │  • /api/v1/search - Entity search                   │   │
│  │  • /api/v1/advanced/pathfinding - Graph traversal   │   │
│  │  • /api/v1/advanced/recommendations - ML-based      │   │
│  │  • /api/v1/advanced/analytics - Graph statistics    │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Service Layer (Business Logic)            │   │
│  │  • Neo4jService - Database operations               │   │
│  │  • Query optimization and caching                   │   │
│  │  • Result transformation                            │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Models & Schemas                        │   │
│  │  • Pydantic models for validation                   │   │
│  │  • Configuration management                         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Neo4j Graph Database                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Graph Schema                        │   │
│  │  Nodes:                                             │   │
│  │    • Article (article_id, title, url, concept_id)   │   │
│  │    • Topic (topic_id, name, level)                  │   │
│  │    • Author (author_id, name, edit_count)           │   │
│  │    • Tag (tag_name)                                 │   │
│  │    • Community (community_id, size, density)        │   │
│  │                                                      │   │
│  │  Relationships:                                      │   │
│  │    • REFERS_TO (Article → Article)                  │   │
│  │    • HAS_TOPIC (Article → Topic)                    │   │
│  │    • AUTHORED (Author → Article)                    │   │
│  │    • TAGGED_WITH (Topic → Tag)                      │   │
│  │    • BELONGS_TO (Article → Community)               │   │
│  │    • PARENT_OF (Topic → Topic)                      │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Indexes & Constraints                   │   │
│  │  • Unique constraint on Article.article_id          │   │
│  │  • Unique constraint on Topic.topic_id              │   │
│  │  • Index on Article.article_title                   │   │
│  │  • Index on Topic.topic_name                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Backend
- **FastAPI 0.115+**: Modern async Python web framework
  - High performance (Starlette + Pydantic)
  - Automatic OpenAPI documentation
  - Type hints and validation
  - Async/await support

- **Neo4j 5.x**: Graph database
  - Native graph storage and processing
  - Cypher query language
  - ACID transactions
  - Graph Data Science (GDS) library

- **Pydantic 2.0+**: Data validation
  - Runtime type checking
  - JSON schema generation
  - Settings management

### Infrastructure
- **Docker & Docker Compose**: Containerization
  - Consistent development/production environments
  - Service orchestration
  - Volume management

- **Nginx**: Reverse proxy
  - Load balancing
  - Rate limiting
  - SSL termination
  - Security headers

### Testing & Quality
- **Pytest**: Testing framework
- **pytest-cov**: Code coverage
- **pytest-asyncio**: Async test support
- **Pylint**: Code quality analysis
- **Black**: Code formatting

### CI/CD
- **GitHub Actions**: Automated workflows
  - Lint pipeline
  - Test pipeline with coverage
  - Docker build and push

---

## Component Design

### 1. API Layer (FastAPI Routers)

#### Graph Router (`app/routers/graph_router.py`)
Handles basic graph operations:
- Custom Cypher query execution
- Entity search by term
- Entity retrieval by ID
- Relationship traversal

#### Advanced Router (`app/routers/advanced_router.py`)
Implements complex graph algorithms:
- **Pathfinding**: Shortest path between articles
- **Recommendations**: ML-based article suggestions
  - Community-based strategy
  - Reference-based collaborative filtering
  - Hybrid approach
- **Analytics**: Graph statistics and metrics
- **Subgraph Export**: Community extraction

### 2. Service Layer

#### Neo4jService (`app/database/neo4j.py`)
Centralized database interaction:
```python
class Neo4jService:
    def verify_connectivity() -> bool
    def execute_query(query: str, parameters: dict) -> list
    def search_entities(term: str, limit: int) -> list
    def find_shortest_path(source: int, target: int, max_depth: int) -> dict
    def get_recommendations(article_id: int, limit: int, strategy: str) -> list
    def get_analytics(top_n: int) -> dict
    def export_subgraph(community_id: int, include_cross: bool) -> dict
```

### 3. Data Models

#### Configuration (`app/models/config.py`)
Environment-based settings using Pydantic:
- Database credentials
- API metadata
- CORS configuration
- Debug mode

#### Schemas (`app/models/schemas.py`)
Request/response models:
- `GraphQueryRequest`, `GraphQueryResponse`
- `EntitySearchRequest`, `EntityNode`
- `PathRequest`, `PathResponse`
- `RecommendationRequest`, `RecommendationResponse`
- `AnalyticsResponse`, `SubgraphResponse`

---

## Data Model

### Graph Schema

```cypher
// Node Types
(:Article {
  article_id: String,        // Unique identifier (e.g., "A000000")
  article_url: String,       // Wikipedia URL
  article_title: String,     // Human-readable title
  concept_id: String         // Wikidata Q-identifier
})

(:Topic {
  topic_id: Integer,         // Unique identifier
  topic_name: String,        // Topic label
  level: Integer             // Hierarchy level
})

(:Author {
  author_id: Integer,        // Unique identifier
  author_name: String,       // Author username
  edit_count: Integer        // Total edits
})

(:Tag {
  tag_name: String           // Tag label
})

(:Community {
  community_id: Integer,     // Unique identifier
  size: Integer,             // Number of articles
  density: Float,            // Graph density
  avg_degree: Float,         // Average connections
  avg_traffic: Integer,      // Average page views
  median_traffic: Integer,   // Median page views
  level: Integer             // Hierarchy level
})

// Relationship Types
(:Article)-[:REFERS_TO]->(:Article)
(:Article)-[:HAS_TOPIC]->(:Topic)
(:Author)-[:AUTHORED {timestamp: DateTime}]->(:Article)
(:Topic)-[:TAGGED_WITH]->(:Tag)
(:Article)-[:BELONGS_TO]->(:Community)
(:Topic)-[:PARENT_OF]->(:Topic)
```

### Constraints and Indexes

```cypher
// Uniqueness constraints
CREATE CONSTRAINT article_id_unique IF NOT EXISTS
FOR (a:Article) REQUIRE a.article_id IS UNIQUE;

CREATE CONSTRAINT topic_id_unique IF NOT EXISTS
FOR (t:Topic) REQUIRE t.topic_id IS UNIQUE;

CREATE CONSTRAINT author_id_unique IF NOT EXISTS
FOR (a:Author) REQUIRE a.author_id IS UNIQUE;

// Performance indexes
CREATE INDEX article_title_idx IF NOT EXISTS
FOR (a:Article) ON (a.article_title);

CREATE INDEX topic_name_idx IF NOT EXISTS
FOR (t:Topic) ON (t.topic_name);

CREATE INDEX author_name_idx IF NOT EXISTS
FOR (a:Author) ON (a.author_name);
```

---

## API Design

### Base URL
- Development: `http://localhost:8000`
- Production (via Nginx): `http://localhost:80`

### Endpoints

#### Core Endpoints

**GET /health**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

**GET /**
```json
{
  "message": "Knowledge Graph Wiki API",
  "version": "0.1.0",
  "docs": "/docs"
}
```

#### Graph Operations

**POST /api/v1/query**
```json
{
  "query": "MATCH (a:Article) RETURN a LIMIT 10",
  "parameters": {}
}
```

**POST /api/v1/search**
```json
{
  "search_term": "organization",
  "limit": 10
}
```

**GET /api/v1/entities/{entity_id}**
Returns entity details and properties.

**GET /api/v1/entities/{entity_id}/relationships?direction=both**
Returns incoming/outgoing/both relationships.

#### Advanced Operations

**POST /api/v1/advanced/pathfinding**
```json
{
  "source_id": 100,
  "target_id": 500,
  "max_depth": 5
}
```

**POST /api/v1/advanced/recommendations**
```json
{
  "article_id": 100,
  "limit": 10,
  "strategy": "community"  // or "references", "hybrid"
}
```

**GET /api/v1/advanced/analytics?top_n=10**
Returns comprehensive graph statistics.

**POST /api/v1/advanced/subgraph/export**
```json
{
  "community_id": 5,
  "include_cross_edges": false
}
```

**GET /api/v1/advanced/communities/{community_id}/stats**
Returns detailed community metrics.

---

## Database Schema

### Data Ingestion Pipeline

1. **CSV Import** (`data/query_wikiperdia/import/`)
   - `articles.csv`: Article metadata
   - `topics.csv`: Topic definitions
   - `authors.csv`: Author information
   - `article_topics.csv`: Article-topic relationships
   - `article_authors.csv`: Authorship data
   - `article_links.csv`: Cross-references
   - `topic_hierarchy.csv`: Topic parent-child
   - `topic_tags.csv`: Topic tagging
   - `tags.csv`: Tag definitions

2. **Schema Creation** (`db_modelisation/01_load_db.cypher`)
   - Create constraints
   - Create indexes
   - Load CSV files using `LOAD CSV`
   - Establish relationships

3. **Validation**
   - Count nodes and relationships
   - Verify constraints
   - Check index usage

### Query Patterns

#### Pattern 1: Semantic Search
```cypher
MATCH (a:Article)
WHERE a.article_title CONTAINS $term
RETURN a
LIMIT $limit
```

#### Pattern 2: Related Articles
```cypher
MATCH (source:Article {article_id: $id})-[:HAS_TOPIC]->(t:Topic)<-[:HAS_TOPIC]-(related:Article)
WHERE source <> related
RETURN related, count(t) as common_topics
ORDER BY common_topics DESC
LIMIT $limit
```

#### Pattern 3: Shortest Path
```cypher
MATCH path = shortestPath(
  (source:Article {article_id: $source_id})-[:REFERS_TO*..5]-(target:Article {article_id: $target_id})
)
RETURN path
```

#### Pattern 4: Community Detection
```cypher
MATCH (a:Article)-[:BELONGS_TO]->(c:Community {community_id: $id})
RETURN a, c
```

---

## Deployment Architecture

### Docker Compose Services

```yaml
services:
  neo4j:          # Graph database
    - Port 7474: Browser interface
    - Port 7687: Bolt protocol
    - GDS plugin enabled
    - Persistent volumes

  api:            # FastAPI application
    - Port 8000: API server
    - Health checks
    - Auto-restart
    - Environment-based config

  nginx:          # Reverse proxy
    - Port 80: Public interface
    - Rate limiting
    - Security headers
    - Load balancing
```

### Environment Configuration

**.env variables:**
```bash
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
API_TITLE=Knowledge Graph Wiki API
API_VERSION=0.1.0
ALLOWED_ORIGINS=["*"]
DEBUG=false
```

---

## Security Considerations

### 1. Authentication & Authorization
- **Current**: Open API (development)
- **Production**: JWT tokens or API keys required
- **Rate Limiting**: 10 requests/second per IP (Nginx)

### 2. Input Validation
- Pydantic models enforce type safety
- Query parameters validated
- SQL/Cypher injection prevention via parameterized queries

### 3. CORS Configuration
- Configurable allowed origins
- Credentials support
- Method restrictions

### 4. Network Security
- Services isolated in Docker network
- Nginx as single entry point
- Database not directly exposed

### 5. Security Headers (Nginx)
```nginx
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
```

---

## Performance Optimizations

### 1. Database Level
- **Indexes**: All frequently queried properties
- **Constraints**: Enforce uniqueness and speed lookups
- **Query Optimization**:
  - Use `LIMIT` to cap results
  - Parameterized queries for caching
  - `EXPLAIN`/`PROFILE` for query analysis

### 2. Application Level
- **Async I/O**: FastAPI async endpoints
- **Connection Pooling**: Neo4j driver handles connection reuse
- **Result Streaming**: Large result sets streamed vs. buffered

### 3. Infrastructure Level
- **Nginx Caching**: Static content and frequent queries
- **Load Balancing**: Multiple API instances (horizontal scaling)
- **Health Checks**: Automatic failover

### 4. Monitoring & Metrics
- Endpoint response times
- Database query performance
- Error rates and types
- Resource utilization (CPU, memory, disk)

---

## Development Workflow

### Local Development
```bash
# Setup
make venv
make install

# Start Neo4j
make docker-up

# Load data
make load-db

# Run API locally
make run

# Run tests
make test

# Check code quality
make lint
```

### Docker Development
```bash
# Full stack
make docker-run

# View logs
make docker-logs

# Teardown
make docker-down
```

### Testing Strategy
1. **Unit Tests**: Individual components (services, models)
2. **Integration Tests**: API endpoints with database
3. **Health Checks**: Container and service availability
4. **Coverage Target**: ≥60%

---

## Future Enhancements

### Planned Features
1. **Neo4j GDS Integration**
   - PageRank for article importance
   - Louvain for community detection
   - Node similarity algorithms

2. **Machine Learning**
   - Link prediction
   - Article classification
   - Embedding generation

3. **LLM Integration**
   - Natural language query interface
   - Semantic search enhancement
   - Answer generation from graph data

4. **Performance**
   - Redis caching layer
   - GraphQL API alternative
   - Materialized views for analytics

5. **Security**
   - OAuth2 authentication
   - Role-based access control
   - API key management

---

## References

- [Neo4j Documentation](https://neo4j.com/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Docker Documentation](https://docs.docker.com/)
- [Graph Data Science Library](https://neo4j.com/docs/graph-data-science/)
