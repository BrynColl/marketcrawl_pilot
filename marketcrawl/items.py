import scrapy

class PageItem(scrapy.Item):
    company_ids = scrapy.Field()
    company_names = scrapy.Field()
    domain = scrapy.Field()
    url = scrapy.Field()
    canonical_url = scrapy.Field()
    page_type = scrapy.Field()
    crawl_timestamp = scrapy.Field()
    status_code = scrapy.Field()
    title = scrapy.Field()
    clean_text = scrapy.Field()
    word_count = scrapy.Field()
    content_hash = scrapy.Field()
