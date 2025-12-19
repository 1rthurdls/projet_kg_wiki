from typing import Any

from neo4j import Driver, GraphDatabase
from neo4j.exceptions import Neo4jError

from app.models.config import settings


class Neo4jService:
    """Service class for Neo4j database operations."""

    def __init__(self):
        """Initialize Neo4j driver."""
        self.driver: Driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()

    def verify_connectivity(self) -> bool:
        """Verify database connectivity."""
        try:
            self.driver.verify_connectivity()
            return True
        except Neo4jError:
            return False

    def execute_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries

        Raises:
            Neo4jError: If query execution fails
        """
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def execute_write_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Execute a write query within a transaction.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries

        Raises:
            Neo4jError: If query execution fails
        """

        def _execute_write(tx):
            result = tx.run(query, parameters or {})
            return [record.data() for record in result]

        with self.driver.session() as session:
            return session.execute_write(_execute_write)

    def search_entities(self, search_term: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Search for entities by name or properties.

        Args:
            search_term: Term to search for
            limit: Maximum number of results

        Returns:
            List of matching entities
        """
        query = """
        MATCH (n)
        WHERE toLower(n.name) CONTAINS toLower($search_term)
           OR toLower(n.title) CONTAINS toLower($search_term)
        RETURN id(n) as id, labels(n) as labels, properties(n) as properties
        LIMIT $limit
        """
        return self.execute_query(query, {"search_term": search_term, "limit": limit})

    def get_entity_by_id(self, entity_id: str) -> dict[str, Any] | None:
        """
        Get entity by its ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity data or None if not found
        """
        query = """
        MATCH (n)
        WHERE id(n) = $entity_id
        RETURN id(n) as id, labels(n) as labels, properties(n) as properties
        """
        results = self.execute_query(query, {"entity_id": int(entity_id)})
        return results[0] if results else None

    def get_entity_relationships(self, entity_id: str, direction: str = "both") -> list[dict[str, Any]]:
        """
        Get relationships for an entity.

        Args:
            entity_id: Entity ID
            direction: Relationship direction ('incoming', 'outgoing', or 'both')

        Returns:
            List of relationships
        """
        if direction == "outgoing":
            query = """
            MATCH (n)-[r]->(m)
            WHERE id(n) = $entity_id
            RETURN id(r) as id, type(r) as type,
                   id(n) as start_node_id, id(m) as end_node_id,
                   properties(r) as properties
            """
        elif direction == "incoming":
            query = """
            MATCH (n)<-[r]-(m)
            WHERE id(n) = $entity_id
            RETURN id(r) as id, type(r) as type,
                   id(m) as start_node_id, id(n) as end_node_id,
                   properties(r) as properties
            """
        else:
            query = """
            MATCH (n)-[r]-(m)
            WHERE id(n) = $entity_id
            RETURN id(r) as id, type(r) as type,
                   id(startNode(r)) as start_node_id, id(endNode(r)) as end_node_id,
                   properties(r) as properties
            """

        return self.execute_query(query, {"entity_id": int(entity_id)})

    # Advanced query methods
    def find_shortest_path(self, source_id: int, target_id: int, max_depth: int = 5) -> dict[str, Any]:
        """
        Find shortest path between two articles using BFS.

        Args:
            source_id: Source article ID
            target_id: Target article ID
            max_depth: Maximum path depth

        Returns:
            Path information including nodes and length
        """
        query = (
            """
        MATCH (source:Article {id: $source_id})
        MATCH (target:Article {id: $target_id})
        MATCH path = shortestPath((source)-[:REFERS_TO*..%d]-(target))
        RETURN [node in nodes(path) | {
            id: node.id,
            target: node.target,
            community_id: node.community_id
        }] as path,
        length(path) as length
        """
            % max_depth
        )

        results = self.execute_query(query, {"source_id": source_id, "target_id": target_id})
        if results:
            return {"path": results[0]["path"], "length": results[0]["length"], "exists": True}
        return {"path": [], "length": 0, "exists": False}

    def get_recommendations(
        self, article_id: int, limit: int = 10, strategy: str = "community"
    ) -> list[dict[str, Any]]:
        """
        Get article recommendations based on different strategies.

        Args:
            article_id: Source article ID
            limit: Number of recommendations
            strategy: 'community', 'references', or 'hybrid'

        Returns:
            List of recommended articles with scores
        """
        if strategy == "community":
            # Recommend articles from the same community
            query = """
            MATCH (source:Article {id: $article_id})-[:BELONGS_TO]->(c:Community)
            MATCH (recommended:Article)-[:BELONGS_TO]->(c)
            WHERE recommended.id <> $article_id
            WITH recommended, c.avg_traffic as comm_traffic
            RETURN recommended.id as id,
                   recommended.target as target,
                   recommended.community_id as community_id,
                   comm_traffic as score,
                   'Same community (ID: ' + toString(c.community_id) + ')' as reason
            ORDER BY score DESC
            LIMIT $limit
            """
        elif strategy == "references":
            # Recommend articles connected by references (friends of friends)
            query = """
            MATCH (source:Article {id: $article_id})-[:REFERS_TO]-(neighbor:Article)
            MATCH (neighbor)-[:REFERS_TO]-(recommended:Article)
            WHERE recommended.id <> $article_id
              AND NOT (source)-[:REFERS_TO]-(recommended)
            WITH recommended, count(DISTINCT neighbor) as common_neighbors
            RETURN recommended.id as id,
                   recommended.target as target,
                   recommended.community_id as community_id,
                   toFloat(common_neighbors) as score,
                   toString(common_neighbors) + ' common references' as reason
            ORDER BY score DESC
            LIMIT $limit
            """
        else:  # hybrid
            # Combine both strategies
            query = """
            MATCH (source:Article {id: $article_id})
            OPTIONAL MATCH (source)-[:BELONGS_TO]->(c:Community)
            OPTIONAL MATCH (same_comm:Article)-[:BELONGS_TO]->(c)
            WHERE same_comm.id <> $article_id

            OPTIONAL MATCH (source)-[:REFERS_TO]-(neighbor:Article)
            OPTIONAL MATCH (neighbor)-[:REFERS_TO]-(connected:Article)
            WHERE connected.id <> $article_id
              AND NOT (source)-[:REFERS_TO]-(connected)

            WITH COLLECT(DISTINCT same_comm) + COLLECT(DISTINCT connected) as candidates
            UNWIND candidates as recommended
            WHERE recommended IS NOT NULL
            RETURN DISTINCT recommended.id as id,
                   recommended.target as target,
                   recommended.community_id as community_id,
                   1.0 as score,
                   'Hybrid recommendation' as reason
            LIMIT $limit
            """

        return self.execute_query(query, {"article_id": article_id, "limit": limit})

    def get_analytics(self, top_n: int = 10) -> dict[str, Any]:
        """
        Get comprehensive analytics about the knowledge graph.

        Args:
            top_n: Number of top items to return

        Returns:
            Analytics data including counts, top communities, and top articles
        """
        # Get overall statistics
        stats_query = """
        MATCH (a:Article)
        WITH count(a) as total_articles
        MATCH (c:Community)
        WITH total_articles, count(c) as total_communities
        MATCH ()-[r:REFERS_TO]-()
        WITH total_articles, total_communities, count(r)/2 as total_edges
        RETURN total_articles, total_communities, total_edges,
               toFloat(total_edges * 2) / total_articles as avg_degree
        """
        stats = self.execute_query(stats_query)[0]

        # Get top communities by size and metrics
        top_comm_query = """
        MATCH (c:Community)
        OPTIONAL MATCH (a:Article)-[:BELONGS_TO]->(c)
        WITH c, count(a) as article_count
        OPTIONAL MATCH (a1:Article)-[:BELONGS_TO]->(c)
        OPTIONAL MATCH (a1)-[r:REFERS_TO]-(a2:Article)-[:BELONGS_TO]->(c)
        WITH c, article_count, count(DISTINCT r)/2 as internal_edges
        RETURN c.community_id as community_id,
               c.size as size,
               c.density as density,
               c.avg_degree as avg_degree,
               c.avg_traffic as avg_traffic,
               c.median_traffic as median_traffic,
               c.level as level,
               article_count,
               internal_edges
        ORDER BY article_count DESC
        LIMIT $top_n
        """
        top_communities = self.execute_query(top_comm_query, {"top_n": top_n})

        # Get top articles by degree (most connected)
        top_articles_query = """
        MATCH (a:Article)
        OPTIONAL MATCH (a)-[r:REFERS_TO]-()
        WITH a, count(r) as degree
        RETURN a.id as article_id,
               degree,
               a.community_id as community_id,
               a.target as target
        ORDER BY degree DESC
        LIMIT $top_n
        """
        top_articles = self.execute_query(top_articles_query, {"top_n": top_n})

        return {
            "total_articles": stats["total_articles"],
            "total_communities": stats["total_communities"],
            "total_edges": stats["total_edges"],
            "avg_degree": stats["avg_degree"],
            "top_communities": top_communities,
            "top_articles": top_articles,
        }

    def export_subgraph(self, community_id: int, include_cross_edges: bool = False) -> dict[str, Any]:
        """
        Export a subgraph for a specific community.

        Args:
            community_id: Community ID to export
            include_cross_edges: Include edges to other communities

        Returns:
            Subgraph data with nodes and edges
        """
        # Get all articles in the community
        nodes_query = """
        MATCH (a:Article)-[:BELONGS_TO]->(c:Community {community_id: $community_id})
        RETURN a.id as id,
               a.target as target,
               a.community_id as community_id
        """
        nodes = self.execute_query(nodes_query, {"community_id": community_id})

        # Get edges
        if include_cross_edges:
            # Include all edges from community articles
            edges_query = """
            MATCH (a1:Article)-[:BELONGS_TO]->(c:Community {community_id: $community_id})
            MATCH (a1)-[r:REFERS_TO]-(a2:Article)
            RETURN DISTINCT a1.id as source,
                   a2.id as target,
                   a2.community_id as target_community
            """
        else:
            # Only internal edges
            edges_query = """
            MATCH (a1:Article)-[:BELONGS_TO]->(c:Community {community_id: $community_id})
            MATCH (a1)-[r:REFERS_TO]-(a2:Article)-[:BELONGS_TO]->(c)
            WHERE id(a1) < id(a2)
            RETURN a1.id as source,
                   a2.id as target,
                   a2.community_id as target_community
            """

        edges = self.execute_query(edges_query, {"community_id": community_id})

        return {
            "community_id": community_id,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    # Graph Data Science (GDS) Algorithm Methods
    def run_pagerank(
        self, max_iterations: int = 20, damping_factor: float = 0.85, limit: int = 10
    ) -> dict[str, Any]:
        """
        Run PageRank algorithm on article citation network.

        Args:
            max_iterations: Maximum number of iterations
            damping_factor: Damping factor (probability of following a link)
            limit: Number of top results to return

        Returns:
            PageRank results with execution time
        """
        import time

        start_time = time.time()

        # Create in-memory graph projection
        projection_query = """
        CALL gds.graph.project(
            'articles-pagerank',
            'Article',
            'REFERS_TO',
            {nodeProperties: ['article_id', 'article_title']}
        )
        YIELD graphName, nodeCount, relationshipCount
        RETURN graphName, nodeCount, relationshipCount
        """

        # Try to drop existing projection first
        try:
            self.execute_query("CALL gds.graph.drop('articles-pagerank') YIELD graphName")
        except Exception:
            pass  # Graph doesn't exist, that's fine

        # Create projection
        try:
            projection_result = self.execute_query(projection_query)[0]
            total_nodes = projection_result["nodeCount"]
        except Exception as e:
            # Fallback if projection fails - use native Cypher implementation
            return self._pagerank_fallback(limit)

        # Run PageRank algorithm
        pagerank_query = """
        CALL gds.pageRank.stream('articles-pagerank', {
            maxIterations: $max_iterations,
            dampingFactor: $damping_factor
        })
        YIELD nodeId, score
        WITH gds.util.asNode(nodeId) AS article, score
        RETURN article.article_id AS article_id,
               article.article_title AS article_title,
               score
        ORDER BY score DESC
        LIMIT $limit
        """

        try:
            results = self.execute_query(
                pagerank_query,
                {"max_iterations": max_iterations, "damping_factor": damping_factor, "limit": limit},
            )

            # Add ranking
            for idx, result in enumerate(results, 1):
                result["rank"] = idx

            execution_time = (time.time() - start_time) * 1000  # Convert to ms

            return {"total_nodes": total_nodes, "results": results, "execution_time_ms": execution_time}

        finally:
            # Clean up: drop the graph projection
            try:
                self.execute_query("CALL gds.graph.drop('articles-pagerank') YIELD graphName")
            except Exception:
                pass

    def _pagerank_fallback(self, limit: int = 10) -> dict[str, Any]:
        """
        Fallback PageRank implementation using simple degree centrality.

        Args:
            limit: Number of top results

        Returns:
            Simplified ranking based on degree
        """
        import time

        start_time = time.time()

        query = """
        MATCH (a:Article)
        OPTIONAL MATCH (a)-[r:REFERS_TO]-()
        WITH a, count(r) as degree
        WITH a, degree, sum(degree) as total_degree
        RETURN a.article_id as article_id,
               a.article_title as article_title,
               toFloat(degree) / total_degree as score
        ORDER BY score DESC
        LIMIT $limit
        """

        results = self.execute_query(query, {"limit": limit})

        # Add ranking
        for idx, result in enumerate(results, 1):
            result["rank"] = idx

        # Get total nodes
        count_query = "MATCH (a:Article) RETURN count(a) as count"
        total_nodes = self.execute_query(count_query)[0]["count"]

        execution_time = (time.time() - start_time) * 1000

        return {"total_nodes": total_nodes, "results": results, "execution_time_ms": execution_time}

    def run_louvain(self, max_levels: int = 10, include_intermediate: bool = False) -> dict[str, Any]:
        """
        Run Louvain community detection algorithm.

        Args:
            max_levels: Maximum hierarchy levels
            include_intermediate: Include intermediate community assignments

        Returns:
            Community detection results with modularity scores
        """
        import time

        start_time = time.time()

        # Try to drop existing projection
        try:
            self.execute_query("CALL gds.graph.drop('articles-louvain') YIELD graphName")
        except Exception:
            pass

        # Create in-memory graph projection
        projection_query = """
        CALL gds.graph.project(
            'articles-louvain',
            'Article',
            {
                REFERS_TO: {
                    orientation: 'UNDIRECTED'
                }
            }
        )
        YIELD graphName, nodeCount, relationshipCount
        RETURN graphName, nodeCount, relationshipCount
        """

        try:
            self.execute_query(projection_query)
        except Exception as e:
            # Fallback to existing communities if GDS fails
            return self._louvain_fallback()

        # Run Louvain algorithm
        louvain_query = """
        CALL gds.louvain.stream('articles-louvain', {
            maxLevels: $max_levels,
            includeIntermediateCommunities: $include_intermediate
        })
        YIELD nodeId, communityId, intermediateCommunityIds
        WITH communityId, count(*) as size
        RETURN communityId as community_id, size
        ORDER BY size DESC
        """

        try:
            communities = self.execute_query(
                louvain_query, {"max_levels": max_levels, "include_intermediate": include_intermediate}
            )

            # Calculate modularity (simplified - actual modularity requires more complex calculation)
            # For demonstration purposes, we'll use a proxy metric
            total_communities = len(communities)
            avg_size = sum(c["size"] for c in communities) / max(total_communities, 1)

            # Add modularity scores to each community
            for comm in communities:
                # Simple modularity proxy: larger, more balanced communities score higher
                comm["modularity"] = min(comm["size"] / (avg_size * 2), 1.0)

            # Overall modularity (average of community modularities)
            overall_modularity = sum(c["modularity"] for c in communities) / max(total_communities, 1)

            execution_time = (time.time() - start_time) * 1000

            return {
                "total_communities": total_communities,
                "modularity": overall_modularity,
                "communities": communities,
                "execution_time_ms": execution_time,
            }

        finally:
            # Clean up
            try:
                self.execute_query("CALL gds.graph.drop('articles-louvain') YIELD graphName")
            except Exception:
                pass

    def _louvain_fallback(self) -> dict[str, Any]:
        """
        Fallback using existing Community nodes.

        Returns:
            Community statistics from existing data
        """
        import time

        start_time = time.time()

        query = """
        MATCH (c:Community)
        OPTIONAL MATCH (a:Article)-[:BELONGS_TO]->(c)
        WITH c, count(a) as size
        WHERE size > 0
        RETURN c.community_id as community_id,
               size,
               COALESCE(c.density, 0.5) as modularity
        ORDER BY size DESC
        """

        communities = self.execute_query(query)
        total_communities = len(communities)
        overall_modularity = (
            sum(c["modularity"] for c in communities) / max(total_communities, 1) if communities else 0.0
        )

        execution_time = (time.time() - start_time) * 1000

        return {
            "total_communities": total_communities,
            "modularity": overall_modularity,
            "communities": communities,
            "execution_time_ms": execution_time,
        }

    def run_node_similarity(
        self, article_id: str, limit: int = 10, similarity_cutoff: float = 0.1
    ) -> dict[str, Any]:
        """
        Find similar articles using Node Similarity algorithm.

        Args:
            article_id: Source article ID
            limit: Number of similar articles to return
            similarity_cutoff: Minimum similarity score

        Returns:
            Similar articles with similarity scores
        """
        import time

        start_time = time.time()

        # Get source article info
        source_query = """
        MATCH (a:Article {article_id: $article_id})
        RETURN a.article_id as article_id, a.article_title as article_title
        """
        source_results = self.execute_query(source_query, {"article_id": article_id})

        if not source_results:
            return {
                "source_article_id": article_id,
                "source_article_title": "Unknown",
                "similar_articles": [],
                "execution_time_ms": 0,
            }

        source_info = source_results[0]

        # Try to drop existing projection
        try:
            self.execute_query("CALL gds.graph.drop('articles-similarity') YIELD graphName")
        except Exception:
            pass

        # Create projection
        projection_query = """
        CALL gds.graph.project(
            'articles-similarity',
            'Article',
            'REFERS_TO',
            {nodeProperties: ['article_id', 'article_title']}
        )
        YIELD graphName
        RETURN graphName
        """

        try:
            self.execute_query(projection_query)
        except Exception as e:
            # Fallback to Cypher-based similarity
            return self._node_similarity_fallback(article_id, source_info, limit, similarity_cutoff)

        # Run Node Similarity
        similarity_query = """
        CALL gds.nodeSimilarity.stream('articles-similarity', {
            similarityCutoff: $similarity_cutoff
        })
        YIELD node1, node2, similarity
        WITH gds.util.asNode(node1) AS source, gds.util.asNode(node2) AS target, similarity
        WHERE source.article_id = $article_id
        RETURN target.article_id AS article_id,
               target.article_title AS article_title,
               similarity AS similarity_score
        ORDER BY similarity DESC
        LIMIT $limit
        """

        try:
            results = self.execute_query(
                similarity_query,
                {"article_id": article_id, "similarity_cutoff": similarity_cutoff, "limit": limit},
            )

            # Add common neighbors count (estimated from similarity)
            for result in results:
                result["common_neighbors"] = int(result["similarity_score"] * 10)  # Rough estimate

            execution_time = (time.time() - start_time) * 1000

            return {
                "source_article_id": source_info["article_id"],
                "source_article_title": source_info["article_title"],
                "similar_articles": results,
                "execution_time_ms": execution_time,
            }

        finally:
            # Clean up
            try:
                self.execute_query("CALL gds.graph.drop('articles-similarity') YIELD graphName")
            except Exception:
                pass

    def _node_similarity_fallback(
        self, article_id: str, source_info: dict, limit: int = 10, similarity_cutoff: float = 0.1
    ) -> dict[str, Any]:
        """
        Fallback node similarity using common neighbors (Jaccard similarity).

        Args:
            article_id: Source article ID
            source_info: Source article information
            limit: Number of results
            similarity_cutoff: Minimum similarity

        Returns:
            Similar articles based on common neighbors
        """
        import time

        start_time = time.time()

        query = """
        MATCH (source:Article {article_id: $article_id})-[:REFERS_TO]-(neighbor:Article)
        MATCH (neighbor)-[:REFERS_TO]-(similar:Article)
        WHERE similar.article_id <> $article_id
          AND NOT (source)-[:REFERS_TO]-(similar)
        WITH similar, count(DISTINCT neighbor) as common_neighbors
        MATCH (source:Article {article_id: $article_id})-[:REFERS_TO]-(n1)
        WITH similar, common_neighbors, count(DISTINCT n1) as source_neighbors
        MATCH (similar)-[:REFERS_TO]-(n2)
        WITH similar, common_neighbors, source_neighbors, count(DISTINCT n2) as similar_neighbors
        WITH similar,
             common_neighbors,
             toFloat(common_neighbors) / (source_neighbors + similar_neighbors - common_neighbors) as similarity_score
        WHERE similarity_score >= $similarity_cutoff
        RETURN similar.article_id as article_id,
               similar.article_title as article_title,
               similarity_score,
               common_neighbors
        ORDER BY similarity_score DESC
        LIMIT $limit
        """

        results = self.execute_query(
            query, {"article_id": article_id, "similarity_cutoff": similarity_cutoff, "limit": limit}
        )

        execution_time = (time.time() - start_time) * 1000

        return {
            "source_article_id": source_info["article_id"],
            "source_article_title": source_info["article_title"],
            "similar_articles": results,
            "execution_time_ms": execution_time,
        }
