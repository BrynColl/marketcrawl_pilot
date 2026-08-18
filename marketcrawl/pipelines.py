from pathlib import Path
import hashlib

class RawHtmlPipeline:
    def open_spider(self, spider):
        self.root = Path("raw_html")
        self.root.mkdir(exist_ok=True)

    def process_item(self, item, spider):
        raw_html = item.pop("_raw_html", None)
        if raw_html:
            digest = hashlib.sha256(raw_html).hexdigest()
            item["content_hash"] = digest
            path = self.root / f"{digest}.html"
            if not path.exists():
                path.write_bytes(raw_html)
        return item
