"""
parsers/behance_parser.py
Extracts brand identity from Behance (and Dribbble/Pinterest) project pages.

Strategy (layered):
  1. Scrape metadata + project text via requests + BeautifulSoup
  2. Extract image URLs from the gallery
  3. Download and analyze key images via Groq vision (llama-3.2-11b-vision-preview)
  4. Synthesize text + visual analysis into a unified brand description
"""
import re
import base64
import io
from urllib.parse import urljoin, urlparse


BRAND_VISION_PROMPT = """You are a brand identity analyst examining visual design work.

Analyze this image from a brand identity project and extract:

1. BRAND ELEMENTS visible:
   - Color palette (describe colors, mood, associations)
   - Typography style (serif/sans/display, weight, personality)
   - Logo/mark style (if visible: geometric, organic, wordmark, etc.)
   - Visual language (patterns, textures, shapes)

2. BRAND PERSONALITY inferred:
   - Values the brand communicates (e.g. trust, playfulness, luxury, sustainability)
   - Target audience implied by the design choices
   - Tone and voice the visuals suggest

3. WHAT THIS BRAND WOULD NEVER DO:
   - Design choices that would violate this brand identity
   - Colors, styles, or approaches that feel wrong for this brand

4. EXAMPLES of good brand application visible in the image.

Be specific and concrete. Reference actual visual elements you see.
Format your response as structured observations, not generic descriptions."""


SYNTHESIS_PROMPT = """You are a brand strategist. Based on the visual and textual analysis below from a brand identity project on Behance, create a comprehensive brand identity summary.

Extract and organize:
- Brand name and sector/industry
- Core brand values (3-5 concrete values)
- Target audience (specific, not generic)
- Tone of voice (how they communicate)
- Visual identity summary (colors, typography, style)
- Restrictions (what this brand would never do)
- 2-3 example applications of the brand

Be specific. Use concrete language. This will be used to build a knowledge graph.

PROJECT DATA:
{data}"""


class BehanceParser:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def parse(self, url: str) -> dict:
        results = {
            "text": "",
            "modality": "behance",
            "url": url,
            "images_analyzed": 0,
            "error": None,
        }

        # Step 1: Scrape metadata and text
        meta_text, image_urls = self._scrape(url)

        # Step 2: Analyze images via vision AI
        visual_descriptions = []
        if self.api_key and image_urls:
            # Analyze up to 4 images (balance quality vs speed/quota)
            for img_url in image_urls[:4]:
                desc = self._analyze_image_url(img_url)
                if desc:
                    visual_descriptions.append(desc)
                    results["images_analyzed"] += 1

        # Step 3: Synthesize everything
        combined = self._synthesize(meta_text, visual_descriptions, url)
        results["text"] = combined

        if not combined:
            results["error"] = "Could not extract content from this URL. Site may block scraping."

        return results

    def _scrape(self, url: str) -> tuple[str, list]:
        """Returns (text_content, image_urls)"""
        try:
            import requests
            from bs4 import BeautifulSoup

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.behance.net/",
            }

            resp = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(resp.text, "html.parser")

            text_parts = []

            # Title
            title = soup.find("title")
            if title:
                text_parts.append(f"PROJECT: {title.get_text(strip=True)}")

            # Meta tags
            for meta in soup.find_all("meta"):
                name = meta.get("name", meta.get("property", "")).lower()
                content = meta.get("content", "").strip()
                if content and any(k in name for k in
                    ("description", "title", "keywords", "og:title",
                     "og:description", "twitter:title", "twitter:description")):
                    text_parts.append(f"{name.upper()}: {content}")

            # All text nodes (Behance renders some server-side)
            for tag in soup(["script", "style", "nav", "svg"]):
                tag.decompose()

            # Project title / owner / tags
            for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
                t = tag.get_text(strip=True)
                if t and len(t) > 2:
                    text_parts.append(f"HEADING: {t}")

            for p in soup.find_all("p"):
                t = p.get_text(strip=True)
                if len(t) > 30:
                    text_parts.append(t)

            # Behance-specific: project tags, tools, categories
            for tag in soup.find_all(attrs={"class": re.compile(r"tag|skill|tool|category|field", re.I)}):
                t = tag.get_text(strip=True)
                if t and len(t) > 2:
                    text_parts.append(f"TAG: {t}")

            # JSON-LD structured data (Behance often embeds this)
            import json
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        for key in ("name", "description", "keywords", "creator"):
                            if key in data:
                                text_parts.append(f"STRUCTURED_{key.upper()}: {data[key]}")
                except Exception:
                    pass

            # Collect image URLs
            image_urls = []
            base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src") or img.get("data-lazy-src", "")
                if src and self._is_content_image(src):
                    full_url = src if src.startswith("http") else urljoin(base, src)
                    image_urls.append(full_url)

            # Also check srcset
            for img in soup.find_all("img", srcset=True):
                srcset = img.get("srcset", "")
                for part in srcset.split(","):
                    src = part.strip().split()[0]
                    if src and self._is_content_image(src):
                        full_url = src if src.startswith("http") else urljoin(base, src)
                        if full_url not in image_urls:
                            image_urls.append(full_url)

            # Deduplicate, prefer larger images (Behance uses size suffixes)
            image_urls = self._prioritize_images(image_urls)

            return "\n".join(text_parts), image_urls

        except Exception as e:
            return f"Scraping error: {e}", []

    def _is_content_image(self, src: str) -> bool:
        """Filter out icons, avatars, tracking pixels."""
        if not src or len(src) < 10:
            return False
        skip = ("avatar", "icon", "logo_small", "pixel", "tracking",
                "badge", "1x1", "spacer", "sprite", ".gif", "thumbnail_small")
        return not any(s in src.lower() for s in skip)

    def _prioritize_images(self, urls: list) -> list:
        """Prefer high-resolution Behance images (contain 'max_1200' or similar)."""
        def score(u):
            if "max_1200" in u or "max_3840" in u:
                return 3
            if "max_800" in u or "max_900" in u:
                return 2
            if any(x in u for x in (".jpg", ".jpeg", ".png", ".webp")):
                return 1
            return 0
        seen = set()
        result = []
        for u in sorted(urls, key=score, reverse=True):
            if u not in seen:
                seen.add(u)
                result.append(u)
        return result

    def _analyze_image_url(self, img_url: str) -> str:
        """Download image and analyze with Groq vision."""
        try:
            import requests
            from groq import Groq

            resp = requests.get(img_url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.behance.net/",
            })

            if resp.status_code != 200:
                return ""

            content_type = resp.headers.get("content-type", "image/jpeg")
            if "image" not in content_type:
                return ""

            # Resize if too large (>4MB) to stay within API limits
            img_data = resp.content
            if len(img_data) > 4_000_000:
                img_data = self._resize_image(img_data)

            b64 = base64.b64encode(img_data).decode()
            mime = content_type.split(";")[0].strip()
            if mime not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
                mime = "image/jpeg"

            client = Groq(api_key=self.api_key)
            response = client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{b64}"},
                            },
                            {"type": "text", "text": BRAND_VISION_PROMPT},
                        ],
                    }
                ],
                max_tokens=800,
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            return ""

    def _resize_image(self, img_data: bytes) -> bytes:
        """Resize image to reduce size for API. Returns original if PIL not available."""
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(img_data))
            img.thumbnail((1200, 1200), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return buf.getvalue()
        except Exception:
            return img_data[:4_000_000]

    def _synthesize(self, meta_text: str, visual_descriptions: list, url: str) -> str:
        """Synthesize text + visual analysis into unified brand description."""
        if not self.api_key:
            # Without API key, return raw text only
            return meta_text or ""

        if not visual_descriptions and not meta_text:
            return ""

        # Build synthesis input
        parts = []
        if meta_text:
            parts.append(f"=== TEXT/METADATA FROM PAGE ===\n{meta_text[:3000]}")

        for i, desc in enumerate(visual_descriptions, 1):
            parts.append(f"=== VISUAL ANALYSIS — IMAGE {i} ===\n{desc}")

        combined_input = "\n\n".join(parts)

        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": SYNTHESIS_PROMPT.format(data=combined_input),
                    },
                    {
                        "role": "user",
                        "content": f"Create a comprehensive brand identity summary for extraction into a knowledge graph. Source: {url}",
                    },
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            # Fallback: return raw combined without synthesis
            return combined_input
