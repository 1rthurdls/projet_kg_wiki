#!/bin/bash

# Demo Readiness Test Script
# This script checks if everything is ready for your demo

echo "========================================="
echo "  Knowledge Graph Wiki - Demo Check"
echo "========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check if Docker is running
echo "1. Checking Docker..."
if docker ps &> /dev/null; then
    echo -e "${GREEN}✓ Docker is running${NC}"
else
    echo -e "${RED}✗ Docker is not running${NC}"
    exit 1
fi

# Test 2: Check if Neo4j is running
echo ""
echo "2. Checking Neo4j..."
if docker ps | grep -q neo4j; then
    echo -e "${GREEN}✓ Neo4j container is running${NC}"
else
    echo -e "${RED}✗ Neo4j container is not running${NC}"
    echo "   Run: make docker-up"
    exit 1
fi

# Test 3: Check if API is running
echo ""
echo "3. Checking FastAPI..."
if docker ps | grep -q kg-wiki-api; then
    echo -e "${GREEN}✓ FastAPI container is running${NC}"
else
    echo -e "${RED}✗ FastAPI container is not running${NC}"
    echo "   Run: make docker-up"
    exit 1
fi

# Test 4: Test API health
echo ""
echo "4. Testing API health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✓ API is healthy${NC}"
    echo "   Response: $HEALTH_RESPONSE"
else
    echo -e "${RED}✗ API is not responding correctly${NC}"
    echo "   Response: $HEALTH_RESPONSE"
    exit 1
fi

# Test 5: Check database has data
echo ""
echo "5. Checking database data..."
ARTICLE_COUNT=$(curl -s -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (a:Article) RETURN count(a) as count", "parameters": {}}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['data'][0]['count'])" 2>/dev/null)

if [ "$ARTICLE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Database has data${NC}"
    echo "   Articles in database: $ARTICLE_COUNT"
else
    echo -e "${RED}✗ Database is empty${NC}"
    echo "   Run: make load-db"
    exit 1
fi

# Test 6: Check if Jupyter is installed
echo ""
echo "6. Checking Jupyter installation..."
if command -v jupyter &> /dev/null; then
    echo -e "${GREEN}✓ Jupyter is installed${NC}"
else
    echo -e "${YELLOW}⚠ Jupyter is not installed${NC}"
    echo "   Install with: pip install jupyter"
fi

# Test 7: Check if demo notebook exists
echo ""
echo "7. Checking demo notebook..."
if [ -f "demo.ipynb" ]; then
    echo -e "${GREEN}✓ Demo notebook exists${NC}"
else
    echo -e "${RED}✗ Demo notebook not found${NC}"
    exit 1
fi

# Summary
echo ""
echo "========================================="
echo -e "${GREEN}  All checks passed! You're ready to demo! ${NC}"
echo "========================================="
echo ""
echo "Quick start commands:"
echo "  • Open Swagger UI:    open http://localhost:8000/docs"
echo "  • Open Neo4j Browser: open http://localhost:7474"
echo "  • Start Jupyter:      jupyter notebook demo.ipynb"
echo ""
echo "Demo URLs:"
echo "  • API Health:  http://localhost:8000/health"
echo "  • API Docs:    http://localhost:8000/docs"
echo "  • Neo4j:       http://localhost:7474 (neo4j/password)"
echo ""
