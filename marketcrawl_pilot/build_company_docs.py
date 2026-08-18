import json
import sys
from pathlib import Path

import pandas as pd


def main(src, dst):
    rows = []
    with open(src, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("No page records found.")

    df = df[df["clean_text"].fillna("").str.len() > 0].copy()
    df["crawl_timestamp"] = pd.to_datetime(df["crawl_timestamp"], utc=True)

    company = (
        df.sort_values(["domain", "page_type", "url"])
          .groupby("domain", as_index=False)
          .agg(
              company_ids=("company_ids", "first"),
              company_names=("company_names", "first"),
              n_pages=("url", "nunique"),
              urls=("url", list),
              page_types=("page_type", list),
              document=("clean_text", lambda s: "\n\n".join(s)),
              total_words=("word_count", "sum"),
              crawl_timestamp_max=("crawl_timestamp", "max"),
          )
    )

    company.to_parquet(dst, index=False)
    print(f"Wrote {len(company):,} company documents to {dst}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python build_company_docs.py pages.jsonl company_docs.parquet")
    main(sys.argv[1], sys.argv[2])
