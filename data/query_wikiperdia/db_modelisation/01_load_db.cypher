// ============================================================================
// KNOWLEDGE BASE - NEO4J COMPLETE LOAD SCRIPT
// ============================================================================
// Includes Article-to-Article Links from Wikidata!
//
// CSV Files Required:
// - topics.csv
// - articles.csv
// - article_links.csv (NEW!)
// - tags.csv
// - authors.csv  
// - topic_hierarchy.csv
// - related_topics.csv
// - article_topics.csv
// - topic_tags.csv
// - article_authors.csv
// ============================================================================

// ============================================================================
// STEP 0: CLEAN UP (Optional - run only if reloading)
// ============================================================================
// Uncomment to start fresh:
// MATCH (n) DETACH DELETE n;

// ============================================================================
// STEP 1: CREATE CONSTRAINTS
// ============================================================================

CREATE CONSTRAINT topic_id IF NOT EXISTS
FOR (t:Topic) REQUIRE t.topic_id IS UNIQUE;

CREATE CONSTRAINT article_id IF NOT EXISTS
FOR (a:Article) REQUIRE a.article_id IS UNIQUE;

CREATE CONSTRAINT tag_id IF NOT EXISTS
FOR (t:Tag) REQUIRE t.tag_id IS UNIQUE;

CREATE CONSTRAINT author_id IF NOT EXISTS
FOR (a:Author) REQUIRE a.author_id IS UNIQUE;

// Create indexes for search performance
CREATE INDEX topic_name IF NOT EXISTS FOR (t:Topic) ON (t.topic_name);
CREATE INDEX article_title IF NOT EXISTS FOR (a:Article) ON (a.article_title);
CREATE INDEX tag_name IF NOT EXISTS FOR (t:Tag) ON (t.tag_name);
CREATE INDEX author_name IF NOT EXISTS FOR (a:Author) ON (a.author_name);

// ============================================================================
// STEP 2: LOAD NODES (Entities)
// ============================================================================

// Load TOPICS
LOAD CSV WITH HEADERS FROM 'file:///topics.csv' AS row
MERGE (t:Topic {topic_id: row.concept_id})
SET 
  t.topic_name = COALESCE(NULLIF(trim(row.concept_name), ''), row.concept_description, 'Unknown Topic'),
  t.topic_description = row.concept_description,
  t.source = 'main_csv';

MATCH (t:Topic)
RETURN 'Topics loaded' as Status, count(t) as Count;

// Load ARTICLES
LOAD CSV WITH HEADERS FROM 'file:///articles.csv' AS row
MERGE (a:Article {article_id: row.article_id})
SET 
  a.article_url = row.article_url,
  a.article_title = row.article_title;

MATCH (a:Article)
RETURN 'Articles loaded' as Status, count(a) as Count;

// Load TAGS
LOAD CSV WITH HEADERS FROM 'file:///tags.csv' AS row
MERGE (t:Tag {tag_id: row.category_id})
SET t.tag_name = row.category_name;

MATCH (t:Tag)
RETURN 'Tags loaded' as Status, count(t) as Count;

// Load AUTHORS
LOAD CSV WITH HEADERS FROM 'file:///authors.csv' AS row
MERGE (a:Author {author_id: row.author_id})
SET
  a.author_name = row.author_name,
  a.total_edits = toInteger(row.total_edits);

MATCH (a:Author)
RETURN 'Authors loaded' as Status, count(a) as Count;

// ============================================================================
// STEP 3: CREATE MISSING PARENT TOPICS (Important!)
// ============================================================================

LOAD CSV WITH HEADERS FROM 'file:///topic_hierarchy.csv' AS row
WITH DISTINCT row.parent_topic_id as parent_id
WHERE parent_id IS NOT NULL
MERGE (p:Topic {topic_id: parent_id})
ON CREATE SET 
  p.topic_name = 'Parent: ' + parent_id,
  p.topic_description = 'Auto-created parent node',
  p.source = 'auto_created';

MATCH (t:Topic)
WHERE t.source = 'auto_created'
RETURN 'Stub parents created' as Status, count(t) as Count;

// ============================================================================
// STEP 4: LOAD RELATIONSHIPS
// ============================================================================

// Load TOPIC HIERARCHY (SUBCLASS_OF)
LOAD CSV WITH HEADERS FROM 'file:///topic_hierarchy.csv' AS row
MATCH (child:Topic {topic_id: row.child_topic_id})
MATCH (parent:Topic {topic_id: row.parent_topic_id})
MERGE (child)-[:SUBCLASS_OF]->(parent);

MATCH ()-[r:SUBCLASS_OF]->()
RETURN 'SUBCLASS_OF loaded' as Status, count(r) as Count;

// Load RELATED TOPICS (RELATED_TO)
LOAD CSV WITH HEADERS FROM 'file:///related_topics.csv' AS row
MATCH (t1:Topic {topic_id: row.topic_id})
MATCH (t2:Topic {topic_id: row.related_topic_id})
MERGE (t1)-[r:RELATED_TO]->(t2)
SET r.relation_type = row.relation_type;

MATCH ()-[r:RELATED_TO]->()
RETURN 'RELATED_TO loaded' as Status, count(r) as Count;

// Load ARTICLE-TOPIC (ABOUT)
LOAD CSV WITH HEADERS FROM 'file:///article_topics.csv' AS row
MATCH (a:Article {article_id: row.article_id})
MATCH (t:Topic {topic_id: row.topic_id})
MERGE (a)-[:ABOUT]->(t);

MATCH ()-[r:ABOUT]->()
RETURN 'ABOUT loaded' as Status, count(r) as Count;

// 🆕 Load ARTICLE-ARTICLE LINKS (NEW!)
LOAD CSV WITH HEADERS FROM 'file:///article_links.csv' AS row
MATCH (a1:Article {article_id: row.source_article_id})
MATCH (a2:Article {article_id: row.target_article_id})
MERGE (a1)-[r:LINKS_TO]->(a2)
SET 
  r.link_type = row.link_type,
  r.wikidata_property = row.wikidata_property;

MATCH ()-[r:LINKS_TO]->()
RETURN '🆕 LINKS_TO loaded' as Status, count(r) as Count;

// Load TOPIC-TAG (TAGGED_WITH)
LOAD CSV WITH HEADERS FROM 'file:///topic_tags.csv' AS row
MATCH (t:Topic {topic_id: row.topic_id})
MATCH (tag:Tag {tag_id: row.tag_id})
MERGE (t)-[:TAGGED_WITH]->(tag);

MATCH ()-[r:TAGGED_WITH]->()
RETURN 'TAGGED_WITH loaded' as Status, count(r) as Count;

// Load AUTHOR-ARTICLE (CONTRIBUTED_TO)
LOAD CSV WITH HEADERS FROM 'file:///article_authors.csv' AS row
MATCH (auth:Author {author_id: row.author_id})
MATCH (a:Article {article_id: row.article_id})
MERGE (auth)-[r:CONTRIBUTED_TO]->(a)
SET r.edit_count = toInteger(row.edit_count);

MATCH ()-[r:CONTRIBUTED_TO]->()
RETURN 'CONTRIBUTED_TO loaded' as Status, count(r) as Count;

