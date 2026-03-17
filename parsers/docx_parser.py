"""parsers/docx_parser.py"""


class DOCXParser:
    def parse(self, path: str) -> dict:
        try:
            from docx import Document
            doc = Document(path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return {"text": "\n".join(paragraphs), "modality": "docx"}
        except ImportError:
            return {"text": "", "error": "python-docx not installed"}
        except Exception as e:
            return {"text": "", "error": str(e)}
