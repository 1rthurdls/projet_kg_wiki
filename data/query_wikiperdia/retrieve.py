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

    if len(concept_ids) > 200:
        concept_ids = concept_ids[:200]
    
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
    LIMIT 1000
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

    if len(concept_ids) > 200:
        concept_ids = concept_ids[:200]
    
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

    if len(concept_ids) > 200:
        concept_ids = concept_ids[:200]

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

def fetch_authors_from_xtools(articles_df: pd.DataFrame, max_articles: int = 50, top_n_editors: int = 10) -> tuple:
    """
    Fetch real Wikipedia contributors using XTools API

    Args:
        articles_df: DataFrame with article_title column
        max_articles: Maximum number of articles to fetch authors for (to avoid long runtime)
        top_n_editors: Number of top editors to fetch per article

    Returns:
        tuple: (authors_df, article_authors_df)
    """
    print("\n" + "="*70)
    print("FETCHING REAL AUTHORS FROM XTOOLS")
    print("="*70)
    print(f"Querying XTools for top {top_n_editors} editors per article...")
    print(f"Processing up to {max_articles} articles (this may take a few minutes)")

    # Limit the number of articles to process
    articles_to_process = articles_df.head(max_articles)

    all_authors = {}  # username -> author data
    article_author_pairs = []  # (article_id, author_username, edit_count)

    for idx, row in articles_to_process.iterrows():
        article_id = row['article_id']
        article_title = row['article_title']

        # URL encode the article title
        encoded_title = requests.utils.quote(article_title.replace(' ', '_'))
        xtools_url = f"https://xtools.wmcloud.org/api/page/top_editors/en.wikipedia.org/{encoded_title}"

        try:
            print(f"  [{idx+1}/{len(articles_to_process)}] Fetching authors for: {article_title}")
            r = requests.get(xtools_url, timeout=30)

            if r.status_code == 404:
                print(f"    ⚠ Article not found, skipping...")
                time.sleep(1)
                continue

            if r.status_code != 200:
                print(f"    ⚠ HTTP {r.status_code}, skipping...")
                time.sleep(2)
                continue

            data = r.json()

            # Extract top editors
            top_editors = data.get('top_editors', [])
            if not top_editors:
                print(f"    ⚠ No editors found, skipping...")
                time.sleep(1)
                continue

            # Take top N editors
            for editor in top_editors[:top_n_editors]:
                username = editor.get('username')
                edit_count = editor.get('count', 0)

                if not username:
                    continue

                # Add to authors dict if not already present
                if username not in all_authors:
                    all_authors[username] = {
                        'username': username,
                        'total_edits': 0
                    }

                # Track total edits across all articles
                all_authors[username]['total_edits'] += edit_count

                # Add article-author relationship
                article_author_pairs.append({
                    'article_id': article_id,
                    'author_username': username,
                    'edit_count': edit_count
                })

            print(f"    ✓ Found {len(top_editors[:top_n_editors])} editors")

            # Rate limiting - be nice to XTools
            time.sleep(1.5)

        except requests.exceptions.Timeout:
            print(f"    ✗ Timeout, skipping...")
            time.sleep(2)
        except Exception as e:
            print(f"    ✗ Error: {e}")
            time.sleep(2)

    # Create authors DataFrame
    if all_authors:
        authors_list = []
        for idx, (username, data) in enumerate(all_authors.items(), 1):
            authors_list.append({
                'author_id': f"AUTH{str(idx).zfill(5)}",
                'author_name': username,
                'total_edits': data['total_edits']
            })
        authors_df = pd.DataFrame(authors_list)

        # Map usernames to author IDs for article_authors
        username_to_id = dict(zip(authors_df['author_name'], authors_df['author_id']))

        # Create article_authors DataFrame
        article_authors_list = []
        for pair in article_author_pairs:
            author_id = username_to_id.get(pair['author_username'])
            if author_id:
                article_authors_list.append({
                    'article_id': pair['article_id'],
                    'author_id': author_id,
                    'edit_count': pair['edit_count']
                })
        article_authors_df = pd.DataFrame(article_authors_list)

        print(f"\n✓ Total unique authors found: {len(authors_df)}")
        print(f"✓ Total article-author relationships: {len(article_authors_df)}")

        return authors_df, article_authors_df
    else:
        print("\n✗ No authors retrieved!")
        # Return empty DataFrames with correct schema
        return (
            pd.DataFrame(columns=['author_id', 'author_name', 'total_edits']),
            pd.DataFrame(columns=['article_id', 'author_id', 'edit_count'])
        )

def main():
    print("="*70)
    print("KNOWLEDGE BASE DATA EXTRACTION WITH ARTICLE LINKS")
    print("="*70)
    print(f"Root concept: {ROOT_QID} (organization)")
    print("Estimated time: 10-15 minutes (larger dataset)\n")
    
    # ===== STEP 1: Fetch main data =====
    main_df = fetch_all_data(limit=100, max_results=2000)
    
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
    
    # ===== Export 9 & 10: AUTHORS & ARTICLE_AUTHORS (from XTools) =====
    authors, article_authors = fetch_authors_from_xtools(
        articles,
        max_articles=100,  # Process up to 100 articles (adjust as needed)
        top_n_editors=10   # Get top 10 editors per article
    )
    
    # ===== SAVE ALL CSVs =====
    topics.to_csv("import/topics.csv", index=False, encoding="utf-8")
    articles.to_csv("import/articles.csv", index=False, encoding="utf-8")
    article_links_df.to_csv("import/article_links.csv", index=False, encoding="utf-8")  # NOUVEAU!
    tags.to_csv("import/tags.csv", index=False, encoding="utf-8")
    topic_hierarchy.to_csv("import/topic_hierarchy.csv", index=False, encoding="utf-8")
    related_topics.to_csv("import/related_topics.csv", index=False, encoding="utf-8")
    article_topics.to_csv("import/article_topics.csv", index=False, encoding="utf-8")
    topic_tags.to_csv("import/topic_tags.csv", index=False, encoding="utf-8")
    authors.to_csv("import/authors.csv", index=False, encoding="utf-8")
    article_authors.to_csv("import/article_authors.csv", index=False, encoding="utf-8")
    
    # ===== FINAL REPORT =====
    print("\n" + "="*70)
    print("✅ KNOWLEDGE BASE DATA EXPORTED")
    print("="*70)
    print(f"Topics:            {len(topics):>6} rows -> import/topics.csv")
    print(f"Articles:          {len(articles):>6} rows -> import/articles.csv")
    print(f"🆕 Article Links:  {len(article_links_df):>6} rows -> import/article_links.csv")
    print(f"Tags:              {len(tags):>6} rows -> import/tags.csv")
    print(f"Topic Hierarchy:   {len(topic_hierarchy):>6} rows -> import/topic_hierarchy.csv")
    print(f"Related Topics:    {len(related_topics):>6} rows -> import/related_topics.csv")
    print(f"Article-Topics:    {len(article_topics):>6} rows -> import/article_topics.csv")
    print(f"Topic-Tags:        {len(topic_tags):>6} rows -> import/topic_tags.csv")
    print(f"Authors:           {len(authors):>6} rows -> import/authors.csv")
    print(f"Article-Authors:   {len(article_authors):>6} rows -> import/article_authors.csv")
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
    
    print("\n✅ CSVs saved to import/ folder. Next step: Run Cypher load script")

if __name__ == "__main__":
    main()