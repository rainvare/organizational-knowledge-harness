"""
parsers/figma_parser.py
Extracts brand identity from Figma links.

Two modes:
  A. Public link (no token): capture embed thumbnail + metadata via oEmbed
  B. With FIGMA_TOKEN: full file inspection via Figma REST API
     → extracts color styles, text styles, component names, typography

Usage:
  FigmaParser(api_key=groq_key, figma_token="fig_xxx").parse(url)
"""
import re
import json
import base64
from urllib.parse import urlparse, parse_qs


class FigmaParser:
    def __init__(self, api_key: str = "", figma_token: str = ""):
        self.api_key = api_key          # Groq key for vision
        self.figma_token = figma_token  # Figma personal access token

    def parse(self, url: str) -> dict:
        file_key, node_id = self._extract_ids(url)

        if not file_key:
            return {
                "text": "",
                "error": "Could not extract Figma file key from URL.",
                "url": url,
                "modality": "figma",
            }

        if self.figma_token:
            return self._parse_with_api(url, file_key, node_id)
        else:
            return self._parse_public(url, file_key, node_id)

    def _extract_ids(self, url: str) -> tuple[str, str]:
        """Extract file_key and optional node_id from Figma URL."""
        # Patterns:
        # https://www.figma.com/file/FILE_KEY/title
        # https://www.figma.com/design/FILE_KEY/title
        # https://www.figma.com/proto/FILE_KEY/title?node-id=...
        match = re.search(r"figma\.com/(?:file|design|proto)/([a-zA-Z0-9]+)", url)
        file_key = match.group(1) if match else ""

        # Node ID from query param
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        node_id = params.get("node-id", [""])[0]

        return file_key, node_id

    def _parse_public(self, url: str, file_key: str, node_id: str) -> dict:
        """
        Public mode (no token):
        1. Try Figma oEmbed for title/description
        2. Capture thumbnail image and analyze via vision AI
        """
        text_parts = [f"SOURCE: Figma project ({url})"]
        thumbnail_url = None

        # 1. oEmbed endpoint (public, no auth required)
        try:
            import requests
            oembed_url = f"https://www.figma.com/oembed?url={url}"
            resp = requests.get(oembed_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("title"):
                    text_parts.append(f"PROJECT TITLE: {data['title']}")
                if data.get("provider_name"):
                    text_parts.append(f"PLATFORM: {data['provider_name']}")
                # oEmbed gives a thumbnail URL
                thumbnail_url = data.get("thumbnail_url")
        except Exception:
            pass

        # 2. Figma public thumbnail API (works without token for public files)
        if not thumbnail_url:
            thumbnail_url = f"https://www.figma.com/file/{file_key}/thumbnail"

        # 3. Analyze thumbnail via vision
        visual_desc = ""
        if self.api_key and thumbnail_url:
            visual_desc = self._analyze_thumbnail(thumbnail_url)
            if visual_desc:
                text_parts.append(f"\n=== VISUAL ANALYSIS ===\n{visual_desc}")

        text_parts.append(
            "\nNOTE: Full token-based extraction not available. "
            "For exact HEX colors, font names, and component structure, "
            "provide a Figma personal access token."
        )

        if len("\n".join(text_parts)) < 100 and not visual_desc:
            return {
                "text": "",
                "modality": "figma",
                "url": url,
                "error": (
                    "Figma file may be private or the link may require authentication. "
                    "Share the file publicly or provide a Figma token."
                ),
            }

        return {
            "text": "\n".join(text_parts),
            "modality": "figma",
            "url": url,
            "file_key": file_key,
            "mode": "public_embed",
        }

    def _parse_with_api(self, url: str, file_key: str, node_id: str) -> dict:
        """
        Full API mode with Figma personal access token.
        Extracts: color styles, text styles, component names, metadata.
        """
        try:
            import requests

            headers = {"X-Figma-Token": self.figma_token}
            base = "https://api.figma.com/v1"

            # File metadata
            resp = requests.get(f"{base}/files/{file_key}", headers=headers, timeout=20)
            if resp.status_code == 403:
                return {"text": "", "error": "Figma token invalid or file access denied.", "modality": "figma"}
            if resp.status_code != 200:
                return {"text": "", "error": f"Figma API error: {resp.status_code}", "modality": "figma"}

            data = resp.json()
            text_parts = []

            # Basic metadata
            doc = data.get("document", {})
            text_parts.append(f"PROJECT NAME: {data.get('name', 'Unknown')}")
            text_parts.append(f"LAST MODIFIED: {data.get('lastModified', '')}")

            # Color styles
            styles = data.get("styles", {})
            colors = []
            texts = []
            for style_id, style in styles.items():
                if style.get("styleType") == "FILL":
                    colors.append(style.get("name", ""))
                elif style.get("styleType") == "TEXT":
                    texts.append(style.get("name", ""))

            if colors:
                text_parts.append(f"COLOR STYLES: {', '.join(colors)}")
            if texts:
                text_parts.append(f"TEXT STYLES: {', '.join(texts)}")

            # Extract text content and component names recursively
            all_texts = []
            all_components = []
            self._traverse_nodes(doc, all_texts, all_components)

            if all_components:
                text_parts.append(f"COMPONENTS: {', '.join(list(set(all_components))[:20])}")
            if all_texts:
                unique_texts = list(dict.fromkeys(all_texts))[:30]
                text_parts.append(f"TEXT CONTENT:\n" + "\n".join(f"- {t}" for t in unique_texts))

            return {
                "text": "\n".join(text_parts),
                "modality": "figma",
                "url": url,
                "file_key": file_key,
                "mode": "api_full",
                "color_styles": colors,
                "text_styles": texts,
            }

        except Exception as e:
            return {"text": "", "error": str(e), "modality": "figma"}

    def _traverse_nodes(self, node: dict, texts: list, components: list, depth: int = 0):
        """Recursively walk Figma document tree."""
        if depth > 6:
            return
        node_type = node.get("type", "")

        if node_type == "COMPONENT":
            name = node.get("name", "")
            if name:
                components.append(name)

        if node_type == "TEXT":
            chars = node.get("characters", "").strip()
            if chars and len(chars) > 3 and len(chars) < 200:
                texts.append(chars)

        for child in node.get("children", []):
            self._traverse_nodes(child, texts, components, depth + 1)

    def _analyze_thumbnail(self, thumbnail_url: str) -> str:
        """Download Figma thumbnail and analyze via Groq vision."""
        try:
            import requests
            from groq import Groq

            resp = requests.get(thumbnail_url, timeout=15)
            if resp.status_code != 200:
                return ""

            content_type = resp.headers.get("content-type", "image/png")
            if "image" not in content_type:
                return ""

            b64 = base64.b64encode(resp.content).decode()
            mime = content_type.split(";")[0].strip()

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
                            {
                                "type": "text",
                                "text": (
                                    "This is a Figma design file thumbnail. "
                                    "Analyze the visual brand identity: color palette, typography, "
                                    "design language, brand personality, target audience, and tone. "
                                    "Be specific about what you observe."
                                ),
                            },
                        ],
                    }
                ],
                max_tokens=600,
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()

        except Exception:
            return ""
