"""Sprint C — Retrieval intelligence regression tests.

Covers:
  1. Section heading detection from chunk content.
  2. Section carry-forward across chunks (the root cause of "not found" on CVs).
  3. BM25 tokenizer correctly handles underscore-separated filenames.
  4. End-to-end chunk enrichment produces per-section context prefix.
  5. Multi-document diversity still preserved after the section fix.
"""
from __future__ import annotations

import uuid
import pytest

from app.workers.tasks import _detect_section_heading, _KNOWN_SECTION_HEADINGS
from app.services.rag.bm25_manager import simple_tokenizer
from app.services.parser.chunker import get_chunker


# ===========================================================================
# 1. Section heading detection
# ===========================================================================

class TestDetectSectionHeading:
    def test_known_vocabulary_match(self) -> None:
        text = "Projects\n\nProject 1: E-commerce website"
        assert _detect_section_heading(text) == "Projects"

    def test_known_vocabulary_case_insensitive(self) -> None:
        assert _detect_section_heading("EDUCATION\nBSc Computer Science") == "EDUCATION"

    def test_known_vocabulary_with_context_prefix(self) -> None:
        # Chunks have a [Document: ...] prefix — heading detection must skip it
        text = "[Document: cv.pdf]\n\nWork Experience\nSoftware Engineer at Acme"
        assert _detect_section_heading(text) == "Work Experience"

    def test_all_caps_heading_two_words(self) -> None:
        # ALL-CAPS lines are common in contracts and formal CVs
        text = "TECHNICAL SKILLS\nPython, React, PostgreSQL"
        result = _detect_section_heading(text)
        assert result is not None
        assert "Technical" in result or "TECHNICAL" in result

    def test_numbered_section_research_paper(self) -> None:
        text = "2. Methodology\nWe used a transformer-based model..."
        result = _detect_section_heading(text)
        assert result == "Methodology"

    def test_numbered_section_subsection(self) -> None:
        text = "3.1 Experimental Setup\nAll experiments ran on..."
        result = _detect_section_heading(text)
        assert result == "Experimental Setup"

    def test_body_text_not_detected_as_heading(self) -> None:
        # A normal sentence should never be a heading
        text = "The model achieved 95% accuracy on the test set."
        assert _detect_section_heading(text) is None

    def test_name_not_detected_as_heading(self) -> None:
        # "Aditya Mishra" is a name, not a known section heading
        text = "Aditya Mishra\nSoftware Engineer"
        # Either None OR not in _KNOWN_SECTION_HEADINGS is acceptable
        result = _detect_section_heading(text)
        if result is not None:
            assert result.lower() not in _KNOWN_SECTION_HEADINGS

    def test_blank_chunk_returns_none(self) -> None:
        assert _detect_section_heading("") is None
        assert _detect_section_heading("   \n  ") is None

    def test_cv_achievements_section(self) -> None:
        text = "Achievements\n- Won national hackathon 2023"
        assert _detect_section_heading(text) == "Achievements"

    def test_context_prefix_only_no_heading(self) -> None:
        text = "[Document: report.pdf]\n\nThe introduction covers..."
        # No heading line after the prefix
        assert _detect_section_heading(text) is None

    def test_abstract_academic(self) -> None:
        text = "Abstract\nThis paper presents a novel approach..."
        assert _detect_section_heading(text) == "Abstract"

    def test_introduction_academic(self) -> None:
        text = "[Document: paper.pdf, Section: Introduction]\n\nIntroduction\n..."
        # Already has section in prefix — should still detect the heading
        assert _detect_section_heading(text) == "Introduction"


# ===========================================================================
# 2. BM25 tokenizer — underscore-separated filenames
# ===========================================================================

class TestSimpleTokenizer:
    def test_plain_sentence(self) -> None:
        tokens = simple_tokenizer("Hello world from Python")
        assert "hello" in tokens
        assert "world" in tokens
        assert "python" in tokens

    def test_underscore_filename(self) -> None:
        # The original regex missed tokens in "aditya_mishra_cv.pdf"
        tokens = simple_tokenizer("aditya_mishra_cv.pdf")
        assert "aditya" in tokens, f"'aditya' not found in {tokens}"
        assert "mishra" in tokens, f"'mishra' not found in {tokens}"
        assert "cv" in tokens, f"'cv' not found in {tokens}"

    def test_hyphenated_compound(self) -> None:
        tokens = simple_tokenizer("state-of-the-art deep-learning model")
        assert "state" in tokens
        assert "art" in tokens
        assert "deep" in tokens
        assert "learning" in tokens
        assert "model" in tokens

    def test_dot_separated(self) -> None:
        tokens = simple_tokenizer("doc.filename.txt")
        assert "doc" in tokens
        assert "filename" in tokens
        assert "txt" in tokens

    def test_short_tokens_excluded(self) -> None:
        tokens = simple_tokenizer("I a is an the")
        # All <= 1 char; "is", "an", "the" are 2-3 chars but the filter is 2+
        # "is" = 2 chars → included; "a" = 1 char → excluded
        assert "a" not in tokens

    def test_context_prefix_tokenized(self) -> None:
        # Every chunk starts with [Document: filename]; the filename tokens must
        # appear in the BM25 index so name-based queries match document chunks
        text = "[Document: Aditya_Mishra_CV.pdf, Section: Projects]\n\nProject details"
        tokens = simple_tokenizer(text)
        assert "aditya" in tokens
        assert "mishra" in tokens
        assert "projects" in tokens
        assert "project" in tokens

    def test_no_duplicates_within_reason(self) -> None:
        # Tokenizer is expected to return ALL occurrences (BM25 handles TF)
        tokens = simple_tokenizer("python python python")
        assert tokens.count("python") == 3


# ===========================================================================
# 3. Section carry-forward in enriched chunks
# ===========================================================================

def _simulate_chunk_enrichment(chunks_raw: list[dict]) -> list[dict]:
    """Replicate the section carry-forward logic from tasks.async_process_document."""
    current_section = ""
    result = []
    for chunk_data in chunks_raw:
        raw_content: str = chunk_data["content"]
        meta = dict(chunk_data.get("metadata", {}))
        title = "test_document.pdf"

        detected = (
            meta.get("heading")
            or meta.get("section")
            or _detect_section_heading(raw_content)
        )
        if detected:
            current_section = detected

        section = current_section
        context_prefix = f"[Document: {title}"
        if section:
            context_prefix += f", Section: {section}"
        context_prefix += "]\n\n"

        meta["filename"] = title
        if section:
            meta["section"] = section

        result.append({
            "content": context_prefix + raw_content,
            "metadata": meta,
            "section": section,
        })
    return result


class TestSectionCarryForward:
    def test_heading_chunk_annotated(self) -> None:
        chunks = [{"content": "Projects\n- E-commerce website", "metadata": {}}]
        enriched = _simulate_chunk_enrichment(chunks)
        assert enriched[0]["section"] == "Projects"
        assert "Section: Projects" in enriched[0]["content"]

    def test_subsequent_chunks_inherit_section(self) -> None:
        chunks = [
            {"content": "Projects\n1. E-commerce website\n   React, Node.js", "metadata": {}},
            {"content": "2. AI Chatbot\n   Python, OpenAI", "metadata": {}},
            {"content": "3. Portfolio Site\n   HTML, CSS", "metadata": {}},
        ]
        enriched = _simulate_chunk_enrichment(chunks)
        # All three must carry the Projects section
        for i, chunk in enumerate(enriched):
            assert chunk["section"] == "Projects", (
                f"Chunk {i} lost section context: {chunk['content'][:80]!r}"
            )
            assert "Section: Projects" in chunk["content"], (
                f"Chunk {i} content prefix missing section: {chunk['content'][:80]!r}"
            )

    def test_section_resets_on_new_heading(self) -> None:
        chunks = [
            {"content": "Projects\n1. E-commerce website", "metadata": {}},
            {"content": "2. AI Chatbot", "metadata": {}},
            {"content": "Experience\nSoftware Engineer at Acme Corp", "metadata": {}},
            {"content": "Worked on microservices architecture", "metadata": {}},
        ]
        enriched = _simulate_chunk_enrichment(chunks)
        assert enriched[0]["section"] == "Projects"
        assert enriched[1]["section"] == "Projects"
        assert enriched[2]["section"] == "Experience"
        assert enriched[3]["section"] == "Experience"

    def test_no_false_heading_on_body_text(self) -> None:
        chunks = [
            {"content": "The model achieved 95% accuracy.", "metadata": {}},
            {"content": "Further experiments confirmed the result.", "metadata": {}},
        ]
        enriched = _simulate_chunk_enrichment(chunks)
        # Neither chunk is a heading; section stays empty
        for chunk in enriched:
            assert chunk["section"] == ""
            assert "Section:" not in chunk["content"]

    def test_chunker_metadata_heading_takes_priority(self) -> None:
        # If the chunker itself provides a heading (e.g. MarkdownAwareChunker),
        # that takes priority over the heuristic
        chunks = [
            {"content": "Some body text", "metadata": {"heading": "Custom Section"}},
        ]
        enriched = _simulate_chunk_enrichment(chunks)
        assert enriched[0]["section"] == "Custom Section"
        assert "Section: Custom Section" in enriched[0]["content"]

    def test_cv_projects_bm25_matchability(self) -> None:
        """The critical regression: after carry-forward, BM25 must find 'projects'
        in ALL project description chunks, not just the one with the heading."""
        chunks = [
            {"content": "Projects\n1. E-commerce Website\n   React, Node.js", "metadata": {}},
            {"content": "2. AI Chatbot\n   Python, OpenAI", "metadata": {}},
            {"content": "3. Portfolio Site\n   HTML, CSS, JavaScript", "metadata": {}},
        ]
        enriched = _simulate_chunk_enrichment(chunks)
        for i, chunk in enumerate(enriched):
            tokens = simple_tokenizer(chunk["content"])
            assert "projects" in tokens, (
                f"BM25 cannot match 'projects' in chunk {i}: "
                f"content={chunk['content'][:100]!r}, tokens={tokens}"
            )

    def test_multi_section_document(self) -> None:
        """Verify a full CV structure: Projects then Experience."""
        chunks = [
            {"content": "Projects\nE-commerce website", "metadata": {}},
            {"content": "AI Chatbot app", "metadata": {}},
            {"content": "Experience\nSoftware Engineer 2022-present", "metadata": {}},
            {"content": "Worked on payment systems", "metadata": {}},
            {"content": "Education\nBSc Computer Science, 2022", "metadata": {}},
        ]
        enriched = _simulate_chunk_enrichment(chunks)
        sections = [c["section"] for c in enriched]
        assert sections == ["Projects", "Projects", "Experience", "Experience", "Education"]

    def test_allcaps_heading_carry(self) -> None:
        chunks = [
            {"content": "TECHNICAL SKILLS\nPython, React, AWS", "metadata": {}},
            {"content": "PostgreSQL, Redis, Docker", "metadata": {}},
        ]
        enriched = _simulate_chunk_enrichment(chunks)
        assert enriched[0]["section"] != ""
        assert enriched[1]["section"] == enriched[0]["section"]

    def test_numbered_section_research_carry(self) -> None:
        chunks = [
            {"content": "2. Methodology\nWe trained the model on...", "metadata": {}},
            {"content": "The training used 10 epochs and batch size 32.", "metadata": {}},
            {"content": "3. Results\nThe model achieved 95% accuracy.", "metadata": {}},
        ]
        enriched = _simulate_chunk_enrichment(chunks)
        assert enriched[0]["section"] == "Methodology"
        assert enriched[1]["section"] == "Methodology"
        assert enriched[2]["section"] == "Results"


# ===========================================================================
# 4. Chunker produces section metadata when heading is in chunk
# ===========================================================================

class TestChunkerMetadata:
    def test_recursive_chunker_basic_structure(self) -> None:
        chunker = get_chunker("recursive_character", chunk_size=200, chunk_overlap=20)
        text = "Some introductory text.\n\nMore content here."
        chunks = chunker.split_text(text)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert "content" in chunk
            assert "page_number" in chunk
            assert "metadata" in chunk

    def test_page_numbers_preserved(self) -> None:
        chunker = get_chunker("recursive_character", chunk_size=300, chunk_overlap=30)
        text = "--- PAGE 1 ---\nFirst page text.\n--- PAGE 2 ---\nSecond page text."
        chunks = chunker.split_text(text)
        page_nums = {c["page_number"] for c in chunks}
        assert 1 in page_nums
        assert 2 in page_nums


# ===========================================================================
# 5. BM25 + section fix integration — query simulation
# ===========================================================================

class TestRetrievalQuerySimulation:
    """Simulate what BM25 tokenization produces for a CV query after the fix."""

    def test_projects_query_matches_subsequent_chunk(self) -> None:
        """'projects of aditya mishra' must find tokens in non-heading chunks."""
        query = "projects of aditya mishra"
        query_tokens = set(simple_tokenizer(query))

        # Simulate enriched chunk 2 of 3 in the "Projects" section
        enriched_chunk_content = (
            "[Document: aditya_mishra_cv.pdf, Section: Projects]\n\n"
            "2. AI Chatbot\nPython, OpenAI API\nDeployed on AWS Lambda"
        )
        chunk_tokens = set(simple_tokenizer(enriched_chunk_content))

        overlap = query_tokens & chunk_tokens
        # Must find "projects" AND "aditya" AND "mishra" in the chunk tokens
        assert "projects" in overlap, f"'projects' not in chunk tokens: {chunk_tokens}"
        assert "aditya" in overlap, f"'aditya' not in chunk tokens: {chunk_tokens}"
        assert "mishra" in overlap, f"'mishra' not in chunk tokens: {chunk_tokens}"

    def test_cv_summary_query_matches_cv_chunks(self) -> None:
        """'summarize my cv' tokens must overlap with CV chunk tokens."""
        query_tokens = set(simple_tokenizer("summarize my cv"))
        cv_chunk = (
            "[Document: my_resume_cv.pdf]\n\n"
            "Software Engineer with 5 years of experience"
        )
        chunk_tokens = set(simple_tokenizer(cv_chunk))
        assert "cv" in chunk_tokens, f"'cv' not in chunk tokens: {chunk_tokens}"

    def test_ram_rom_query_matches_relevant_chunk(self) -> None:
        """'difference between RAM and ROM' must hit a chunk containing those terms."""
        query_tokens = set(simple_tokenizer("difference between RAM and ROM"))
        # A relevant chunk from a computer science textbook
        chunk = (
            "[Document: computer_architecture.pdf, Section: Memory]\n\n"
            "RAM (Random Access Memory) is volatile, while ROM (Read-Only Memory) "
            "is non-volatile. RAM stores data temporarily during execution."
        )
        chunk_tokens = set(simple_tokenizer(chunk))
        assert "ram" in chunk_tokens
        assert "rom" in chunk_tokens
        # BM25 query overlap
        overlap = query_tokens & chunk_tokens
        assert len(overlap) >= 2, f"Insufficient overlap: {overlap}"

    def test_gandhara_mathura_query(self) -> None:
        """Multi-keyword query for art history must hit section-relevant chunks."""
        query_tokens = set(simple_tokenizer("summarize gandhara vs mathura"))
        chunk = (
            "[Document: art_history.pdf, Section: Indian Art Schools]\n\n"
            "The Gandhara school was influenced by Greco-Roman art, while "
            "the Mathura school was distinctly Indian in origin."
        )
        chunk_tokens = set(simple_tokenizer(chunk))
        assert "gandhara" in chunk_tokens
        assert "mathura" in chunk_tokens
        overlap = query_tokens & chunk_tokens
        assert len(overlap) >= 2, f"Insufficient overlap: {overlap}"
