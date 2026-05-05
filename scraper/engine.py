"""
Core scraping engine - handles HTTP requests, parsing, and data extraction.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import re


class ScraperEngine:
    """Main scraping engine that fetches and parses web pages."""

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    def __init__(self, timeout=15, retries=3, delay=1.0):
        self.timeout = timeout
        self.retries = retries
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        self._last_response = None

    def fetch(self, url, method="GET", headers=None, params=None, data=None, json_data=None):
        """Fetch a URL with retry logic."""
        if headers:
            merged = {**self.DEFAULT_HEADERS, **headers}
        else:
            merged = self.DEFAULT_HEADERS

        last_error = None
        for attempt in range(self.retries):
            try:
                resp = self.session.request(
                    method=method,
                    url=url,
                    headers=merged,
                    params=params,
                    data=data,
                    json=json_data,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                self._last_response = resp
                return resp
            except requests.RequestException as e:
                last_error = e
                if attempt < self.retries - 1:
                    time.sleep(self.delay * (attempt + 1))

        raise last_error

    def fetch_page(self, url):
        """Fetch and return a BeautifulSoup parsed page."""
        resp = self.fetch(url)
        soup = BeautifulSoup(resp.content, "lxml")
        return soup, resp

    def get_last_response(self):
        return self._last_response


class PageAnalyzer:
    """Analyzes a parsed page and extracts structured overview data."""

    def __init__(self, soup, url):
        self.soup = soup
        self.url = url
        self.base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    def get_overview(self):
        """Return a full structured overview of the page."""
        return {
            "title": self._get_title(),
            "meta": self._get_meta(),
            "headings": self._get_headings(),
            "links": self._get_links(),
            "images": self._get_images(),
            "tables": self._get_tables(),
            "forms": self._get_forms(),
            "paragraphs": self._get_paragraphs(),
            "lists": self._get_lists(),
            "scripts": self._get_scripts(),
            "styles": self._get_styles(),
            "raw_text": self._get_raw_text(),
        }

    def _get_title(self):
        tag = self.soup.find("title")
        return tag.get_text(strip=True) if tag else ""

    def _get_meta(self):
        metas = []
        for tag in self.soup.find_all("meta"):
            entry = {}
            if tag.get("name"):
                entry["name"] = tag["name"]
            if tag.get("property"):
                entry["property"] = tag["property"]
            if tag.get("content"):
                entry["content"] = tag["content"]
            if tag.get("charset"):
                entry["charset"] = tag["charset"]
            if entry:
                metas.append(entry)
        return metas

    def _get_headings(self):
        headings = []
        for level in range(1, 7):
            for tag in self.soup.find_all(f"h{level}"):
                headings.append({
                    "level": level,
                    "text": tag.get_text(strip=True),
                    "id": tag.get("id", ""),
                    "class": " ".join(tag.get("class", [])),
                })
        return headings

    def _get_links(self):
        links = []
        for tag in self.soup.find_all("a", href=True):
            href = tag["href"]
            abs_url = urljoin(self.url, href)
            links.append({
                "text": tag.get_text(strip=True),
                "href": abs_url,
                "original_href": href,
                "title": tag.get("title", ""),
            })
        return links

    def _get_images(self):
        images = []
        for tag in self.soup.find_all("img"):
            src = tag.get("src", "")
            abs_src = urljoin(self.url, src) if src else ""
            images.append({
                "src": abs_src,
                "alt": tag.get("alt", ""),
                "title": tag.get("title", ""),
                "width": tag.get("width", ""),
                "height": tag.get("height", ""),
            })
        return images

    def _get_tables(self):
        tables = []
        for idx, table in enumerate(self.soup.find_all("table")):
            rows = []
            for tr in table.find_all("tr"):
                cells = []
                for cell in tr.find_all(["td", "th"]):
                    cells.append({
                        "tag": cell.name,
                        "text": cell.get_text(strip=True),
                    })
                if cells:
                    rows.append(cells)
            tables.append({
                "index": idx,
                "id": table.get("id", ""),
                "class": " ".join(table.get("class", [])),
                "rows": rows,
                "row_count": len(rows),
            })
        return tables

    def _get_forms(self):
        forms = []
        for form in self.soup.find_all("form"):
            fields = []
            for inp in form.find_all(["input", "textarea", "select"]):
                fields.append({
                    "tag": inp.name,
                    "type": inp.get("type", ""),
                    "name": inp.get("name", ""),
                    "id": inp.get("id", ""),
                    "placeholder": inp.get("placeholder", ""),
                })
            forms.append({
                "action": form.get("action", ""),
                "method": form.get("method", "GET"),
                "id": form.get("id", ""),
                "fields": fields,
            })
        return forms

    def _get_paragraphs(self):
        paragraphs = []
        for p in self.soup.find_all("p"):
            text = p.get_text(strip=True)
            if text:
                paragraphs.append({
                    "text": text,
                    "class": " ".join(p.get("class", [])),
                    "id": p.get("id", ""),
                })
        return paragraphs

    def _get_lists(self):
        lists = []
        for lst in self.soup.find_all(["ul", "ol"]):
            items = []
            for li in lst.find_all("li", recursive=False):
                items.append(li.get_text(strip=True))
            lists.append({
                "type": lst.name,
                "id": lst.get("id", ""),
                "class": " ".join(lst.get("class", [])),
                "items": items,
            })
        return lists

    def _get_scripts(self):
        scripts = []
        for s in self.soup.find_all("script"):
            scripts.append({
                "src": s.get("src", ""),
                "type": s.get("type", ""),
                "has_inline": bool(s.string and s.string.strip()),
            })
        return scripts

    def _get_styles(self):
        styles = []
        for link in self.soup.find_all("link", rel="stylesheet"):
            styles.append({"href": link.get("href", ""), "type": "external"})
        for style in self.soup.find_all("style"):
            styles.append({"type": "inline", "length": len(style.get_text())})
        return styles

    def _get_raw_text(self):
        text = self.soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)


class DataExtractor:
    """Extracts specific data from a page based on user-selected fields."""

    def __init__(self, soup, url):
        self.soup = soup
        self.url = url
        self.analyzer = PageAnalyzer(soup, url)

    def extract(self, selections):
        """
        Extract data based on selections dict.
        Keys are category names, values are True/False or sub-config dicts.
        """
        overview = self.analyzer.get_overview()
        result = {}

        for key, config in selections.items():
            if not config:
                continue
            if key in overview:
                if isinstance(config, dict):
                    result[key] = self._filter_data(overview[key], config)
                else:
                    result[key] = overview[key]

        return result

    def extract_css_selector(self, selector):
        """Extract elements matching a CSS selector."""
        elements = self.soup.select(selector)
        results = []
        for el in elements:
            results.append({
                "tag": el.name,
                "text": el.get_text(strip=True),
                "html": str(el),
                "attrs": dict(el.attrs),
            })
        return results

    def extract_xpath_like(self, tag, attrs=None):
        """Extract elements by tag and optional attributes."""
        elements = self.soup.find_all(tag, attrs=attrs or {})
        results = []
        for el in elements:
            results.append({
                "tag": el.name,
                "text": el.get_text(strip=True),
                "html": str(el),
                "attrs": dict(el.attrs),
            })
        return results

    def _filter_data(self, data, config):
        """Apply filters to extracted data."""
        if isinstance(data, list) and "limit" in config:
            data = data[: config["limit"]]
        if isinstance(data, list) and "search" in config:
            pattern = re.compile(config["search"], re.IGNORECASE)
            data = [
                item for item in data
                if isinstance(item, dict) and any(
                    pattern.search(str(v)) for v in item.values()
                )
            ]
        return data
