// 1. Contraintes
CREATE CONSTRAINT constraint_article_id FOR (a:Article) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT constraint_community_id FOR (c:Community) REQUIRE c.id IS UNIQUE;

// 2. Index
CREATE INDEX index_article_community FOR (a:Article) ON (a.community_id);
CREATE INDEX index_article_traffic FOR (a:Article) ON (a.monthly_traffic);
CREATE INDEX index_article_composite FOR (a:Article) ON (a.community_id, a.monthly_traffic);

// 3. Charger Communities
LOAD CSV WITH HEADERS FROM 'file:///communities.csv' AS row
CREATE (:Community {
  id: toInteger(row.`id:ID(Community)`),
  size: toInteger(row.`size:int`),
  level: row.level,
  density: toFloat(row.`density:float`),
  avg_degree: toFloat(row.`avg_degree:float`),
  avg_traffic: toFloat(row.`avg_traffic:float`),
  median_traffic: toFloat(row.`median_traffic:float`)
});

// 4. Charger Articles
LOAD CSV WITH HEADERS FROM 'file:///articles.csv' AS row
CREATE (:Article {
  id: row.`id:ID`,
  monthly_traffic: toInteger(row.`monthly_traffic:int`),
  community_id: toInteger(row.`community_id:int`)
});

// 5. Créer BELONGS_TO
MATCH (a:Article)
MATCH (c:Community {id: a.community_id})
CREATE (a)-[:BELONGS_TO]->(c);

// 6. Créer LINKS_TO
:auto LOAD CSV WITH HEADERS FROM 'file:///edges.csv' AS row
CALL {
  WITH row
  MATCH (a1:Article {id: row.`:START_ID`})
  MATCH (a2:Article {id: row.`:END_ID`})
  CREATE (a1)-[:LINKS_TO]->(a2)
} IN TRANSACTIONS OF 1000 ROWS;