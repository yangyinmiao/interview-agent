import pytest
from app.services.document_parser import DocumentParser, Chunker


class TestDocumentParser:
    @pytest.mark.asyncio
    async def test_parse_txt(self):
        content = b"Hello World\nThis is a test"
        result = await DocumentParser().parse(content, "test.txt")
        assert result == "Hello World\nThis is a test"

    @pytest.mark.asyncio
    async def test_parse_unknown_extension_falls_through_to_txt(self):
        content = b"simple text"
        result = await DocumentParser().parse(content, "test.xyz")
        assert result == "simple text"

    @pytest.mark.asyncio
    async def test_parse_txt_utf8_with_special_chars(self):
        content = "简历内容：张三\n技能：Python, React".encode("utf-8")
        result = await DocumentParser().parse(content, "test.txt")
        assert "张三" in result


class TestChunker:
    def test_chunk_resume_strategy(self):
        text = "Section 1: Experience\n\n" + ("Worked at Acme Corp. " * 100)
        chunks = Chunker().chunk(text, "resume")
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, str)
            assert len(chunk) > 0

    def test_chunk_question_bank_strategy(self):
        text = "1. What is Python?\nAnswer: A programming language.\n\n" * 5
        chunks = Chunker().chunk(text, "question_bank")
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, str)

    def test_chunk_jd_strategy(self):
        text = "Job Title: Engineer\n\nRequirements:\n- Python\n- Docker\n\n" + ("Details here. " * 50)
        chunks = Chunker().chunk(text, "jd")
        assert len(chunks) > 0

    def test_chunk_empty_text(self):
        chunks = Chunker().chunk("", "resume")
        assert chunks == []

    def test_chunk_short_text(self):
        chunks = Chunker().chunk("Short text", "resume")
        assert len(chunks) >= 1
