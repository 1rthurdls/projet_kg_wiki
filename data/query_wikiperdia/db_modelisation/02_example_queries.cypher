
// Count all nodes (FIXED - uses UNION)
MATCH (n:Topic) 
RETURN 'Topic' as NodeType, count(n) as Count
UNION
MATCH (n:Article) 
RETURN 'Article' as NodeType, count(n) as Count
UNION
MATCH (n:Tag) 
RETURN 'Tag' as NodeType, count(n) as Count
UNION
MATCH (n:Author) 
RETURN 'Author' as NodeType, count(n) as Count
ORDER BY NodeType;

// Count all relationships (FIXED - uses UNION)
MATCH ()-[r:SUBCLASS_OF]->() 
RETURN 'SUBCLASS_OF' as RelType, count(r) as Count
UNION
MATCH ()-[r:RELATED_TO]->() 
RETURN 'RELATED_TO' as RelType, count(r) as Count
UNION
MATCH ()-[r:ABOUT]->() 
RETURN 'ABOUT' as RelType, count(r) as Count
UNION
MATCH ()-[r:TAGGED_WITH]->() 
RETURN 'TAGGED_WITH' as RelType, count(r) as Count
UNION
MATCH ()-[r:CONTRIBUTED_TO]->() 
RETURN 'CONTRIBUTED_TO' as RelType, count(r) as Count
ORDER BY RelType;

// Check data sources
MATCH (t:Topic)
RETURN t.source as Source, count(t) as Count
ORDER BY Count DESC;

// Check for topics without names (should be 0)
MATCH (t:Topic)
WHERE t.topic_name IS NULL OR t.topic_name = ''
RETURN 'Topics without names' as Issue, count(t) as Count;

// Sample the loaded data
MATCH (t:Topic)
WHERE t.source = 'main_csv'
RETURN t.topic_id, t.topic_name, t.topic_description
LIMIT 10;

// test QUERIES

// 1. Topics with most articles (NOW WORKS!)
MATCH (t:Topic)<-[:ABOUT]-(a:Article)
RETURN t.topic_name, t.topic_id, count(a) as article_count
ORDER BY article_count DESC
LIMIT 10;

// 2. Find root topics (most common parents)
MATCH (child:Topic)-[:SUBCLASS_OF]->(parent:Topic)
WITH parent, count(child) as children
WHERE children > 5
RETURN parent.topic_name, parent.topic_id, children, parent.source
ORDER BY children DESC
LIMIT 10;

// 3. Find deeply nested hierarchies
MATCH path = (t:Topic)-[:SUBCLASS_OF*1..3]->(parent:Topic)
WHERE t.source = 'main_csv' AND parent.source = 'auto_created'
RETURN t.topic_name, parent.topic_name, parent.topic_id, length(path) as depth
ORDER BY depth DESC
LIMIT 10;

// 4. Articles by tag
MATCH (tag:Tag)<-[:TAGGED_WITH]-(t:Topic)<-[:ABOUT]-(a:Article)
RETURN tag.tag_name, count(DISTINCT a) as article_count
ORDER BY article_count DESC
LIMIT 10;

// 5. Author contributions
MATCH (auth:Author)-[:CONTRIBUTED_TO]->(a:Article)
RETURN auth.author_name, count(a) as articles
ORDER BY articles DESC;

// 6. Find related articles through relationships
MATCH (a1:Article)-[:ABOUT]->(t1:Topic)-[:RELATED_TO]-(t2:Topic)<-[:ABOUT]-(a2:Article)
WHERE a1 <> a2
RETURN a1.article_title, a2.article_title, t1.topic_name, t2.topic_name
LIMIT 10;

// visualisation QUERIES

// Small sample of the full graph
MATCH (a:Article)-[:ABOUT]->(t:Topic)-[:SUBCLASS_OF]->(parent:Topic)
WHERE t.source = 'main_csv'
RETURN a, t, parent
LIMIT 25;

// Show the hierarchy from a root
MATCH path = (t:Topic)-[:SUBCLASS_OF*1..2]->(root:Topic {topic_id: 'Q43229'})
RETURN path
LIMIT 20;
