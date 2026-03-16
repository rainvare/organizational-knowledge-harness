"""
Image Parser — Sprint 5
Describes images via Gemini Vision → structured text → graph.
Prevents visual modality from being silently dropped.
"""
import base64
import os
from pathlib import Path

IMAGE_PROMPT = """
You are analyzing an image that is part of organizational brand materials.

Describe what you see in structured form:
1. What type of content is this? (logo, product photo, team photo, infographic, etc.)
2. What brand elements are visible? (colors, typography, imagery style)
3. What values or tone does this image communicate?
4. Are there any text elements? Transcribe them exactly.
5. What would be inappropriate to place next to this image?

Be specific and factual. This description will be used to build a knowledge graph.
"""

class ImageParser:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")

    def parse(self, source) -> dict:
        path = Path(source)
        error = None
        text = ""

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            with open(path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            suffix = path.suffix.lower().lstrip(".")
            mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                        "png": "image/png", "gif": "image/gif", "webp": "image/webp"}
            mime_type = mime_map.get(suffix, "image/jpeg")

            response = model.generate_content([
                IMAGE_PROMPT,
                {"mime_type": mime_type, "data": image_data}
            ])
            text = response.text

        except ImportError:
            error = "Image parsing requires: pip install google-generativeai"
        except Exception as e:
            error = str(e)

        return {
            "text": text,
            "modality": "image",
            "source_name": path.name,
            "metadata": {"file_size": path.stat().st_size if path.exists() else 0},
            **({"error": error} if error else {}),
        }
