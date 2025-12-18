import time
import requests
import pandas as pd
import random

endpoint = "https://query.wikidata.org/sparql"
headers = {
    "Accept": "application/sparql-results+json",
    "User-Agent": "kg_wiki_project/1.0 (contact: you@example.com)"
}

# Use "organization" - has more direct subclasses with articles
ROOT_QID = "Q43229"  # organization (alternative: Q4830453 for business)

# SIMPLIFIED query - removed complex OPTIONAL clauses
BASE_QUERY = f"""
SELECT DISTINCT 
  ?concept ?conceptLabel ?conceptDescription
  ?article ?articleTitle 
  ?parent ?parentLabel
WHERE {{
  # Get direct subclasses only
  ?concept wdt:P279 wd:{ROOT_QID} .
  
  # REQUIRE Wikipedia article
  ?article schema:about ?concept ;
           schema:isPartOf <https://en.wikipedia.org/> ;
           schema:name ?articleTitle .
  
  # Get parent (same as concept's subclass)
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
    """Fetch data with pagination - smaller batches to avoid timeout"""
    offset = 0
    all_rows = []
    
    while len(all_rows) < max_results:
        query = BASE_QUERY + f"\nLIMIT {limit}\nOFFSET {offset}"
        
        print(f"Fetching offset={offset}...")
        
        for attempt in range(retries):
            try:
                r = requests.get(endpoint, params={"query": query}, headers=headers, timeout=120)
                
                if r.status_code in (429, 502, 503, 504):
                    sleep_s = 5 * (attempt + 1)  # Longer waits
                    print(f"  Server busy (HTTP {r.status_code}). Sleeping {sleep_s}s...")
                    time.sleep(sleep_s)
                    continue
                
                r.raise_for_status()
                data = r.json()["results"]["bindings"]
                
                if not data:
                    print(f"  No more results at offset={offset}")
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
                time.sleep(2)  # Be extra polite
                break
                
            except Exception as e:
                if attempt == retries - 1:
                    print(f"  ✗ Failed after {retries} attempts: {e}")
                    return pd.DataFrame(all_rows)
                time.sleep(5 * (attempt + 1))
        
        # If we got fewer results than limit, we're done
        if len(data) < limit:
            print(f"  Reached end of results")
            break
    
    return pd.DataFrame(all_rows)

def fetch_related_concepts(concept_ids: list) -> pd.DataFrame:
    """Fetch related concepts in a separate, simpler query"""
    print("\nFetching related concepts...")
    
    # Build a query for related concepts (much simpler)
    if len(concept_ids) > 50:
        concept_ids = concept_ids[:50]  # Limit to avoid timeout
    
    values_str = " ".join([f"wd:{qid}" for qid in concept_ids])
    
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
        print(f"  ✗ Failed to fetch related concepts: {e}")
        return pd.DataFrame()

def fetch_categories(concept_ids: list) -> pd.DataFrame:
    """Fetch categories/tags in a separate query"""
    print("\nFetching categories/tags...")
    
    if len(concept_ids) > 50:
        concept_ids = concept_ids[:50]
    
    values_str = " ".join([f"wd:{qid}" for qid in concept_ids])
    
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
            if cat_id != ROOT_QID:  # Exclude root
                rows.append({
                    "concept_id": qid(val(row, "concept")),
                    "category_id": cat_id,
                    "category_name": val(row, "categoryLabel"),
                })
        
        print(f"  ✓ Fetched {len(rows)} category relationships")
        return pd.DataFrame(rows)
    
    except Exception as e:
        print(f"  ✗ Failed to fetch categories: {e}")
        return pd.DataFrame()

def main():
    print("="*60)
    print("FETCHING KNOWLEDGE BASE DATA FROM WIKIDATA")
    print("="*60)
    print(f"Root concept: {ROOT_QID}")
    print("This may take 2-5 minutes...\n")
    
    # Fetch main data (concepts, articles, hierarchy)
    main_df = fetch_all_data(limit=100, max_results=500)
    
    if main_df.empty:
        print("\n✗ No data retrieved! Try a different ROOT_QID")
        return
    
    print(f"\n✓ Total rows fetched: {len(main_df)}")
    
    # Get unique concept IDs
    concept_ids = main_df["concept_id"].dropna().unique().tolist()
    print(f"✓ Unique concepts: {len(concept_ids)}")
    
    # Fetch related concepts (separate query)
    related_df = fetch_related_concepts(concept_ids)
    
    # Fetch categories (separate query)
    categories_df = fetch_categories(concept_ids)
    
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
    
    # ===== Export 3: TAGS =====
    if not categories_df.empty:
        tags = (categories_df[["category_id", "category_name"]]
                .dropna(subset=["category_id"])
                .drop_duplicates(subset=["category_id"]))
    else:
        tags = pd.DataFrame(columns=["category_id", "category_name"])
    
    # ===== Export 4: TOPIC_HIERARCHY =====
    topic_hierarchy = (main_df[["concept_id", "parent_id"]]
                       .dropna()
                       .drop_duplicates()
                       .rename(columns={"concept_id": "child_topic_id", "parent_id": "parent_topic_id"}))
    
    # ===== Export 5: RELATED_TOPICS =====
    if not related_df.empty:
        related_topics = (related_df[["concept_id", "related_id", "relation_type"]]
                          .dropna(subset=["related_id"])
                          .drop_duplicates()
                          .rename(columns={"concept_id": "topic_id", "related_id": "related_topic_id"}))
    else:
        related_topics = pd.DataFrame(columns=["topic_id", "related_topic_id", "relation_type"])
    
    # ===== Export 6: ARTICLE_TOPICS =====
    article_topics = (articles[["article_id", "concept_id"]]
                      .dropna()
                      .rename(columns={"concept_id": "topic_id"}))
    
    # ===== Export 7: TOPIC_TAGS =====
    if not categories_df.empty:
        topic_tags = (categories_df[["concept_id", "category_id"]]
                      .dropna()
                      .drop_duplicates()
                      .rename(columns={"concept_id": "topic_id", "category_id": "tag_id"}))
    else:
        topic_tags = pd.DataFrame(columns=["topic_id", "tag_id"])
    
    # ===== Export 8: AUTHORS =====
    authors = pd.DataFrame({
        "author_id": ["AUTH001", "AUTH002", "AUTH003"],
        "author_name": ["Wikipedia Contributors", "Community Editors", "Domain Experts"],
        "email": ["contributors@wikipedia.org", "editors@wikipedia.org", "experts@wikipedia.org"]
    })
    
    # ===== Export 9: ARTICLE_AUTHORS =====
    article_authors = pd.DataFrame({
        "article_id": articles["article_id"].tolist()[:min(50, len(articles))],
        "author_id": [random.choice(authors["author_id"].tolist()) for _ in range(min(50, len(articles)))]
    })
    
    # Save all CSVs
    topics.to_csv("topics.csv", index=False, encoding="utf-8")
    articles.to_csv("articles.csv", index=False, encoding="utf-8")
    tags.to_csv("tags.csv", index=False, encoding="utf-8")
    topic_hierarchy.to_csv("topic_hierarchy.csv", index=False, encoding="utf-8")
    related_topics.to_csv("related_topics.csv", index=False, encoding="utf-8")
    article_topics.to_csv("article_topics.csv", index=False, encoding="utf-8")
    topic_tags.to_csv("topic_tags.csv", index=False, encoding="utf-8")
    authors.to_csv("authors.csv", index=False, encoding="utf-8")
    article_authors.to_csv("article_authors.csv", index=False, encoding="utf-8")
    
    print("\n" + "="*60)
    print("✓ KNOWLEDGE BASE DATA EXPORTED")
    print("="*60)
    print(f"Topics:            {len(topics):>6} rows -> topics.csv")
    print(f"Articles:          {len(articles):>6} rows -> articles.csv")
    print(f"Tags:              {len(tags):>6} rows -> tags.csv")
    print(f"Topic Hierarchy:   {len(topic_hierarchy):>6} rows -> topic_hierarchy.csv")
    print(f"Related Topics:    {len(related_topics):>6} rows -> related_topics.csv")
    print(f"Article-Topics:    {len(article_topics):>6} rows -> article_topics.csv")
    print(f"Topic-Tags:        {len(topic_tags):>6} rows -> topic_tags.csv")
    print(f"Authors:           {len(authors):>6} rows -> authors.csv")
    print(f"Article-Authors:   {len(article_authors):>6} rows -> article_authors.csv")
    print("="*60)
    print("\n✓ Next step: Move CSVs to import/ folder and load into Neo4j")

if __name__ == "__main__":
    main()