from __future__ import annotations

import csv
import hashlib
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import scrapy
import trafilatura

from marketcrawl.items import PageItem


POSITIVE = {
    "product": 5,
    "products": 5,
    "service": 5,
    "services": 5,
    "solution": 5,
    "solutions": 5,
    "platform": 5,
    "use-case": 4,
    "use-cases": 4,
    "usecase": 4,
    "industry": 3,
    "industries": 3,
    "about": 2,
    "company": 1,
    "pricing": 2,
}

NEGATIVE = {
    "blog": -8,
    "news": -8,
    "press": -8,
    "career": -10,
    "careers": -10,
    "jobs": -10,
    "job": -10,
    "privacy": -12,
    "terms": -12,
    "legal": -12,
    "login": -12,
    "signin": -12,
    "sign-in": -12,
    "signup": -8,
    "sign-up": -8,
    "support": -6,
    "docs": -6,
    "documentation": -6,
    "help": -6,
    "events": -6,
    "webinar": -6,
    "webinars": -6,
    "podcast": -6,
    "tag": -10,
    "author": -10,
    "search": -10,
    "feed": -10,
}

EXCLUDED_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".zip", ".xml", ".json", ".rss", ".mp4", ".mp3", ".css", ".js"
}

MAX_PAGES_PER_DOMAIN = 20


def normalize_domain(raw: str) -> str:
    raw = raw.strip()
    if "://" not in raw:
        raw = "https://" + raw
    p = urlparse(raw)
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def normalize_url(url: str) -> str:
    p = urlparse(url)
    scheme = "https" if p.scheme in {"http", "https"} else p.scheme
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/+", "/", p.path or "/")
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return urlunparse((scheme, host, path, "", "", ""))


def page_score(url: str) -> int:
    p = urlparse(url)
    path = (p.path or "/").lower()
    tokens = [t for t in re.split(r"[/_\-.]+", path) if t]

    # Homepage is always valuable.
    score = 6 if path in {"", "/"} else 0

    for token in tokens:
        score += POSITIVE.get(token, 0)
        score += NEGATIVE.get(token, 0)

    # Avoid deep, noisy URLs.
    depth = len([x for x in path.split("/") if x])
    score -= max(0, depth - 3)

    if p.query:
        score -= 5

    return score


def infer_page_type(url: str) -> str:
    path = urlparse(url).path.lower()
    for label in ["products", "product", "services", "service", "solutions", "solution",
                  "platform", "industries", "industry", "use-cases", "use-case",
                  "pricing", "about"]:
        if label in path:
            return label
    return "homepage" if path in {"", "/"} else "other"


class CompanySpider(scrapy.Spider):
    name = "companies"

    custom_settings = {
        "ITEM_PIPELINES": {"marketcrawl.pipelines.RawHtmlPipeline": 300},
    }

    def __init__(self, input_path="companies.tsv", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_path = input_path
        self.company_by_domain = defaultdict(list)
        self.seen_urls = defaultdict(set)
        self.selected_counts = defaultdict(int)

        with open(input_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                domain = normalize_domain(row["domain"])
                self.company_by_domain[domain].append(row)

    def start_requests(self):
        for domain in sorted(self.company_by_domain):
            # Prefer HTTPS. Redirects will be followed automatically.
            root = f"https://{domain}/"
            yield scrapy.Request(
                root,
                callback=self.parse_home,
                errback=self.errback,
                meta={"domain": domain},
                dont_filter=True,
            )

    def parse_home(self, response):
        domain = response.meta["domain"]
        self._record_seen(domain, response.url)

        # Always save homepage.
        yield self.make_item(response, domain, "homepage")
        self.selected_counts[domain] += 1

        # First, try common sitemap locations. sitemap.xml may itself be an index.
        for sitemap_url in [
            urljoin(response.url, "/sitemap.xml"),
            urljoin(response.url, "/sitemap_index.xml"),
        ]:
            yield scrapy.Request(
                sitemap_url,
                callback=self.parse_sitemap,
                errback=self.errback,
                meta={"domain": domain},
                dont_filter=True,
            )

        # Also collect a small set of same-domain links from the homepage.
        candidates = []
        for href in response.css("a::attr(href)").getall():
            url = response.urljoin(href)
            if self.allowed_url(domain, url):
                candidates.append(url)

        yield from self.schedule_candidates(domain, candidates)

    def parse_sitemap(self, response):
        domain = response.meta["domain"]
        if response.status != 200:
            return

        # Extract <loc> values without needing namespace-specific XPath.
        locs = response.xpath("//*[local-name()='loc']/text()").getall()
        sitemap_children = []
        page_candidates = []

        for loc in locs:
            loc = loc.strip()
            if loc.lower().endswith(".xml"):
                sitemap_children.append(loc)
            elif self.allowed_url(domain, loc):
                page_candidates.append(loc)

        # Only recurse through a small number of sitemap files.
        for child in sitemap_children[:10]:
            yield scrapy.Request(
                child,
                callback=self.parse_sitemap,
                errback=self.errback,
                meta={"domain": domain},
            )

        yield from self.schedule_candidates(domain, page_candidates)

    def schedule_candidates(self, domain, urls):
        # Normalize + unique, then score.
        unique = {}
        for url in urls:
            norm = normalize_url(url)
            if norm not in unique:
                unique[norm] = url

        ranked = sorted(unique.values(), key=lambda u: (page_score(u), -len(u)), reverse=True)

        remaining = max(0, MAX_PAGES_PER_DOMAIN - self.selected_counts[domain])
        for url in ranked[:remaining]:
            norm = normalize_url(url)
            if norm in self.seen_urls[domain]:
                continue
            self.seen_urls[domain].add(norm)
            self.selected_counts[domain] += 1
            yield scrapy.Request(
                url,
                callback=self.parse_page,
                errback=self.errback,
                meta={"domain": domain},
            )

    def parse_page(self, response):
        domain = response.meta["domain"]
        yield self.make_item(response, domain, infer_page_type(response.url))

    def make_item(self, response, domain, page_type):
        rows = self.company_by_domain[domain]
        html = response.body

        # Trafilatura extracts main text; fallback to visible response text.
        clean = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
            deduplicate=True,
        ) or ""

        title = response.css("title::text").get()
        item = PageItem(
            company_ids=[r["company_id"] for r in rows],
            company_names=[r["company_name"] for r in rows],
            domain=domain,
            url=response.url,
            canonical_url=normalize_url(response.url),
            page_type=page_type,
            crawl_timestamp=datetime.now(timezone.utc).isoformat(),
            status_code=response.status,
            title=(title or "").strip(),
            clean_text=clean,
            word_count=len(clean.split()),
            content_hash=hashlib.sha256(html).hexdigest(),
        )
        item["_raw_html"] = html
        return item

    def allowed_url(self, domain, url):
        p = urlparse(url)
        if p.scheme not in {"http", "https"}:
            return False

        host = (p.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if host != domain:
            return False

        path = p.path.lower()
        if any(path.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
            return False

        # Reject obvious traps/noise.
        low = url.lower()
        if any(f"/{x}/" in low or low.endswith(f"/{x}") for x in
               ["login", "signin", "sign-in", "cart", "search", "tag", "author", "feed"]):
            return False

        # Avoid query-string combinatorial traps in the pilot.
        if p.query:
            return False

        return page_score(url) >= 0

    def _record_seen(self, domain, url):
        self.seen_urls[domain].add(normalize_url(url))

    def errback(self, failure):
        request = failure.request
        domain = request.meta.get("domain", "")
        self.logger.warning("Request failed for %s: %s", domain, request.url)
