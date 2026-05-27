"""Document parsing and chunking utilities."""

import io
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentParser:
    """Parse various document formats into raw text."""

    async def parse(self, file_bytes: bytes, filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

        if ext == "pdf":
            return self._parse_pdf(file_bytes)
        elif ext in ("docx", "doc"):
            return self._parse_docx(file_bytes)
        else:
            return self._parse_txt(file_bytes)

    def _parse_pdf(self, content: bytes) -> str:
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            return "\n\n".join(text_parts)
        except Exception:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(content))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    def _parse_docx(self, content: bytes) -> str:
        from docx import Document
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    def _parse_txt(self, content: bytes) -> str:
        return content.decode("utf-8", errors="replace")


class Chunker:
    """Split text into chunks based on document type strategy."""

    def chunk(self, text: str, strategy: str = "resume") -> List[str]:
        if not text or not text.strip():
            return []

        if strategy == "question_bank":
            return self._chunk_questions(text)
        elif strategy == "jd":
            return self._chunk_by_sections(text)
        else:
            return self._chunk_recursive(text)

    def _chunk_recursive(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", "。", ".", " ", ""],
        )
        return splitter.split_text(text)

    def _chunk_questions(self, text: str) -> List[str]:
        """Split by question numbering patterns."""
        import re
        parts = re.split(r"\n(?=\d+[.、)）]|\n(?=[Qq]uestion\s*\d+))", text)
        chunks = []
        for part in parts:
            part = part.strip()
            if part:
                if len(part) > 1000:
                    chunks.extend(self._chunk_recursive(part, chunk_size=800))
                else:
                    chunks.append(part)
        return chunks

    def _chunk_by_sections(self, text: str) -> List[str]:
        """Split JD by apparent section boundaries."""
        import re
        sections = re.split(r"\n(?=[#【\[]|(?:第[一二三四五六七八九十]).*(?:章|节|部分)])", text)
        chunks = []
        for section in sections:
            section = section.strip()
            if section:
                if len(section) > 800:
                    chunks.extend(self._chunk_recursive(section, chunk_size=600))
                else:
                    chunks.append(section)
        return chunks
