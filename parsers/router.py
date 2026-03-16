"""
Modality Router — Organizational Knowledge Harness Sprint 5
Detects input type and routes to the appropriate parser.
Each parser returns plain text → Extraction Agent always receives text.

Architecture decision (MANGO-inspired): each modality processed separately
before fusion. No modality dominates the graph.

Supported: .txt .md .pdf .pptx .docx image files (jpg/png/gif/webp) URL
"""

import os
import re
from pathlib import Path


def detect_modality(source: str | Path) -> str:
    """Detect input modality from file path or content."""
    if isinstance(source, str) and (source.startswith("http://") or source.startswith("https://")):
        return "url"

    path = Path(source) if not isinstance(source, Path) else source
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        return "text"
    elif suffix == ".pdf":
        return "pdf"
    elif suffix == ".pptx":
        return "pptx"
    elif suffix == ".docx":
        return "docx"
    elif suffix in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        return "image"
    elif suffix in (".mp3", ".mp4", ".wav", ".m4a", ".ogg"):
        return "audio"
    else:
        return "text"


def route(source: str | Path, api_key: str = None) -> dict:
    """
    Route a source to its appropriate parser.
    Returns {"text": str, "modality": str, "source_name": str, "metadata": dict}
    """
    modality = detect_modality(source)

    if modality == "text":
        from parsers.text_parser import TextParser
        return TextParser().parse(source)
    elif modality == "pdf":
        from parsers.pdf_parser import PDFParser
        return PDFParser().parse(source)
    elif modality == "pptx":
        from parsers.pptx_parser import PPTXParser
        return PPTXParser(api_key=api_key).parse(source)
    elif modality == "docx":
        from parsers.docx_parser import DOCXParser
        return DOCXParser().parse(source)
    elif modality == "image":
        from parsers.image_parser import ImageParser
        return ImageParser(api_key=api_key).parse(source)
    elif modality == "url":
        from parsers.url_parser import URLParser
        return URLParser().parse(source)
    elif modality == "audio":
        return {
            "text": "",
            "modality": "audio",
            "source_name": str(source),
            "metadata": {},
            "error": "Audio parsing requires Sprint 5+ implementation with Whisper API",
        }
    else:
        from parsers.text_parser import TextParser
        return TextParser().parse(source)
