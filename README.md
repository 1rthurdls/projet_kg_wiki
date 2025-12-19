# Knowledge Graph Wiki System 📚

[![Lint](https://github.com/YOUR_USERNAME/projet_kg_wiki/workflows/Lint/badge.svg)](https://github.com/YOUR_USERNAME/projet_kg_wiki/actions)
[![Test](https://github.com/YOUR_USERNAME/projet_kg_wiki/workflows/Test/badge.svg)](https://github.com/YOUR_USERNAME/projet_kg_wiki/actions)
[![Docker](https://github.com/YOUR_USERNAME/projet_kg_wiki/workflows/Docker%20Build/badge.svg)](https://github.com/YOUR_USERNAME/projet_kg_wiki/actions)
[![codecov](https://codecov.io/gh/YOUR_USERNAME/projet_kg_wiki/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/projet_kg_wiki)

A comprehensive knowledge graph system built with Neo4j and FastAPI that enables semantic search, article recommendations, and advanced graph analytics on Wikipedia data. This project implements **Project #6 (Knowledge Graph / Wiki System)** from the AIDAMS 3A GraphDB course requirements.

## 🎯 Project Overview

**Use Case**: Company internal knowledge base with graph-powered features

**Key Features**:
- 🔍 **Semantic Search**: Find articles through connected concepts and topics
- 📊 **Related Articles**: Intelligent recommendations based on graph relationships
- 🗺️ **Topic Exploration**: Navigate hierarchical topic structures with customizable depth
- ✍️ **Author Tracking**: Monitor contributions and authorship patterns
- 🎯 **Community Detection**: Identify article clusters using advanced graph algorithms
- 📈 **Advanced Analytics**: Comprehensive graph statistics and network metrics

**Difficulty Level**: 1 (Introductory) - Extended with advanced features

## 📑 Table of Contents

- [Quick Start](#-quick-start)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Running the Application](#-running-the-application)
- [API Documentation](#-api-documentation)
- [Testing](#-testing)
- [Architecture](#-architecture)
- [Team Contributions](#-team-contributions)
- [Project Structure](#-project-structure)
- [Development Workflow](#-development-workflow)
- [Troubleshooting](#-troubleshooting)

---

## 🚀 Quick Start

The fastest way to get the entire stack running:

```bash
# Clone the repository
git clone <repository-url>
cd projet_kg_wiki

# Copy environment file
cp .env.example .env

# Install dependencies (optional for local development)
make install

# Build and start all services (Neo4j + FastAPI + Nginx)
make docker-run

# Load the Wikipedia knowledge graph data
make load-db
```

**Access Points**:
- 🌐 **API (via Nginx)**: http://localhost:80
- 📖 **API Docs**: http://localhost:80/docs
- 🔍 **Neo4j Browser**: http://localhost:7474 (user: `neo4j`, password: `password`)
- 🐳 **Direct API**: http://localhost:8000 (bypasses Nginx)

---

## 📋 Prerequisites

Ensure you have the following installed:

- **Python**: 3.12 or higher
- **Docker**: 20.10+ and Docker Compose
- **Make**: For convenience commands (optional but recommended)
- **Git**: For version control

---

## 📦 Installation

### Method 1: Docker (Recommended)

This method runs everything in containers - **no local Python setup required**.

```bash
# Copy environment file
cp .env.example .env

# Build and start all services
make docker-run

# Load database
make load-db
```

### Method 2: Local Development

For development with hot-reload and debugging:

```bash
# Create virtual environment and install dependencies
make install

# Start only Neo4j in Docker
make docker-up

# Load database
make load-db

# Run FastAPI locally with auto-reload
make run
```

---

## 🏃 Running the Application

### Full Stack with Docker

```bash
# Start all services (Neo4j, FastAPI, Nginx)
make docker-run

# View logs
make docker-logs

# Stop all services
make docker-down
```

### Local Development Mode

```bash
# Terminal 1: Start Neo4j
make docker-up

# Terminal 2: Load data (first time only)
make load-db

# Terminal 3: Run FastAPI with hot-reload
make run
```

### Available Make Commands

Run `make help` to see all available commands:

```
Commands:
  make venv          Create local virtualenv (.venv)
  make install       Install requirements into .venv
  make run           Run FastAPI (uvicorn) on :8000
  make docker-build  Build Docker image (TAG=kg-wiki-api:latest)
  make docker-up     Start all services (Neo4j + API + Nginx)
  make docker-down   Stop all services
  make docker-run    Run full stack with Docker Compose
  make docker-logs   Show logs from all containers
  make load-db       Load database from Cypher script
  make reload        Restart and reload database
  make test          Run pytest with coverage
  make lint          Run pylint
  make format        Run black code formatter
  make clean         Remove caches and temp files
  make tree          Show project tree (depth 3)
```

---

## 📚 API Documentation

### Interactive Documentation

Once the application is running, visit:

- **Swagger UI**: http://localhost:80/docs (or http://localhost:8000/docs)
- **ReDoc**: http://localhost:80/redoc

### Health Check

Verify the API and database are running:

```bash
curl http://localhost:80/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### Core Endpoints

#### 1. Semantic Search
```bash
curl -X POST http://localhost:80/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "search_term": "organization",
    "limit": 10
  }'
```

#### 2. Related Articles
```bash
curl -X POST http://localhost:80/api/v1/advanced/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "article_id": 100,
    "limit": 10,
    "strategy": "community"
  }'
```

Strategies: `community`, `references`, `hybrid`

#### 3. Topic Exploration
```bash
curl -X POST http://localhost:80/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (t:Topic {topic_id: $topic_id})-[:PARENT_OF*0..2]->(child:Topic) RETURN t, child",
    "parameters": {"topic_id": 1}
  }'
```

#### 4. Author Contributions
```bash
curl -X POST http://localhost:80/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (au:Author {author_id: $author_id})-[:AUTHORED]->(a:Article) RETURN au, a",
    "parameters": {"author_id": 1}
  }'
```

#### 5. Shortest Path (Advanced)
```bash
curl -X POST http://localhost:80/api/v1/advanced/pathfinding \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": 100,
    "target_id": 500,
    "max_depth": 5
  }'
```

#### 6. Graph Analytics
```bash
curl http://localhost:80/api/v1/advanced/analytics?top_n=10
```

#### 7. Community Subgraph Export
```bash
curl -X POST http://localhost:80/api/v1/advanced/subgraph/export \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 1,
    "include_cross_edges": false
  }'
```

### Example Responses

See the [ARCHITECTURE.md](./ARCHITECTURE.md) file for detailed API specifications and response schemas.

---

## 🧪 Testing

### Run All Tests

```bash
# With virtual environment
make test

# Or directly with pytest
pytest
```

### Run Specific Test Files

```bash
pytest tests/test_main.py
pytest tests/test_database.py
pytest tests/test_graph_router.py
pytest tests/test_advanced_router.py
```

### Coverage Report

Tests automatically generate coverage reports:

```bash
# HTML report (open in browser)
open htmlcov/index.html

# Terminal report
pytest --cov=app --cov-report=term-missing
```

**Current Coverage**: Target ≥60%

---

## 🏗️ Architecture

The system uses a three-tier architecture:

```
┌─────────────┐
│   Nginx     │  ← Reverse proxy, rate limiting, security headers
│  (Port 80)  │
└──────┬──────┘
       │
┌──────▼──────┐
│   FastAPI   │  ← RESTful API, business logic, Pydantic validation
│  (Port 8000)│
└──────┬──────┘
       │
┌──────▼──────┐
│   Neo4j 5   │  ← Graph database, GDS library, Cypher queries
│(Port 7474/  │
│     7687)   │
└─────────────┘
```

### Technology Stack

- **Backend**: FastAPI 0.115+, Pydantic 2.0+, Python 3.12+
- **Database**: Neo4j 5.x with Graph Data Science (GDS) library
- **Proxy**: Nginx (rate limiting, security)
- **Testing**: Pytest, pytest-cov, pytest-asyncio
- **Quality**: Pylint, Black, isort
- **CI/CD**: GitHub Actions (Lint, Test, Docker Build)
- **Containerization**: Docker & Docker Compose

### Graph Schema

```cypher
// Node Types
(:Article {article_id, article_url, article_title, concept_id})
(:Topic {topic_id, topic_name, level})
(:Author {author_id, author_name, edit_count})
(:Tag {tag_name})
(:Community {community_id, size, density, avg_degree})

// Relationships
(:Article)-[:REFERS_TO]->(:Article)
(:Article)-[:HAS_TOPIC]->(:Topic)
(:Author)-[:AUTHORED]->(:Article)
(:Topic)-[:TAGGED_WITH]->(:Tag)
(:Article)-[:BELONGS_TO]->(:Community)
(:Topic)-[:PARENT_OF]->(:Topic)
```

For detailed architecture information, see [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## 📁 Project Structure

```
projet_kg_wiki/
├── .github/
│   └── workflows/           # GitHub Actions CI/CD
│       ├── lint.yml
│       ├── test.yml
│       └── docker.yml
├── app/
│   ├── main.py             # FastAPI application entry point
│   ├── database/           # Neo4j service and connection
│   │   ├── __init__.py
│   │   └── neo4j.py
│   ├── models/             # Pydantic models and config
│   │   ├── config.py       # Settings management
│   │   └── schemas.py      # Request/response models
│   ├── routers/            # API route handlers
│   │   ├── graph_router.py      # Basic graph operations
│   │   └── advanced_router.py   # Complex queries & algorithms
│   └── services/           # Business logic (if needed)
├── data/
│   └── query_wikiperdia/
│       ├── import/         # CSV data files
│       │   ├── articles.csv
│       │   ├── topics.csv
│       │   ├── authors.csv
│       │   └── ...
│       └── db_modelisation/
│           └── 01_load_db.cypher  # Database schema & load script
├── tests/
│   ├── conftest.py         # Pytest fixtures
│   ├── test_main.py        # Main app tests
│   ├── test_database.py    # Database tests
│   ├── test_graph_router.py
│   └── test_advanced_router.py
├── .env.example            # Environment template
├── .gitignore
├── .pylintrc               # Pylint configuration
├── ARCHITECTURE.md         # Detailed architecture docs
├── demo.ipynb              # Jupyter notebook demo
├── docker-compose.yml      # Service orchestration
├── Dockerfile              # FastAPI container build
├── load_database.sh        # Database loading script
├── Makefile                # Automation commands
├── nginx.conf              # Nginx reverse proxy config
├── pytest.ini              # Pytest configuration
├── pyproject.toml          # Python project metadata
├── README.md               # This file
└── requirements.txt        # Python dependencies
```

---

## 💻 Development Workflow

### 1. Local Development

```bash
# Setup
make install

# Start Neo4j only
make docker-up

# Load data
make load-db

# Run API with hot-reload
make run

# In another terminal, run tests
make test

# Check code quality
make lint
```

### 2. Code Quality

```bash
# Format code
make format

# Run linter
make lint

# View project structure
make tree
```

### 3. Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes and commit
git add .
git commit -m "feat: add your feature"

# Push and create PR
git push origin feature/your-feature
```

### 4. CI/CD Pipeline

On every push/PR:
1. **Lint**: Code quality checks (Pylint, Black, isort)
2. **Test**: Full test suite with coverage
3. **Docker**: Build verification

---

## 🐛 Troubleshooting

### Database Connection Issues

**Problem**: Health check shows `"database": "disconnected"`

**Solutions**:
```bash
# 1. Check if Neo4j is running
docker ps | grep neo4j

# 2. View Neo4j logs
make docker-logs

# 3. Restart Neo4j
make docker-down
make docker-up

# 4. Reload database
make load-db
```

### Port Already in Use

**Problem**: `Error: bind: address already in use`

**Solutions**:
```bash
# Check what's using the port
lsof -i :7474
lsof -i :7687
lsof -i :8000
lsof -i :80

# Kill the process or change ports in docker-compose.yml
```

### API Not Starting

**Solutions**:
```bash
# 1. Verify Python version
python --version  # Should be 3.12+

# 2. Reinstall dependencies
make clean
make install

# 3. Check environment variables
cat .env

# 4. Check for syntax errors
pylint app
```

### Docker Issues

**Solutions**:
```bash
# Clean Docker resources
make clean
docker system prune -a

# Rebuild from scratch
make docker-build
make docker-run
```

### Test Failures

**Solutions**:
```bash
# Run tests with verbose output
pytest -vv

# Run specific test
pytest tests/test_main.py::test_health_check_endpoint -vv

# Check coverage
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

---

## 📊 Demo Notebook

Explore the knowledge graph interactively using the Jupyter notebook:

```bash
# Install Jupyter if not already installed
pip install jupyter

# Start Jupyter
jupyter notebook demo.ipynb
```

The notebook includes:
- Database statistics and visualizations
- Graph exploration queries
- API endpoint demonstrations
- Network visualizations with NetworkX
- Sample analytics queries

---

## 🔗 Data Sources

- **WikiGraphs Dataset**: [GitHub - benedekrozemberczki/datasets](https://github.com/benedekrozemberczki/datasets)
- **Wikidata**: [query.wikidata.org](https://query.wikidata.org/)
- **Custom Generated**: Article relationships and metadata

---

## 📄 License

This project is developed for educational purposes as part of the AIDAMS 3A GraphDB course.

---

## 📞 Support

For issues and questions:
- Create an issue in the GitHub repository
- Contact the team lead
- Check the [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed documentation

---

## 🎓 Course Information

**Course**: GraphDB - AIDAMS 3A
**Project**: #6 - Knowledge Graph / Wiki System
**Academic Year**: 2024-2025
**Difficulty**: Level 1 (Extended with advanced features)
