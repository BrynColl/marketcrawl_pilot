# MarketCrawl pilot

A conservative pilot crawler for company websites.

## 1. Create the environment

```bash
conda create -n marketcrawl python=3.12 -y
conda activate marketcrawl
pip install scrapy trafilatura pandas pyarrow lxml
```

## 2. Identify the crawler

Open:

`marketcrawl/settings.py`

Replace:

`REPLACE_WITH_YOUR_EMAIL`

with an email address you are willing to expose in the crawler User-Agent.

## 3. Review the input

`companies.tsv` contains the 20 companies supplied for the pilot.

Company IDs and domains are expected to be unique; run `python validate_input.py`
to check for duplicate normalized domains before crawling.

## 4. Run the crawl

From this project directory:

```bash
scrapy crawl companies -O pages.jsonl
```

The crawler will:

- obey robots.txt;
- make at most one simultaneous request to a given domain;
- impose a 2-second base download delay;
- use Scrapy AutoThrottle;
- prefer HTTPS;
- try sitemap.xml and sitemap_index.xml;
- score URLs for product/service/solution relevance;
- cap selected content pages at 20 per normalized domain;
- avoid query-string URLs and common crawl traps;
- save raw HTML once by SHA-256 hash in `raw_html/`;
- extract main text with Trafilatura;
- save structured page data to `pages.jsonl`.

## 5. Inspect before scaling

Do **not** immediately jump from 20 companies to thousands.

Check:

- number of pages captured per domain;
- whether pages are actually product/service/about pages;
- whether extracted text is meaningful;
- which domains return 403/429;
- which domains are mostly JavaScript shells;
- whether sitemap discovery is excessive or poor.

## 6. Convert page data into company documents

The included `build_company_docs.py` aggregates page-level records into one
document per normalized domain.

```bash
python build_company_docs.py pages.jsonl company_docs.parquet
```

The Parquet file can then feed TF-IDF, embeddings, cosine similarity, KNN,
and community-detection experiments.

## IP-ban / server-load policy

This project is intentionally conservative. It does not rotate IP addresses,
spoof browser identities, bypass CAPTCHAs, or retry 403/429 responses.

A 403 or 429 should be treated as a signal to stop or reduce access to that
site rather than an obstacle to defeat.
