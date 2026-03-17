"""
parsers/url_parser.py
Generic URL parser — layered strategy:
  1. Detect URL type (Behance / Figma / generic)
  2. Route to specialized parser or generic fetch
  3. Fallback: raw text extraction via BeautifulSoup
"""
import re
from urllib.parse import urlparse


def detect_url_type(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    if "behance.net" in domain:
        return "behance"
    if "figma.com" in domain:
        return "figma"
    if "dribbble.com" in domain:
        return "dribbble"
    if "pinterest.com" in domain:
        return "pinterest"
    return "generic"


class URLParser:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def parse(self, url: str) -> dict:
        url_type = detect_url_type(url)

        if url_type == "behance":
            from parsers.behance_parser import BehanceParser
            return BehanceParser(api_key=self.api_key).parse(url)

        if url_type == "figma":
            from parsers.figma_parser import FigmaParser
            return FigmaParser(api_key=self.api_key).parse(url)

        if url_type in ("dribbble", "pinterest"):
            # Visual-first fallback — treat like Behance
            from parsers.behance_parser import BehanceParser
            return BehanceParser(api_key=self.api_key).parse(url)

        return self._generic_fetch(url)

    def _generic_fetch(self, url: str) -> dict:
        """
        Generic fetch: requests + BeautifulSoup.
        Extracts meaningful text: title, meta description, headings, paragraphs.
        Strips nav/footer/scripts.
        """
        try:
            import requests
            from bs4 import BeautifulSoup

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
            }

            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove noise
            for tag in soup(["script", "style", "nav", "footer", "header",
                              "aside", "noscript", "iframe", "svg"]):
                tag.decompose()

            # Extract structured content
            parts = []

            title = soup.find("title")
            if title:
                parts.append(f"TITLE: {title.get_text(strip=True)}")

            for meta in soup.find_all("meta", attrs={"name": True}):
                name = meta.get("name", "").lower()
                content = meta.get("content", "").strip()
                if name in ("description", "keywords", "author") and content:
                    parts.append(f"{name.upper()}: {content}")

            # Open Graph tags (rich metadata)
            for og in soup.find_all("meta", property=re.compile(r"^og:")):
                prop = og.get("property", "").replace("og:", "").upper()
                content = og.get("content", "").strip()
                if content and prop in ("TITLE", "DESCRIPTION", "SITE_NAME", "TYPE"):
                    parts.append(f"OG_{prop}: {content}")

            # Headings
            for tag in soup.find_all(["h1", "h2", "h3"]):
                text = tag.get_text(strip=True)
                if text and len(text) > 3:
                    parts.append(f"{tag.name.upper()}: {text}")

            # Paragraphs
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 40:
                    parts.append(text)

            # Strong/em for highlighted content
            for tag in soup.find_all(["strong", "em", "b"]):
                text = tag.get_text(strip=True)
                if len(text) > 10:
                    parts.append(f"HIGHLIGHTED: {text}")

            text = "\n".join(parts)

            if len(text) < 200:
                return {
                    "text": text,
                    "modality": "url_generic",
                    "warning": "Limited content extracted. Site may be JS-rendered.",
                    "url": url,
                }

            return {"text": text[:12000], "modality": "url_generic", "url": url}

        except Exception as e:
            return {"text": "", "error": str(e), "url": url}
