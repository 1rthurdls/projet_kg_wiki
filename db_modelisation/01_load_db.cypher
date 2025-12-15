// =====================================================
// Neo4j load script for Wikipedia Article Networks (Chameleon)
// Files expected in Neo4j /import folder:
//   - communities.csv  (community_id,size,level,density,avg_degree,avg_traffic,median_traffic)
//   - article.csv      (id,target,community_id)
//   - edges.csv        (id1,id2)
// =====================================================

// (OPTIONAL) RESET DATA ONLY (keeps indexes/constraints)
// Uncomment if you want to wipe nodes+rels before reloading
// MATCH (n) DETACH DELETE n;

// 1) Constraints (safe re-run)
CREATE CONSTRAINT article_id_unique IF NOT EXISTS
FOR (a:Article) REQUIRE a.id IS UNIQUE;

CREATE CONSTRAINT community_id_unique IF NOT EXISTS
FOR (c:Community) REQUIRE c.community_id IS UNIQUE;

// 2) Helpful indexes (optional, safe re-run)
CREATE INDEX article_community_id IF NOT EXISTS
FOR (a:Article) ON (a.community_id);

CREATE INDEX article_target IF NOT EXISTS
FOR (a:Article) ON (a.target);

// 3) load communities.csv
LOAD CSV WITH HEADERS FROM 'file:///communities.csv' AS row
MERGE (c:Community {community_id: toInteger(row.community_id)})
SET
  c.size = toInteger(row.size),
  c.level = row.level,
  c.density = toFloat(row.density),
  c.avg_degree = toFloat(row.avg_degree),
  c.avg_traffic = toFloat(row.avg_traffic),
  c.median_traffic = toFloat(row.median_traffic);


// 4) Load Articles (and store target + community_id as properties)
LOAD CSV WITH HEADERS FROM 'file:///article.csv' AS row
MERGE (a:Article {id: toInteger(row.id)})
SET
  a.target       = toInteger(row.target),
  a.community_id = toInteger(row.community_id);

// 5) Create BELONGS_TO (Article -> Community)
MATCH (a:Article)
WHERE a.community_id IS NOT NULL
MATCH (c:Community {community_id: a.community_id})
MERGE (a)-[:BELONGS_TO]->(c);

// 6) Create REFERS_TO between Articles (undirected edges, de-duplicated)
// We canonicalize each pair (min,max) so we don't create duplicates.
:auto LOAD CSV WITH HEADERS FROM 'file:///edges.csv' AS row
CALL {
  WITH row
  WITH toInteger(row.id1) AS id1, toInteger(row.id2) AS id2
  WITH CASE WHEN id1 < id2 THEN id1 ELSE id2 END AS u,
       CASE WHEN id1 < id2 THEN id2 ELSE id1 END AS v
  MATCH (a1:Article {id: u})
  MATCH (a2:Article {id: v})
  MERGE (a1)-[:REFERS_TO]-(a2)
} IN TRANSACTIONS OF 10000 ROWS;


// 7) Quick checks
MATCH (a:Article) RETURN count(a) AS n_articles;
MATCH (c:Community) RETURN count(c) AS n_communities;
MATCH (:Article)-[r:BELONGS_TO]->(:Community) RETURN count(r) AS n_belongs_to;
MATCH (:Article)-[r:REFERS_TO]-(:Article) RETURN count(r) AS n_refers_to;

// 8) Visualize schema (Neo4j Browser)
CALL db.schema.visualization();
