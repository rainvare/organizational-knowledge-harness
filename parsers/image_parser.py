"""parsers/image_parser.py — Describes images via Groq vision (llama-3.2-11b-vision-preview)."""
import base64
from pathlib import Path


class ImageParser:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def parse(self, path: str) -> dict:
        try:
            from groq import Groq
            img_data = Path(path).read_bytes()
            b64 = base64.b64encode(img_data).decode()
            suffix = Path(path).suffix.lower().lstrip(".")
            mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                    "webp": "image/webp", "gif": "image/gif"}.get(suffix, "image/jpeg")

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
                                "text": "Describe in detail what you see in this image, especially any text, brand elements, visual style, colors, tone, and messaging. Be precise and exhaustive.",
                            },
                        ],
                    }
                ],
                max_tokens=1000,
            )
            return {"text": response.choices[0].message.content, "modality": "image"}
        except Exception as e:
            return {"text": "", "error": str(e)}
