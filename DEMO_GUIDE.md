# Demo Presentation Guide

## Pre-Demo Checklist

### Before Your Presentation:

```bash
# 1. Start all services
make docker-up

# 2. Load the database
make load-db

# 3. Verify everything is working
curl http://localhost:8000/health
```

Expected output: `{"status": "healthy", "database": "connected"}`

---

## Demo Option 1: Interactive Jupyter Notebook (Recommended)

### Setup (5 minutes before demo):

```bash
# Activate virtual environment
source .venv/bin/activate

# Start Jupyter
jupyter notebook demo.ipynb
```

### Presentation Flow (15-20 minutes):

#### 1. **Introduction (2 min)**
   - "We built a Knowledge Graph Wiki System using Neo4j and FastAPI"
   - "It stores 266 Wikipedia articles with topics, authors, and relationships"
   - "Three-tier architecture: Nginx → FastAPI → Neo4j"

#### 2. **Show Database Statistics (3 min)**
   - Run cells 1-7 in notebook
   - **Point out:**
     - 266 Articles
     - 266 Topics
     - 851 Real Wikipedia Authors
     - Beautiful bar chart visualization

#### 3. **Graph Exploration (4 min)**
   - Run cells 8-12
   - **Show:**
     - Most connected articles
     - Topic distribution
     - Interactive visualizations

#### 4. **API Demonstrations (4 min)**
   - Run cells 13-15
   - **Demonstrate:**
     - Search functionality
     - Graph analytics
     - Real-time API calls

#### 5. **Advanced Queries (3 min)**
   - Run cells 16-18
   - **Show:**
     - Multi-topic articles
     - Author contributions
     - Complex Cypher queries

#### 6. **Network Visualization (4 min)**
   - Run cells 19-22
   - **Showcase:**
     - Article reference network graph
     - Degree distribution
     - NetworkX visualization

---

## Demo Option 2: Live API Browser Demo

### URLs to Open:

1. **Swagger UI** (Interactive API Docs):
   ```
   http://localhost:8000/docs
   ```

2. **Neo4j Browser** (Graph Visualization):
   ```
   http://localhost:7474
   ```
   - Username: `neo4j`
   - Password: `password`

### Presentation Flow (10-15 minutes):

#### 1. **API Documentation** (5 min)

   Open: `http://localhost:8000/docs`

   **Demonstrate these endpoints:**

   a. **Health Check**
   ```
   GET /health
   ```
   Click "Try it out" → "Execute"
   Show: `{"status": "healthy", "database": "connected"}`

   b. **Search Endpoint**
   ```
   POST /api/v1/search
   ```
   Body:
   ```json
   {
     "search_term": "organization",
     "limit": 5
   }
   ```

   c. **Custom Query**
   ```
   POST /api/v1/query
   ```
   Body:
   ```json
   {
     "query": "MATCH (a:Article) RETURN a.article_title LIMIT 10",
     "parameters": {}
   }
   ```

   d. **Graph Analytics**
   ```
   GET /api/v1/advanced/analytics?top_n=10
   ```

#### 2. **Neo4j Browser** (5 min)

   Open: `http://localhost:7474`

   **Run these Cypher queries:**

   a. **Visualize Article Network**
   ```cypher
   MATCH (a:Article)-[r:LINKS_TO]->(b:Article)
   RETURN a, r, b LIMIT 25
   ```

   b. **Show Topic Hierarchy**
   ```cypher
   MATCH (t:Topic)-[:SUBCLASS_OF]->(parent:Topic)
   RETURN t, parent LIMIT 30
   ```

   c. **Author Contributions**
   ```cypher
   MATCH (au:Author)-[:CONTRIBUTED_TO]->(a:Article)
   RETURN au, a LIMIT 50
   ```

   d. **Database Statistics**
   ```cypher
   MATCH (a:Article)
   WITH count(a) as articles
   MATCH (t:Topic)
   WITH articles, count(t) as topics
   MATCH (au:Author)
   RETURN articles, topics, count(au) as authors
   ```

---

## Demo Option 3: Command Line Demo

### Quick Terminal Commands:

```bash
# 1. Health Check
curl http://localhost:8000/health | jq

# 2. Search for articles
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"search_term": "organization", "limit": 5}' | jq

# 3. Get all articles
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (a:Article) RETURN a.article_title as title LIMIT 10", "parameters": {}}' | jq

# 4. Get topics
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (t:Topic) RETURN t.topic_name as topic LIMIT 10", "parameters": {}}' | jq

# 5. Author contributions
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (au:Author)-[:CONTRIBUTED_TO]->(a:Article) RETURN au.author_name as author, count(a) as contributions ORDER BY contributions DESC LIMIT 10", "parameters": {}}' | jq

# 6. Show tests passing
make test
```

---

## Key Points to Emphasize

### Technical Achievements:
- ✅ **Three-tier architecture**: Nginx (reverse proxy) → FastAPI (API) → Neo4j (database)
- ✅ **67% test coverage** (exceeds 60% requirement)
- ✅ **Real Wikipedia data**: 266 articles with real authors from XTools
- ✅ **Docker containerization**: Everything runs with `make docker-run`
- ✅ **CI/CD pipeline**: Automated testing with GitHub Actions
- ✅ **Comprehensive documentation**: README, ARCHITECTURE, HOW_IT_WORKS

### Graph Features:
- ✅ **Graph algorithms**: Pathfinding, community detection
- ✅ **Advanced queries**: Multi-hop relationships, pattern matching
- ✅ **Real-time analytics**: Graph statistics and metrics
- ✅ **Recommendations**: Community-based and reference-based strategies

### Data Quality:
- ✅ **Real Wikipedia authors** extracted using XTools API
- ✅ **WikiGraphs dataset** for article relationships
- ✅ **Hierarchical topic structure** with SUBCLASS_OF relationships
- ✅ **Rich metadata**: Tags, edit counts, article links

---

## Common Questions & Answers

**Q: How did you get the data?**
A: We used the WikiGraphs dataset for articles and the Wikipedia XTools API to fetch real author data. The data is loaded via Cypher scripts.

**Q: What graph algorithms did you implement?**
A: Pathfinding (shortest path), community detection, degree centrality, and recommendation algorithms using both graph structure and content similarity.

**Q: How scalable is this?**
A: The system uses Neo4j which can handle billions of nodes and relationships. We implemented proper indexing and optimized queries. Docker makes it easy to scale horizontally.

**Q: Can you add new data?**
A: Yes! The system is designed to ingest new data. Just add CSV files to the import directory and run the Cypher load script.

**Q: How do you ensure code quality?**
A: We use pytest for testing (67% coverage), pylint for linting, black for formatting, and GitHub Actions for CI/CD.

---

## Backup Plan (If Something Goes Wrong)

If services aren't running:
```bash
# Quick restart
make docker-down
make docker-up
make load-db
```

If database is empty:
```bash
make load-db
```

If Jupyter doesn't work:
- Fall back to browser demo (Swagger UI)
- Or use curl commands in terminal

---

## Time Management

**For 10-minute demo:**
- Introduction: 1 min
- Swagger UI demo: 4 min
- Neo4j Browser: 4 min
- Q&A: 1 min

**For 15-minute demo:**
- Introduction: 2 min
- Jupyter notebook highlights: 8 min
- Architecture explanation: 3 min
- Q&A: 2 min

**For 20-minute demo:**
- Full Jupyter notebook walkthrough: 15 min
- Architecture + Code review: 3 min
- Q&A: 2 min

---

## Final Checklist Before Demo

- [ ] All Docker containers running
- [ ] Database loaded (266 articles)
- [ ] Health check returns "healthy"
- [ ] Browser tabs prepared (Swagger, Neo4j)
- [ ] Jupyter notebook tested
- [ ] Backup plan ready
- [ ] Presentation notes reviewed

Good luck! 🚀
