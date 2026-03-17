"""
parsers/router.py
Sprint 5+: Detects file modality and routes to the appropriate parser.
Supports: text, PDF, PPTX, DOCX, image, URL (generic / Behance / Figma / Dribbble)
"""
from pathlib import Path


MODALITY_MAP = {
    ".txt": "text",
    ".md": "text",
    ".pdf": "pdf",
    ".pptx": "pptx",
    ".ppt": "pptx",
    ".docx": "docx",
    ".doc": "docx",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".webp": "image",
    ".gif": "image",
}

URL_TYPE_LABELS = {
    "behance": "Behance / portfolio visual",
    "figma": "Figma (public embed)",
    "dribbble": "Dribbble / portfolio visual",
    "pinterest": "Pinterest / visual board",
    "generic": "URL genérica",
}


def detect_modality(path: Path) -> str:
    return MODALITY_MAP.get(path.suffix.lower(), "text")


def detect_url_type(url: str) -> str:
    from parsers.url_parser import detect_url_type as _detect
    return _detect(url)


def route(path: Path, api_key: str = "") -> dict:
    modality = detect_modality(path)
    if modality == "text":
        return {"text": path.read_text(encoding="utf-8", errors="replace"), "modality": "text"}
    elif modality == "pdf":
        from parsers.pdf_parser import PDFParser
        return PDFParser().parse(str(path))
    elif modality == "pptx":
        from parsers.pptx_parser import PPTXParser
        return PPTXParser(api_key=api_key).parse(str(path))
    elif modality == "docx":
        from parsers.docx_parser import DOCXParser
        return DOCXParser().parse(str(path))
    elif modality == "image":
        from parsers.image_parser import ImageParser
        return ImageParser(api_key=api_key).parse(str(path))
    return {"text": "", "error": f"Unknown modality for {path}"}


def route_url(url: str, api_key: str = "", figma_token: str = "") -> dict:
    """Route a URL to the appropriate specialized parser."""
    from parsers.url_parser import URLParser, detect_url_type

    url_type = detect_url_type(url)

    if url_type == "behance":
        from parsers.behance_parser import BehanceParser
        return BehanceParser(api_key=api_key).parse(url)

    if url_type == "figma":
        from parsers.figma_parser import FigmaParser
        return FigmaParser(api_key=api_key, figma_token=figma_token).parse(url)

    if url_type in ("dribbble", "pinterest"):
        from parsers.behance_parser import BehanceParser
        return BehanceParser(api_key=api_key).parse(url)

    return URLParser(api_key=api_key)._generic_fetch(url)
