#!/bin/bash

# Wait for Neo4j to be ready
echo "Waiting for Neo4j to be ready..."
until docker exec neo4j cypher-shell -u neo4j -p password "RETURN 1;" > /dev/null 2>&1; do
  echo "Neo4j is unavailable - sleeping"
  sleep 2
done

echo "Neo4j is up - executing database load script"

# Execute the Cypher script
docker exec -i neo4j cypher-shell -u neo4j -p password < data/query_wikiperdia/db_modelisation/01_load_db.cypher

echo "Database loaded successfully!"
