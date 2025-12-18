
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

// Create indexes
CREATE INDEX topic_name IF NOT EXISTS FOR (t:Topic) ON (t.topic_name);
CREATE INDEX article_title IF NOT EXISTS FOR (a:Article) ON (a.article_title);
CREATE INDEX tag_name IF NOT EXISTS FOR (t:Tag) ON (t.tag_name);
CREATE INDEX author_name IF NOT EXISTS FOR (a:Author) ON (a.author_name);

// ============================================================================
// STEP 2: LOAD MAIN ENTITIES
// ============================================================================

// Load TOPICS
// FIX: concept_name is EMPTY in CSV, use concept_description as name
LOAD CSV WITH HEADERS FROM 'file:///topics.csv' AS row
MERGE (t:Topic {topic_id: row.concept_id})
SET 
  t.topic_name = COALESCE(NULLIF(trim(row.concept_name), ''), row.concept_description, 'Unknown Topic'),
  t.topic_description = row.concept_description,
  t.source = 'main_csv';

// Verify topics loaded
MATCH (t:Topic)
RETURN 'Topics loaded' as status, count(t) as count;

// Load ARTICLES
LOAD CSV WITH HEADERS FROM 'file:///articles.csv' AS row
MERGE (a:Article {article_id: row.article_id})
SET 
  a.article_url = row.article_url,
  a.article_title = row.article_title;

// Verify articles loaded
MATCH (a:Article)
RETURN 'Articles loaded' as status, count(a) as count;

// Load TAGS
LOAD CSV WITH HEADERS FROM 'file:///tags.csv' AS row
MERGE (t:Tag {tag_id: row.category_id})
SET t.tag_name = row.category_name;

// Verify tags loaded
MATCH (t:Tag)
RETURN 'Tags loaded' as status, count(t) as count;

// Load AUTHORS
LOAD CSV WITH HEADERS FROM 'file:///authors.csv' AS row
MERGE (a:Author {author_id: row.author_id})
SET 
  a.author_name = row.author_name,
  a.email = row.email;

// Verify authors loaded
MATCH (a:Author)
RETURN 'Authors loaded' as status, count(a) as count;

// ============================================================================
// STEP 3: CREATE MISSING PARENT TOPICS (CRITICAL FIX!)
// ============================================================================
// Many parent topics in topic_hierarchy.csv don't exist in topics.csv
// We create stub nodes for them so relationships don't fail

LOAD CSV WITH HEADERS FROM 'file:///topic_hierarchy.csv' AS row
WITH DISTINCT row.parent_topic_id as parent_id
WHERE parent_id IS NOT NULL
MERGE (p:Topic {topic_id: parent_id})
ON CREATE SET 
  p.topic_name = 'Parent Topic: ' + parent_id,
  p.topic_description = 'Auto-created parent node',
  p.source = 'auto_created';

// Check how many stub parents were created
MATCH (t:Topic)
WHERE t.source = 'auto_created'
RETURN 'Stub parent topics created' as status, count(t) as count;

// ============================================================================
// STEP 4: LOAD RELATIONSHIPS
// ============================================================================

// Load TOPIC HIERARCHY (SUBCLASS_OF)
LOAD CSV WITH HEADERS FROM 'file:///topic_hierarchy.csv' AS row
MATCH (child:Topic {topic_id: row.child_topic_id})
MATCH (parent:Topic {topic_id: row.parent_topic_id})
MERGE (child)-[:SUBCLASS_OF]->(parent);

// Verify topic hierarchy
MATCH ()-[r:SUBCLASS_OF]->()
RETURN 'SUBCLASS_OF relationships' as status, count(r) as count;

// Load RELATED TOPICS (RELATED_TO)
LOAD CSV WITH HEADERS FROM 'file:///related_topics.csv' AS row
MATCH (t1:Topic {topic_id: row.topic_id})
MATCH (t2:Topic {topic_id: row.related_topic_id})
MERGE (t1)-[r:RELATED_TO]->(t2)
SET r.relation_type = row.relation_type;

// Verify related topics
MATCH ()-[r:RELATED_TO]->()
RETURN 'RELATED_TO relationships' as status, count(r) as count;

// Load ARTICLE-TOPIC (ABOUT)
LOAD CSV WITH HEADERS FROM 'file:///article_topics.csv' AS row
MATCH (a:Article {article_id: row.article_id})
MATCH (t:Topic {topic_id: row.topic_id})
MERGE (a)-[:ABOUT]->(t);

// Verify article-topic relationships
MATCH ()-[r:ABOUT]->()
RETURN 'ABOUT relationships' as status, count(r) as count;

// Load TOPIC-TAG (TAGGED_WITH)
LOAD CSV WITH HEADERS FROM 'file:///topic_tags.csv' AS row
MATCH (t:Topic {topic_id: row.topic_id})
MATCH (tag:Tag {tag_id: row.tag_id})
MERGE (t)-[:TAGGED_WITH]->(tag);

// Verify topic-tag relationships
MATCH ()-[r:TAGGED_WITH]->()
RETURN 'TAGGED_WITH relationships' as status, count(r) as count;

// Load AUTHOR-ARTICLE (CONTRIBUTED_TO)
LOAD CSV WITH HEADERS FROM 'file:///article_authors.csv' AS row
MATCH (auth:Author {author_id: row.author_id})
MATCH (a:Article {article_id: row.article_id})
MERGE (auth)-[:CONTRIBUTED_TO]->(a);

// Verify author-article relationships
MATCH ()-[r:CONTRIBUTED_TO]->()
RETURN 'CONTRIBUTED_TO relationships' as status, count(r) as count;
