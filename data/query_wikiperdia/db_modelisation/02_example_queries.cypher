// ============================================================================
// STEP 5: VERIFICATION
// ============================================================================

// Count all nodes
MATCH (n:Topic) RETURN 'Topic' as Type, count(n) as Count
UNION
MATCH (n:Article) RETURN 'Article' as Type, count(n) as Count
UNION
MATCH (n:Tag) RETURN 'Tag' as Type, count(n) as Count
UNION
MATCH (n:Author) RETURN 'Author' as Type, count(n) as Count
ORDER BY Type;

// Count all relationships
MATCH ()-[r:SUBCLASS_OF]->() RETURN 'SUBCLASS_OF' as RelType, count(r) as Count
UNION
MATCH ()-[r:RELATED_TO]->() RETURN 'RELATED_TO' as RelType, count(r) as Count
UNION
MATCH ()-[r:ABOUT]->() RETURN 'ABOUT' as RelType, count(r) as Count
UNION
MATCH ()-[r:LINKS_TO]->() RETURN '🆕 LINKS_TO' as RelType, count(r) as Count
UNION
MATCH ()-[r:TAGGED_WITH]->() RETURN 'TAGGED_WITH' as RelType, count(r) as Count
UNION
MATCH ()-[r:CONTRIBUTED_TO]->() RETURN 'CONTRIBUTED_TO' as RelType, count(r) as Count
ORDER BY Count DESC;

// Check data quality
MATCH (t:Topic)
WHERE t.topic_name IS NULL OR t.topic_name = ''
RETURN 'Topics without names' as Issue, count(t) as Count;

// ============================================================================
// STEP 6: EXAMPLE QUERIES WITH ARTICLE LINKS
// ============================================================================

// 1. Find directly linked articles
MATCH (a1:Article)-[r:LINKS_TO]->(a2:Article)
RETURN a1.article_title, r.link_type, a2.article_title
LIMIT 20;

// 2. Most linked articles (incoming links)
MATCH (a:Article)<-[r:LINKS_TO]-()
RETURN a.article_title, count(r) as incoming_links
ORDER BY incoming_links DESC
LIMIT 10;

// 3. Articles with most outgoing links
MATCH (a:Article)-[r:LINKS_TO]->()
RETURN a.article_title, count(r) as outgoing_links
ORDER BY outgoing_links DESC
LIMIT 10;

// 4. Related articles (1-hop away)
MATCH (a1:Article {article_id: 'A000001'})-[:LINKS_TO]->(a2:Article)
RETURN a1.article_title as Source, a2.article_title as Related
LIMIT 10;

// 5. Related articles (2-hops away - "friends of friends")
MATCH (a1:Article {article_id: 'A000001'})-[:LINKS_TO*1..2]->(a2:Article)
WHERE a1 <> a2
RETURN DISTINCT a2.article_title as SuggestedArticle
LIMIT 10;

// 6. Link types distribution
MATCH ()-[r:LINKS_TO]->()
RETURN r.link_type, count(*) as count
ORDER BY count DESC;

// 7. Visualize article network (small sample)
MATCH path = (a1:Article)-[:LINKS_TO]->(a2:Article)
RETURN path
LIMIT 50;

// 8. Find articles linked both ways (mutual links)
MATCH (a1:Article)-[:LINKS_TO]->(a2:Article)
MATCH (a2)-[:LINKS_TO]->(a1)
RETURN a1.article_title, a2.article_title
LIMIT 10;

// 9. Articles with no incoming links (potential entry points)
MATCH (a:Article)
WHERE NOT (a)<-[:LINKS_TO]-()
RETURN a.article_title
LIMIT 10;

// 10. Articles with no outgoing links (potential dead-ends)
MATCH (a:Article)
WHERE NOT (a)-[:LINKS_TO]->()
RETURN a.article_title
LIMIT 10;

// ============================================================================
// STEP 7: COMPREHENSIVE QUERIES (Topics + Articles)
// ============================================================================

// 1. Full path: Article -> Topic -> Parent Topic -> Related Article
MATCH path = (a1:Article)-[:ABOUT]->(t1:Topic)-[:SUBCLASS_OF]->(parent:Topic)
             <-[:SUBCLASS_OF]-(t2:Topic)<-[:ABOUT]-(a2:Article)
WHERE a1 <> a2
RETURN path
LIMIT 25;

// 2. Compare: Direct links vs. Topic-based links
// Direct links
MATCH (a1:Article {article_id: 'A000001'})-[:LINKS_TO]->(a2:Article)
WITH collect(a2.article_title) as direct_links

// Topic-based links
MATCH (a1:Article {article_id: 'A000001'})-[:ABOUT]->(:Topic)-[:SUBCLASS_OF]->(:Topic)
      <-[:SUBCLASS_OF]-(:Topic)<-[:ABOUT]-(a3:Article)
WHERE a1 <> a3
WITH direct_links, collect(DISTINCT a3.article_title) as topic_links

RETURN 
  size(direct_links) as DirectLinks,
  size(topic_links) as TopicLinks,
  direct_links[0..5] as SampleDirectLinks,
  topic_links[0..5] as SampleTopicLinks;

// 3. Shortest path between two articles
MATCH path = shortestPath(
  (a1:Article {article_id: 'A000001'})-[*]-(a2:Article {article_id: 'A000010'})
)
RETURN path;

// 4. Article network centrality (how connected is each article?)
MATCH (a:Article)
OPTIONAL MATCH (a)-[out:LINKS_TO]->()
OPTIONAL MATCH (a)<-[in:LINKS_TO]-()
RETURN 
  a.article_title,
  count(DISTINCT out) as outgoing,
  count(DISTINCT in) as incoming,
  count(DISTINCT out) + count(DISTINCT in) as total_connections
ORDER BY total_connections DESC
LIMIT 20;

// ============================================================================
// STEP 8: API-READY PARAMETERIZED QUERIES
// ============================================================================

// API 1: Get article and its direct links
// GET /api/articles/{article_id}/links
MATCH (a:Article {article_id: $article_id})
OPTIONAL MATCH (a)-[r:LINKS_TO]->(linked:Article)
RETURN 
  a.article_id,
  a.article_title,
  a.article_url,
  collect({
    article_id: linked.article_id,
    article_title: linked.article_title,
    link_type: r.link_type
  }) as linked_articles;
// Test: :param article_id => 'A000001'

// API 2: Recommend related articles (hybrid: direct + topic-based)
// GET /api/articles/{article_id}/recommendations
MATCH (a:Article {article_id: $article_id})

// Get direct links
OPTIONAL MATCH (a)-[direct:LINKS_TO]->(d:Article)
WITH a, collect({article: d, score: 10, reason: 'direct_link'}) as direct_recs

// Get topic-based links
OPTIONAL MATCH (a)-[:ABOUT]->(:Topic)-[:SUBCLASS_OF]->(:Topic)<-[:SUBCLASS_OF]-(:Topic)<-[:ABOUT]-(t:Article)
WHERE a <> t
WITH a, direct_recs, collect({article: t, score: 5, reason: 'shared_parent'}) as topic_recs

// Combine and deduplicate
WITH a, direct_recs + topic_recs as all_recs
UNWIND all_recs as rec
WITH rec.article as article, sum(rec.score) as total_score, collect(rec.reason) as reasons
WHERE article IS NOT NULL
RETURN 
  article.article_id,
  article.article_title,
  article.article_url,
  total_score as relevance_score,
  reasons
ORDER BY total_score DESC
LIMIT 10;
// Test: :param article_id => 'A000001'

// API 3: Search articles with link context
// GET /api/search?q={query}
MATCH (a:Article)
WHERE toLower(a.article_title) CONTAINS toLower($query)
OPTIONAL MATCH (a)-[:LINKS_TO]->(linked:Article)
OPTIONAL MATCH (a)-[:ABOUT]->(t:Topic)
RETURN 
  a.article_id,
  a.article_title,
  a.article_url,
  t.topic_name,
  count(DISTINCT linked) as outgoing_links
LIMIT 20;
// Test: :param query => 'organization'

// API 4: Article network around a specific article
// GET /api/articles/{article_id}/network?depth=2
MATCH path = (a:Article {article_id: $article_id})-[:LINKS_TO*1..2]-(other:Article)
RETURN DISTINCT 
  other.article_id,
  other.article_title,
  length(path) as distance
ORDER BY distance
LIMIT 50;
// Test: :param article_id => 'A000001'

// ============================================================================
// STEP 9: STATISTICS AND ANALYTICS
// ============================================================================

// Network statistics
MATCH (a:Article)
OPTIONAL MATCH (a)-[out:LINKS_TO]->()
OPTIONAL MATCH (a)<-[in:LINKS_TO]-()
WITH 
  count(DISTINCT a) as total_articles,
  sum(CASE WHEN out IS NOT NULL THEN 1 ELSE 0 END) as total_outgoing,
  sum(CASE WHEN in IS NOT NULL THEN 1 ELSE 0 END) as total_incoming,
  avg(count(DISTINCT out)) as avg_outgoing,
  avg(count(DISTINCT in)) as avg_incoming
RETURN 
  total_articles,
  total_outgoing,
  total_incoming,
  round(avg_outgoing, 2) as avg_links_out,
  round(avg_incoming, 2) as avg_links_in;

