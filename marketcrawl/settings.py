BOT_NAME = "marketcrawl"

SPIDER_MODULES = ["marketcrawl.spiders"]
NEWSPIDER_MODULE = "marketcrawl.spiders"

# Be a polite, identifiable research crawler.
USER_AGENT = "MarketResearchCrawler/0.1 (+contact: REPLACE_WITH_YOUR_EMAIL)"

ROBOTSTXT_OBEY = True

# Conservative per-domain behavior.
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 2.0
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 30

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2.0
AUTOTHROTTLE_MAX_DELAY = 30.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 0.5
AUTOTHROTTLE_DEBUG = False

# Retry transient failures, but do not aggressively fight explicit blocking.
RETRY_ENABLED = True
RETRY_TIMES = 2
RETRY_HTTP_CODES = [408, 425, 500, 502, 503, 504, 522, 524]

# HTTP cache means re-runs do not re-hit unchanged pages during development.
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [403, 429]

# Reasonable crawl depth and memory footprint.
DEPTH_LIMIT = 2
COOKIES_ENABLED = False
TELNETCONSOLE_ENABLED = False

FEED_EXPORT_ENCODING = "utf-8"

# Keep logs readable.
LOG_LEVEL = "INFO"

ITEM_PIPELINES = {"marketcrawl.pipelines.RawHtmlPipeline": 300}
