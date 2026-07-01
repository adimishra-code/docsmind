from __future__ import annotations

import csv
import io
import re
from typing import Any

import docx
import pdfplumber
import pypdfium2 as pdfium
from pptx import Presentation
from PIL import Image
import pytesseract
from langdetect import detect, LangDetectException

from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.services.parser.base import DocumentParserInterface

logger = get_logger(__name__)


# --------------------------------------------------------------------------- #
# OCR Helper (Tesseract + pypdfium2 Wrapper)
# --------------------------------------------------------------------------- #
def perform_ocr_on_pdf_page(file_content: bytes, page_num: int) -> str:
    """Render PDF page to image and perform OCR using Tesseract."""
    logger.info("Executing OCR on scanned PDF page", page_number=page_num)
    try:
        # Load PDF using pypdfium2 (pure Python/precompiled wrapper)
        doc = pdfium.PdfDocument(io.BytesIO(file_content))
        page = doc[page_num - 1]
        
        # Render page to bitmap and convert to PIL Image
        bitmap = page.render(scale=2)
        image = bitmap.to_pil()
        
        # Run OCR
        text = pytesseract.image_to_string(image)
        return text
    except Exception as exc:
        logger.exception("OCR processing failed for page", page_number=page_num, error=str(exc))
        return ""


# --------------------------------------------------------------------------- #
# PDF Parser (with pdfplumber Table Extraction & Tesseract OCR Fallback)
# --------------------------------------------------------------------------- #
class PDFParser(DocumentParserInterface):
    """Production PDF processing engine.

    Uses pdfplumber for layout-aware text and table extraction.
    Formats tables as markdown tables.
    Automatically detects scanned/empty pages and executes OCR.
    """

    def parse(self, file_content: bytes) -> tuple[str, dict[str, Any]]:
        logger.info("Parsing PDF document")
        extracted_text_blocks = []
        headings = []
        tables_metadata = []
        pages_count = 0
        ocr_triggered = False

        # 1. First Pass: Attempt layout text extraction using pdfplumber
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            pages_count = len(pdf.pages)
            for page_num, pdf_page in enumerate(pdf.pages):
                text = pdf_page.extract_text() or ""
                extracted_text_blocks.append((page_num, text))

        # Check total text density. If average characters per page < 100, trigger OCR fallback
        total_chars = sum(len(text) for _, text in extracted_text_blocks)
        if pages_count > 0 and (total_chars / pages_count) < 100:
            logger.warn("Low text density detected. Triggering OCR pipeline.", char_count=total_chars)
            ocr_triggered = True
            extracted_text_blocks.clear()
            for page_num in range(pages_count):
                ocr_text = perform_ocr_on_pdf_page(file_content, page_num + 1)
                extracted_text_blocks.append((page_num, ocr_text))

        # 2. Extract Tables using pdfplumber and append as Markdown tables
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                for page_num, pdf_page in enumerate(pdf.pages):
                    tables = pdf_page.extract_tables()
                    if tables:
                        for table_index, table in enumerate(tables):
                            markdown_table = self._format_table_as_markdown(table)
                            if markdown_table:
                                # Inject table markdown into the page text block
                                page_text = next((t for p, t in extracted_text_blocks if p == page_num), "")
                                updated_text = page_text + "\n\n### Extracted Table\n\n" + markdown_table
                                
                                # Update block
                                for i, (p, _) in enumerate(extracted_text_blocks):
                                    if p == page_num:
                                        extracted_text_blocks[i] = (page_num, updated_text)
                                
                                tables_metadata.append({
                                    "page": page_num + 1,
                                    "table_index": table_index,
                                    "rows_count": len(table),
                                })
        except Exception as exc:
            logger.warn("Table extraction failed or bypassed", error=str(exc))

        # Merge all pages into final structured text string
        final_text_parts = []
        for page_num, text in extracted_text_blocks:
            final_text_parts.append(f"--- PAGE {page_num + 1} ---\n{text}")

        metadata = {
            "pages": pages_count,
            "headings": headings,
            "tables": tables_metadata,
            "ocr_applied": ocr_triggered,
        }

        return "\n\n".join(final_text_parts), metadata

    def _format_table_as_markdown(self, table: list[list[str | None]]) -> str:
        """Convert a list-of-lists table into a raw GFM Markdown table string."""
        if not table or not table[0]:
            return ""

        # Filter out empty or fully null rows
        valid_rows = []
        for row in table:
            cleaned_row = [str(cell or "").strip().replace("\n", " ") for cell in row]
            if any(cleaned_row):
                valid_rows.append(cleaned_row)

        if not valid_rows:
            return ""

        cols_count = len(valid_rows[0])
        headers = valid_rows[0]
        rows = valid_rows[1:]

        # Create separator
        separator = ["---"] * cols_count

        markdown_lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(separator) + " |",
        ]
        for row in rows:
            # Ensure row length matches header length
            row_cells = row + [""] * (cols_count - len(row))
            markdown_lines.append("| " + " | ".join(row_cells[:cols_count]) + " |")

        return "\n".join(markdown_lines)


# --------------------------------------------------------------------------- #
# DOCX Parser
# --------------------------------------------------------------------------- #
class DocxParser(DocumentParserInterface):
    """Parses Word files (*.docx) maintaining paragraph structures."""

    def parse(self, file_content: bytes) -> tuple[str, dict[str, Any]]:
        logger.info("Parsing DOCX document")
        doc = docx.Document(io.BytesIO(file_content))
        text_runs = []
        headings = []

        for p_idx, p in enumerate(doc.paragraphs):
            text = p.text.strip()
            if not text:
                continue

            # Detect headings by style
            if p.style.name.startswith("Heading"):
                headings.append({"paragraph_index": p_idx, "text": text, "style": p.style.name})

            text_runs.append(text)

        # Basic table parsing
        tables_count = len(doc.tables)
        for t_idx, table in enumerate(doc.tables):
            table_text = []
            for row in table.rows:
                row_text = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                table_text.append("| " + " | ".join(row_text) + " |")
            if table_text:
                text_runs.append(f"\n\n### Document Table\n\n" + "\n".join(table_text))

        final_text = "\n\n".join(text_runs)
        metadata = {
            "paragraphs_count": len(doc.paragraphs),
            "headings": headings,
            "tables_count": tables_count,
        }
        return final_text, metadata


# --------------------------------------------------------------------------- #
# PowerPoint Parser
# --------------------------------------------------------------------------- #
class PptxParser(DocumentParserInterface):
    """Parses PowerPoint presentations (*.pptx) slide-by-slide."""

    def parse(self, file_content: bytes) -> tuple[str, dict[str, Any]]:
        logger.info("Parsing PPTX document")
        prs = Presentation(io.BytesIO(file_content))
        slides_text = []

        for slide_idx, slide in enumerate(prs.slides):
            slide_runs = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_runs.append(shape.text.strip())

            combined_slide_text = "\n".join(slide_runs)
            slides_text.append(f"--- SLIDE {slide_idx + 1} ---\n{combined_slide_text}")

        final_text = "\n\n".join(slides_text)
        metadata = {
            "slides_count": len(prs.slides),
        }
        return final_text, metadata


# --------------------------------------------------------------------------- #
# CSV Parser
# --------------------------------------------------------------------------- #
class CsvParser(DocumentParserInterface):
    """Parses CSV files and formats rows as Markdown tables."""

    def parse(self, file_content: bytes) -> tuple[str, dict[str, Any]]:
        logger.info("Parsing CSV document")
        try:
            decoded_content = file_content.decode("utf-8")
        except UnicodeDecodeError:
            decoded_content = file_content.decode("latin-1")

        csv_reader = csv.reader(io.StringIO(decoded_content))
        rows = list(csv_reader)

        if not rows:
            return "", {"rows_count": 0, "cols_count": 0}

        cols_count = len(rows[0])
        headers = rows[0]
        body_rows = rows[1:]

        # Format as standard GFM markdown table
        separator = ["---"] * cols_count
        markdown_lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(separator) + " |",
        ]
        for r in body_rows:
            cleaned_row = [cell.strip().replace("\n", " ") for cell in r]
            row_cells = cleaned_row + [""] * (cols_count - len(cleaned_row))
            markdown_lines.append("| " + " | ".join(row_cells[:cols_count]) + " |")

        final_text = "\n".join(markdown_lines)
        metadata = {
            "rows_count": len(rows),
            "cols_count": cols_count,
        }
        return final_text, metadata


# --------------------------------------------------------------------------- #
# Plain Text & Markdown Parser
# --------------------------------------------------------------------------- #
class TxtParser(DocumentParserInterface):
    """Parses plain text and Markdown files, detecting heading layouts."""

    def parse(self, file_content: bytes) -> tuple[str, dict[str, Any]]:
        logger.info("Parsing TXT/MD document")
        try:
            text = file_content.decode("utf-8")
        except UnicodeDecodeError:
            text = file_content.decode("latin-1")

        # Parse structural Markdown headings using regex
        headings = []
        for line_num, line in enumerate(text.splitlines()):
            match = re.match(r"^(#+)\s+(.*)$", line)
            if match:
                headings.append({
                    "line": line_num + 1,
                    "level": len(match.group(1)),
                    "text": match.group(2).strip(),
                })

        metadata = {
            "lines_count": len(text.splitlines()),
            "headings": headings,
        }
        return text, metadata


# --------------------------------------------------------------------------- #
# XLSX Parser (Microsoft Excel)
# --------------------------------------------------------------------------- #
class XlsxParser(DocumentParserInterface):
    """Parses Excel files (*.xlsx) sheet-by-sheet using openpyxl."""

    def parse(self, file_content: bytes) -> tuple[str, dict[str, Any]]:
        logger.info("Parsing XLSX document")
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(file_content), data_only=True)
        sheets_text = []
        sheets_count = 0
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = []
            for row in ws.iter_rows(values_only=True):
                cells = [str(c) if c is not None else "" for c in row]
                rows.append(" | ".join(cells))
            if rows:
                sheets_text.append(f"### Sheet: {sheet_name}\n" + "\n".join(rows))
            sheets_count += 1
        wb.close()
        final_text = "\n\n".join(sheets_text)
        metadata = {"sheets_count": sheets_count, "sheet_names": wb.sheetnames}
        return final_text, metadata


# --------------------------------------------------------------------------- #
# HTML Parser
# --------------------------------------------------------------------------- #
class HtmlParser(DocumentParserInterface):
    """Parses HTML files by stripping tags and extracting visible text."""

    def parse(self, file_content: bytes) -> tuple[str, dict[str, Any]]:
        logger.info("Parsing HTML document")
        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.parts: list[str] = []
                self.skip = False

            def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
                if tag in ("script", "style"):
                    self.skip = True

            def handle_endtag(self, tag: str) -> None:
                if tag in ("script", "style"):
                    self.skip = False
                if tag in ("p", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"):
                    self.parts.append("\n")

            def handle_data(self, data: str) -> None:
                if not self.skip:
                    stripped = data.strip()
                    if stripped:
                        self.parts.append(stripped + " ")

        try:
            raw = file_content.decode("utf-8")
        except UnicodeDecodeError:
            raw = file_content.decode("latin-1")

        extractor = TextExtractor()
        extractor.feed(raw)
        text = "".join(extractor.parts).strip()
        metadata = {"char_count": len(text)}
        return text, metadata


# --------------------------------------------------------------------------- #
# RTF Parser (Rich Text Format)
# --------------------------------------------------------------------------- #
class RtfParser(DocumentParserInterface):
    """Extracts plain text from RTF files by stripping control sequences."""

    def parse(self, file_content: bytes) -> tuple[str, dict[str, Any]]:
        logger.info("Parsing RTF document")
        try:
            raw = file_content.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            raw = file_content.decode("latin-1", errors="replace")

        text = raw
        text = re.sub(r"\\([a-z]+)(-?\d+)?", "", text)
        text = re.sub(r"\{|\}", "", text)
        text = re.sub(r"\r\n|\r|\n", "\n", text)
        text = re.sub(r" +", " ", text)
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        metadata = {"char_count": len(text)}
        return text, metadata


# --------------------------------------------------------------------------- #
# Parser Router & Language Detection
# --------------------------------------------------------------------------- #
def get_parser_for_file_type(file_type: str) -> DocumentParserInterface:
    """Routing factory returning appropriate parser for file type extensions."""
    ftype = file_type.lower().strip(".")
    if ftype == "pdf":
        return PDFParser()
    elif ftype == "docx":
        return DocxParser()
    elif ftype == "pptx":
        return PptxParser()
    elif ftype == "csv":
        return CsvParser()
    elif ftype in ("txt", "md", "markdown"):
        return TxtParser()
    elif ftype in ("xlsx", "xls"):
        return XlsxParser()
    elif ftype in ("html", "htm"):
        return HtmlParser()
    elif ftype == "rtf":
        return RtfParser()
    else:
        raise ValidationError(f"No parser implemented for file type: {file_type}", code="unsupported_format")


def detect_document_language(text: str) -> str:
    """Execute language detection on document text sample."""
    if not text.strip():
        return "en"
    try:
        # Sample first 2000 characters to reduce detection processing time
        sample = text[:2000]
        return detect(sample)
    except LangDetectException:
        return "en"  # fallback
