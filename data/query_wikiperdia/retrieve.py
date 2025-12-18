import time
import requests
import pandas as pd
import random

endpoint = "https://query.wikidata.org/sparql"
headers = {
    "Accept": "application/sparql-results+json",
    "User-Agent": "kg_wiki_project/1.0 (contact: you@example.com)"
}

ROOT_QID = "Q43229"  # organization

# Query 1: Main concepts + articles + hierarchy
BASE_QUERY = f"""
SELECT DISTINCT 
  ?concept ?conceptLabel ?conceptDescription
  ?article ?articleTitle 
  ?parent ?parentLabel
WHERE {{
  ?concept wdt:P279 wd:{ROOT_QID} .
  
  ?article schema:about ?concept ;
           schema:isPartOf <https://en.wikipedia.org/> ;
           schema:name ?articleTitle .
  
  OPTIONAL {{ ?concept wdt:P279 ?parent . }}
  
  SERVICE wikibase:label {{ 
    bd:serviceParam wikibase:language "en". 
    ?concept schema:description ?conceptDescription .
  }}
}}"""

def qid(url: str | None) -> str | None:
    """Extract QID from Wikidata URL"""
    return None if not url else url.rsplit("/", 1)[-1]

def val(row: dict, key: str) -> str | None:
    """Safely extract value from result row"""
    return row[key]["value"] if key in row else None

def fetch_all_data(limit: int = 100, max_results: int = 500, retries: int = 3) -> pd.DataFrame:
    """Fetch main data with pagination"""
    offset = 0
    all_rows = []
    
    while len(all_rows) < max_results:
        query = BASE_QUERY + f"\nLIMIT {limit}\nOFFSET {offset}"
        print(f"Fetching batch at offset={offset}...")
        
        for attempt in range(retries):
            try:
                r = requests.get(endpoint, params={"query": query}, headers=headers, timeout=120)
                
                if r.status_code in (429, 502, 503, 504):
                    sleep_s = 5 * (attempt + 1)
                    print(f"  Server busy (HTTP {r.status_code}). Sleeping {sleep_s}s...")
                    time.sleep(sleep_s)
                    continue
                
                r.raise_for_status()
                data = r.json()["results"]["bindings"]
                
                if not data:
                    print(f"  No more results")
                    return pd.DataFrame(all_rows)
                
                for row in data:
                    all_rows.append({
                        "concept_id": qid(val(row, "concept")),
                        "concept_name": val(row, "conceptLabel"),
                        "concept_description": val(row, "conceptDescription"),
                        "article_url": val(row, "article"),
                        "article_title": val(row, "articleTitle"),
                        "parent_id": qid(val(row, "parent")),
                        "parent_name": val(row, "parentLabel"),
                    })
                
                print(f"  ✓ Fetched {len(data)} rows (total: {len(all_rows)})")
                offset += limit
                time.sleep(2)
                break
                
            except Exception as e:
                if attempt == retries - 1:
                    print(f"  ✗ Failed: {e}")
                    return pd.DataFrame(all_rows)
                time.sleep(5 * (attempt + 1))
        
        if len(data) < limit:
            break
    
    return pd.DataFrame(all_rows)

def fetch_article_links(concept_ids: list) -> pd.DataFrame:
    """
    NOUVELLE FONCTION : Récupère les relations entre articles via Wikidata
    
    Stratégie : Si concept1 a une relation sémantique avec concept2,
    et tous deux ont des articles Wikipedia, alors créer un lien entre les articles
    """
    print("\n" + "="*70)
    print("FETCHING ARTICLE-TO-ARTICLE LINKS FROM WIKIDATA")
    print("="*70)
    
    if len(concept_ids) > 50:
        concept_ids = concept_ids[:50]
    
    values_str = " ".join([f"wd:{cid}" for cid in concept_ids])
    
    # Query pour trouver toutes les relations sémantiques entre concepts
    query = f"""
    SELECT DISTINCT ?concept1 ?article1 ?article1Title
                    ?concept2 ?article2 ?article2Title
                    ?property ?propertyLabel
    WHERE {{
      VALUES ?concept1 {{ {values_str} }}
      
      # Relations sémantiques importantes
      ?concept1 ?property ?concept2 .
      
      # Filtrer sur les propriétés pertinentes
      FILTER(?property IN (
        wdt:P361,   # part of
        wdt:P527,   # has part
        wdt:P1269,  # facet of
        wdt:P279,   # subclass of (redondant avec hierarchy mais utile)
        wdt:P366,   # use
        wdt:P460,   # said to be the same as
        wdt:P1659,  # see also
        wdt:P138,   # named after
        wdt:P2354   # has list
      ))
      
      # Les deux concepts doivent avoir des articles Wikipedia EN
      ?article1 schema:about ?concept1 ;
                schema:isPartOf <https://en.wikipedia.org/> ;
                schema:name ?article1Title .
      
      ?article2 schema:about ?concept2 ;
                schema:isPartOf <https://en.wikipedia.org/> ;
                schema:name ?article2Title .
      
      # Labels pour les propriétés
      SERVICE wikibase:label {{ 
        bd:serviceParam wikibase:language "en". 
        ?property rdfs:label ?propertyLabel .
      }}
    }}
    LIMIT 500
    """
    
    try:
        print("Querying Wikidata for semantic links between articles...")
        r = requests.get(endpoint, params={"query": query}, headers=headers, timeout=180)
        r.raise_for_status()
        data = r.json()["results"]["bindings"]
        
        rows = []
        for row in data:
            rows.append({
                "source_concept_id": qid(val(row, "concept1")),
                "source_article_url": val(row, "article1"),
                "source_article_title": val(row, "article1Title"),
                "target_concept_id": qid(val(row, "concept2")),
                "target_article_url": val(row, "article2"),
                "target_article_title": val(row, "article2Title"),
                "relation_property": val(row, "property").split("/")[-1] if val(row, "property") else None,
                "relation_label": val(row, "propertyLabel")
            })
        
        print(f"  ✓ Fetched {len(rows)} article-to-article semantic links!")
        return pd.DataFrame(rows)
    
    except Exception as e:
        print(f"  ✗ Failed to fetch article links: {e}")
        return pd.DataFrame()

def fetch_related_concepts(concept_ids: list) -> pd.DataFrame:
    """Fetch related concepts (part_of, has_part)"""
    print("\nFetching related concepts...")
    
    if len(concept_ids) > 50:
        concept_ids = concept_ids[:50]
    
    values_str = " ".join([f"wd:{cid}" for cid in concept_ids])
    
    query = f"""
    SELECT DISTINCT ?concept ?related ?relatedLabel
    WHERE {{
      VALUES ?concept {{ {values_str} }}
      {{
        ?concept wdt:P361 ?related .
      }} UNION {{
        ?concept wdt:P527 ?related .
      }}
      ?relatedArticle schema:about ?related ;
                      schema:isPartOf <https://en.wikipedia.org/> .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 200
    """
    
    try:
        r = requests.get(endpoint, params={"query": query}, headers=headers, timeout=120)
        r.raise_for_status()
        data = r.json()["results"]["bindings"]
        
        rows = []
        for row in data:
            rows.append({
                "concept_id": qid(val(row, "concept")),
                "related_id": qid(val(row, "related")),
                "related_name": val(row, "relatedLabel"),
                "relation_type": "related"
            })
        
        print(f"  ✓ Fetched {len(rows)} relationships")
        return pd.DataFrame(rows)
    
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return pd.DataFrame()

def fetch_categories(concept_ids: list) -> pd.DataFrame:
    """Fetch categories/tags"""
    print("\nFetching categories/tags...")
    
    if len(concept_ids) > 50:
        concept_ids = concept_ids[:50]
    
    values_str = " ".join([f"wd:{cid}" for cid in concept_ids])
    
    query = f"""
    SELECT DISTINCT ?concept ?category ?categoryLabel
    WHERE {{
      VALUES ?concept {{ {values_str} }}
      ?concept wdt:P31 ?category .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 200
    """
    
    try:
        r = requests.get(endpoint, params={"query": query}, headers=headers, timeout=120)
        r.raise_for_status()
        data = r.json()["results"]["bindings"]
        
        rows = []
        for row in data:
            cat_id = qid(val(row, "category"))
            if cat_id != ROOT_QID:
                rows.append({
                    "concept_id": qid(val(row, "concept")),
                    "category_id": cat_id,
                    "category_name": val(row, "categoryLabel"),
                })
        
        print(f"  ✓ Fetched {len(rows)} category relationships")
        return pd.DataFrame(rows)
    
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return pd.DataFrame()

def main():
    print("="*70)
    print("KNOWLEDGE BASE DATA EXTRACTION WITH ARTICLE LINKS")
    print("="*70)
    print(f"Root concept: {ROOT_QID} (organization)")
    print("Estimated time: 3-5 minutes\n")
    
    # ===== STEP 1: Fetch main data =====
    main_df = fetch_all_data(limit=100, max_results=500)
    
    if main_df.empty:
        print("\n✗ No data retrieved!")
        return
    
    print(f"\n✓ Total rows: {len(main_df)}")
    concept_ids = main_df["concept_id"].dropna().unique().tolist()
    print(f"✓ Unique concepts: {len(concept_ids)}")
    
    # ===== STEP 2: Fetch article links (NOUVEAU!) =====
    article_links_raw = fetch_article_links(concept_ids)
    
    # ===== STEP 3: Fetch related concepts =====
    related_df = fetch_related_concepts(concept_ids)
    
    # ===== STEP 4: Fetch categories =====
    categories_df = fetch_categories(concept_ids)
    
    print("\n" + "="*70)
    print("PROCESSING AND EXPORTING DATA")
    print("="*70)
    
    # ===== Export 1: TOPICS =====
    topics = (main_df[["concept_id", "concept_name", "concept_description"]]
              .dropna(subset=["concept_id"])
              .drop_duplicates(subset=["concept_id"]))
    
    # ===== Export 2: ARTICLES =====
    articles = (main_df[["article_url", "article_title", "concept_id"]]
                .dropna(subset=["article_url"])
                .drop_duplicates(subset=["article_url"])
                .reset_index(drop=True))
    articles.insert(0, "article_id", ["A" + str(i).zfill(6) for i in range(len(articles))])
    
    # ===== Export 3: ARTICLE LINKS (NOUVEAU!) =====
    if not article_links_raw.empty:
        # Map URLs to article IDs
        url_to_id = dict(zip(articles['article_url'], articles['article_id']))
        
        article_links = []
        for _, row in article_links_raw.iterrows():
            source_url = row['source_article_url']
            target_url = row['target_article_url']
            
            # Only keep links between articles we have
            if source_url in url_to_id and target_url in url_to_id:
                article_links.append({
                    'source_article_id': url_to_id[source_url],
                    'target_article_id': url_to_id[target_url],
                    'link_type': row['relation_label'],
                    'wikidata_property': row['relation_property']
                })
        
        article_links_df = pd.DataFrame(article_links).drop_duplicates(
            subset=['source_article_id', 'target_article_id']
        )
    else:
        article_links_df = pd.DataFrame(columns=['source_article_id', 'target_article_id', 'link_type', 'wikidata_property'])
    
    # ===== Export 4: TAGS =====
    if not categories_df.empty:
        tags = (categories_df[["category_id", "category_name"]]
                .dropna(subset=["category_id"])
                .drop_duplicates(subset=["category_id"]))
    else:
        tags = pd.DataFrame(columns=["category_id", "category_name"])
    
    # ===== Export 5: TOPIC_HIERARCHY =====
    topic_hierarchy = (main_df[["concept_id", "parent_id"]]
                       .dropna()
                       .drop_duplicates()
                       .rename(columns={"concept_id": "child_topic_id", "parent_id": "parent_topic_id"}))
    
    # ===== Export 6: RELATED_TOPICS =====
    if not related_df.empty:
        related_topics = (related_df[["concept_id", "related_id", "relation_type"]]
                          .dropna(subset=["related_id"])
                          .drop_duplicates()
                          .rename(columns={"concept_id": "topic_id", "related_id": "related_topic_id"}))
    else:
        related_topics = pd.DataFrame(columns=["topic_id", "related_topic_id", "relation_type"])
    
    # ===== Export 7: ARTICLE_TOPICS =====
    article_topics = (articles[["article_id", "concept_id"]]
                      .dropna()
                      .rename(columns={"concept_id": "topic_id"}))
    
    # ===== Export 8: TOPIC_TAGS =====
    if not categories_df.empty:
        topic_tags = (categories_df[["concept_id", "category_id"]]
                      .dropna()
                      .drop_duplicates()
                      .rename(columns={"concept_id": "topic_id", "category_id": "tag_id"}))
    else:
        topic_tags = pd.DataFrame(columns=["topic_id", "tag_id"])
    
    # ===== Export 9: AUTHORS =====
    authors = pd.DataFrame({
        "author_id": ["AUTH001", "AUTH002", "AUTH003"],
        "author_name": ["Wikipedia Contributors", "Community Editors", "Domain Experts"],
        "email": ["contributors@wikipedia.org", "editors@wikipedia.org", "experts@wikipedia.org"]
    })
    
    # ===== Export 10: ARTICLE_AUTHORS =====
    article_authors = pd.DataFrame({
        "article_id": articles["article_id"].tolist()[:min(50, len(articles))],
        "author_id": [random.choice(authors["author_id"].tolist()) for _ in range(min(50, len(articles)))]
    })
    
    # ===== SAVE ALL CSVs =====
    topics.to_csv("topics.csv", index=False, encoding="utf-8")
    articles.to_csv("articles.csv", index=False, encoding="utf-8")
    article_links_df.to_csv("article_links.csv", index=False, encoding="utf-8")  # NOUVEAU!
    tags.to_csv("tags.csv", index=False, encoding="utf-8")
    topic_hierarchy.to_csv("topic_hierarchy.csv", index=False, encoding="utf-8")
    related_topics.to_csv("related_topics.csv", index=False, encoding="utf-8")
    article_topics.to_csv("article_topics.csv", index=False, encoding="utf-8")
    topic_tags.to_csv("topic_tags.csv", index=False, encoding="utf-8")
    authors.to_csv("authors.csv", index=False, encoding="utf-8")
    article_authors.to_csv("article_authors.csv", index=False, encoding="utf-8")
    
    # ===== FINAL REPORT =====
    print("\n" + "="*70)
    print("✅ KNOWLEDGE BASE DATA EXPORTED")
    print("="*70)
    print(f"Topics:            {len(topics):>6} rows -> topics.csv")
    print(f"Articles:          {len(articles):>6} rows -> articles.csv")
    print(f"🆕 Article Links:  {len(article_links_df):>6} rows -> article_links.csv")
    print(f"Tags:              {len(tags):>6} rows -> tags.csv")
    print(f"Topic Hierarchy:   {len(topic_hierarchy):>6} rows -> topic_hierarchy.csv")
    print(f"Related Topics:    {len(related_topics):>6} rows -> related_topics.csv")
    print(f"Article-Topics:    {len(article_topics):>6} rows -> article_topics.csv")
    print(f"Topic-Tags:        {len(topic_tags):>6} rows -> topic_tags.csv")
    print(f"Authors:           {len(authors):>6} rows -> authors.csv")
    print(f"Article-Authors:   {len(article_authors):>6} rows -> article_authors.csv")
    print("="*70)
    
    if not article_links_df.empty:
        print("\n📊 ARTICLE LINKS STATISTICS:")
        print(f"Total article-to-article links: {len(article_links_df)}")
        print("\nTop link types:")
        print(article_links_df['link_type'].value_counts().head(10))
        print("\nMost linked articles:")
        top_sources = article_links_df['source_article_id'].value_counts().head(5)
        for art_id, count in top_sources.items():
            title = articles[articles['article_id'] == art_id]['article_title'].values[0]
            print(f"  {title}: {count} outgoing links")
    
    print("\n Next step: Move CSVs to Neo4j import/ folder and run Cypher load script")

if __name__ == "__main__":
    main()