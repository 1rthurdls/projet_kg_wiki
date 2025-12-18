#!/usr/bin/env python3
"""
Script to automatically load the Neo4j database from Cypher file.
"""

import time
from pathlib import Path
from neo4j import GraphDatabase


def wait_for_neo4j(driver, max_attempts=30):
    """Wait for Neo4j to be ready."""
    print("Waiting for Neo4j to be ready...")
    for attempt in range(max_attempts):
        try:
            driver.verify_connectivity()
            print("Neo4j is ready!")
            return True
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_attempts}: Neo4j not ready yet...")
            time.sleep(2)
    return False


def execute_cypher_file(driver, cypher_file_path):
    """Execute a Cypher file line by line."""
    print(f"Reading Cypher file: {cypher_file_path}")

    with open(cypher_file_path, 'r') as file:
        content = file.read()

    # Split by semicolons and filter out comments and empty statements
    statements = []
    current_statement = []

    for line in content.split('\n'):
        # Skip comment-only lines
        stripped = line.strip()
        if stripped.startswith('//') or not stripped:
            if not any(current_statement):
                continue

        current_statement.append(line)

        # Check if line ends with semicolon
        if stripped.endswith(';'):
            statement = '\n'.join(current_statement)
            # Remove comments from statement
            clean_statement = '\n'.join(
                l for l in statement.split('\n')
                if not l.strip().startswith('//')
            ).strip()

            if clean_statement and clean_statement != ';':
                statements.append(clean_statement)
            current_statement = []

    print(f"Found {len(statements)} statements to execute")

    with driver.session() as session:
        for i, statement in enumerate(statements, 1):
            try:
                # Skip certain visualization commands that don't work in driver
                if 'db.schema.visualization' in statement:
                    print(f"[{i}/{len(statements)}] Skipping visualization command")
                    continue

                print(f"[{i}/{len(statements)}] Executing statement...")
                result = session.run(statement)

                # Try to consume and display results
                try:
                    records = list(result)
                    if records:
                        print(f"  → Result: {records}")
                except:
                    pass

            except Exception as e:
                print(f"  ⚠️  Error executing statement {i}: {e}")
                print(f"  Statement: {statement[:100]}...")


def main():
    # Configuration
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "password"

    # Path to Cypher file
    project_root = Path(__file__).parent.parent
    cypher_file = project_root / "db_modelisation" / "01_load_db.cypher"

    if not cypher_file.exists():
        print(f"Error: Cypher file not found at {cypher_file}")
        return

    print("=" * 60)
    print("Neo4j Database Loader")
    print("=" * 60)

    # Connect to Neo4j
    print(f"Connecting to Neo4j at {NEO4J_URI}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        # Wait for Neo4j to be ready
        if not wait_for_neo4j(driver):
            print("Error: Neo4j did not become ready in time")
            return

        # Execute the Cypher file
        execute_cypher_file(driver, cypher_file)

        print("\n" + "=" * 60)
        print("Database loaded successfully!")
        print("=" * 60)

        # Verification queries
        print("\nVerification:")
        with driver.session() as session:
            article_count = session.run("MATCH (a:Article) RETURN count(a) AS count").single()["count"]
            community_count = session.run("MATCH (c:Community) RETURN count(c) AS count").single()["count"]
            refers_count = session.run("MATCH ()-[r:REFERS_TO]-() RETURN count(r) AS count").single()["count"]
            belongs_count = session.run("MATCH ()-[r:BELONGS_TO]->() RETURN count(r) AS count").single()["count"]

            print(f"  Articles: {article_count}")
            print(f"  Communities: {community_count}")
            print(f"  REFERS_TO relationships: {refers_count}")
            print(f"  BELONGS_TO relationships: {belongs_count}")

    finally:
        driver.close()


if __name__ == "__main__":
    main()
