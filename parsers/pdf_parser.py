"""parsers/pdf_parser.py"""


class PDFParser:
    def parse(self, path: str) -> dict:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(path)
            pages = []
            for page in doc:
                pages.append(page.get_text())
            text = "\n".join(pages)
            return {"text": text, "modality": "pdf", "pages": len(doc)}
        except ImportError:
            return {"text": "", "error": "PyMuPDF not installed. Run: pip install PyMuPDF"}
        except Exception as e:
            return {"text": "", "error": str(e)}
