"""
Enhanced PDF processing service for PDF RAG Chatbot application.
Provides robust PDF text extraction with metadata and error handling.
"""
import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import re
import csv
import json
import zipfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from io import BytesIO, StringIO
from utils.logger import get_logger


logger = get_logger(__name__)


class _HTMLTextExtractor(HTMLParser):
    """Tiny HTML text extractor used for uploaded HTML documents."""

    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        if tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"p", "div", "li", "tr"}:
            self._parts.append("\n")

    def handle_data(self, data):
        if not self._skip_depth and data.strip():
            self._parts.append(data.strip())

    def get_text(self) -> str:
        return " ".join(self._parts)


class EnhancedPDFService:
    """
    Service for processing PDF files with advanced features.

    Provides text extraction, metadata extraction, and optimization
    for various PDF formats and large documents.
    """

    def __init__(self):
        """Initialize the PDF service"""
        self.supported_formats = [
            '.pdf',
            '.txt', '.md', '.markdown', '.csv', '.tsv', '.json', '.xml', '.html', '.htm',
            '.docx', '.doc', '.xlsx', '.xlsm', '.pptx',
            '.rtf', '.odt', '.ods', '.odp',
            '.xls'
        ]
        self.min_text_length = 20  # Minimum characters to consider a document useful

        # Text extraction settings
        self.preserve_layout = True
        self.extract_images = False  # Set to True for OCR if needed

        logger.info("EnhancedPDFService initialized")

    def extract_text(
        self,
        pdf_path: Optional[str] = None,
        content: Optional[bytes] = None,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
        include_metadata: bool = True
    ) -> str:
        """
        Extract text from a supported document file or binary content.

        Args:
            pdf_path: Path to the PDF file (optional if content provided)
            content: Binary PDF content (optional if pdf_path provided)
            include_metadata: Include document metadata in extracted text

        Returns:
            Extracted text as string
        """
        try:
            source_name = filename
            if pdf_path:
                path = Path(pdf_path)
                if not path.exists():
                    raise Exception(f"Document file not found: {path}")
                content = path.read_bytes()
                source_name = source_name or path.name
            elif not content:
                raise Exception("Either pdf_path or content must be provided")

            suffix = Path(source_name or "").suffix.lower()
            if suffix not in self.supported_formats:
                raise Exception(f"Unsupported file format: {suffix or 'unknown'}")

            if suffix == ".pdf":
                full_text = self._extract_pdf_text(content, include_metadata=include_metadata)
            elif suffix in {".txt", ".md", ".markdown", ".xml"}:
                full_text = self._decode_text(content)
            elif suffix in {".html", ".htm"}:
                full_text = self._extract_html_text(content)
            elif suffix in {".csv", ".tsv"}:
                full_text = self._extract_delimited_text(content, delimiter="\t" if suffix == ".tsv" else ",")
            elif suffix == ".json":
                full_text = self._extract_json_text(content)
            elif suffix == ".docx":
                full_text = self._extract_docx_text(content)
            elif suffix == ".doc":
                full_text = self._extract_legacy_doc_text(content)
            elif suffix in {".xlsx", ".xlsm"}:
                full_text = self._extract_xlsx_text(content)
            elif suffix == ".pptx":
                full_text = self._extract_pptx_text(content)
            elif suffix == ".rtf":
                full_text = self._extract_rtf_text(content)
            elif suffix in {".odt", ".ods", ".odp"}:
                full_text = self._extract_opendocument_text(content)
            elif suffix == ".xls":
                full_text = self._extract_xls_text(content)
            else:
                raise Exception(f"Unsupported file format: {suffix}")

            # Clean up text
            full_text = self._clean_text(full_text)

            # Validate extracted text
            if len(full_text.strip()) < self.min_text_length:
                raise Exception(f"Extracted text too short ({len(full_text)} characters)")

            logger.info(f"Successfully extracted {len(full_text)} characters from {source_name or 'binary content'}")

            return full_text

        except Exception as e:
            logger.error(f"Failed to extract text from document: {e}")
            raise Exception(f"Document text extraction failed: {e}")

    def _extract_pdf_text(self, content: bytes, include_metadata: bool = True) -> str:
        """Extract text from PDF bytes."""
        logger.info("Extracting text from PDF content")
        doc = fitz.open(stream=content, filetype="pdf")
        text_parts = []

        if include_metadata:
            metadata = doc.metadata
            if metadata:
                title = metadata.get('title', '')
                author = metadata.get('author', '')
                subject = metadata.get('subject', '')
                if title:
                    text_parts.append(f"Title: {title}")
                if author:
                    text_parts.append(f"Author: {author}")
                if subject:
                    text_parts.append(f"Subject: {subject}")
                text_parts.append("")

        for page_num, page in enumerate(doc, 1):
            try:
                page_text = self._extract_page_text(page)
                if page_text.strip():
                    text_parts.append(page_text)
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {e}")
                continue

        doc.close()
        return "\n".join(text_parts)

    def _decode_text(self, content: bytes) -> str:
        """Decode text bytes with common encodings."""
        for encoding in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return content.decode("utf-8", errors="ignore")

    def _extract_delimited_text(self, content: bytes, delimiter: str) -> str:
        """Extract readable text from CSV/TSV files."""
        raw = self._decode_text(content)
        output = []
        reader = csv.reader(StringIO(raw), delimiter=delimiter)
        for row_index, row in enumerate(reader, 1):
            cells = [cell.strip() for cell in row if cell and cell.strip()]
            if cells:
                output.append(f"Row {row_index}: " + " | ".join(cells))
        return "\n".join(output)

    def _extract_json_text(self, content: bytes) -> str:
        """Extract text from JSON by pretty-printing it."""
        data = json.loads(self._decode_text(content))
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _extract_html_text(self, content: bytes) -> str:
        """Extract visible-ish text from HTML."""
        parser = _HTMLTextExtractor()
        parser.feed(self._decode_text(content))
        return parser.get_text()

    def _zip_xml_text(self, content: bytes, file_filter) -> str:
        """Extract text nodes from selected XML files inside a zip container."""
        text_parts = []
        with zipfile.ZipFile(BytesIO(content)) as archive:
            for name in archive.namelist():
                if not file_filter(name):
                    continue
                try:
                    root = ET.fromstring(archive.read(name))
                    texts = [node.text for node in root.iter() if node.text and node.text.strip()]
                    if texts:
                        text_parts.append(" ".join(texts))
                except Exception as e:
                    logger.warning(f"Failed to parse XML member {name}: {e}")
        return "\n".join(text_parts)

    def _extract_docx_text(self, content: bytes) -> str:
        """Extract text from DOCX files."""
        return self._zip_xml_text(
            content,
            lambda name: name.startswith("word/") and name.endswith(".xml")
        )

    def _extract_legacy_doc_text(self, content: bytes) -> str:
        """Best-effort text extraction from legacy binary DOC files."""
        decoded = content.decode("utf-16le", errors="ignore")
        runs = re.findall(r"[\x20-\x7E\r\n\t]{4,}", decoded)
        text = "\n".join(run.strip() for run in runs if run.strip())
        if len(text.strip()) >= self.min_text_length:
            return text

        decoded = content.decode("latin-1", errors="ignore")
        runs = re.findall(r"[A-Za-z0-9][A-Za-z0-9\s.,;:!?@#$%&()\[\]{}'\"/\\\-+_=]{5,}", decoded)
        text = "\n".join(run.strip() for run in runs if run.strip())
        if len(text.strip()) >= self.min_text_length:
            return text

        raise Exception("Could not extract readable text from legacy .doc file. Convert it to .docx for best results.")

    def _extract_pptx_text(self, content: bytes) -> str:
        """Extract text from PPTX slides and notes."""
        return self._zip_xml_text(
            content,
            lambda name: name.startswith("ppt/") and name.endswith(".xml")
        )

    def _extract_xlsx_text(self, content: bytes) -> str:
        """Extract workbook text from XLSX/XLSM files."""
        try:
            import openpyxl
        except ImportError as exc:
            raise Exception("Excel extraction requires openpyxl. Install backend requirements.") from exc

        workbook = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)
        parts = []
        for sheet in workbook.worksheets:
            parts.append(f"Sheet: {sheet.title}")
            for row_index, row in enumerate(sheet.iter_rows(values_only=True), 1):
                values = [str(value).strip() for value in row if value is not None and str(value).strip()]
                if values:
                    parts.append(f"Row {row_index}: " + " | ".join(values))
        workbook.close()
        return "\n".join(parts)

    def _extract_xls_text(self, content: bytes) -> str:
        """Extract workbook text from legacy XLS files."""
        try:
            import xlrd
        except ImportError as exc:
            raise Exception("Legacy .xls extraction requires xlrd. Install backend requirements.") from exc

        workbook = xlrd.open_workbook(file_contents=content)
        parts = []
        for sheet in workbook.sheets():
            parts.append(f"Sheet: {sheet.name}")
            for row_index in range(sheet.nrows):
                values = [str(value).strip() for value in sheet.row_values(row_index) if str(value).strip()]
                if values:
                    parts.append(f"Row {row_index + 1}: " + " | ".join(values))
        return "\n".join(parts)

    def _extract_rtf_text(self, content: bytes) -> str:
        """Extract text from RTF files."""
        raw = self._decode_text(content)
        try:
            from striprtf.striprtf import rtf_to_text
            return rtf_to_text(raw)
        except ImportError:
            text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", raw)
            text = re.sub(r"\\[a-zA-Z]+\d* ?", " ", text)
            text = re.sub(r"[{}]", " ", text)
            return text

    def _extract_opendocument_text(self, content: bytes) -> str:
        """Extract text from ODT/ODS/ODP content.xml."""
        with zipfile.ZipFile(BytesIO(content)) as archive:
            if "content.xml" not in archive.namelist():
                raise Exception("OpenDocument file is missing content.xml")
            root = ET.fromstring(archive.read("content.xml"))
            texts = [node.text for node in root.iter() if node.text and node.text.strip()]
            return "\n".join(texts)

    def _extract_page_text(self, page) -> str:
        """
        Extract text from a single page with layout preservation.

        Args:
            page: PyMuPDF page object

        Returns:
            Extracted page text
        """
        if self.preserve_layout:
            # Use get_text("text") for layout preservation
            text = page.get_text("text")
        else:
            # Use simple text extraction
            text = page.get_text()

        return text

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace but preserve newlines
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Remove artifacts
        text = re.sub(r'\f', '\n', text)  # Form feed characters
        text = re.sub(r'\x0c', '\n', text)  # Form feed

        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Remove page numbers and headers/footers (basic detection)
        text = re.sub(r'\n\s*\d+\s*\n', '\n\n', text)  # Standalone page numbers
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)  # Page numbers at line ends

        # Clean up excessive empty lines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        return text.strip()

    def get_pdf_info(self, pdf_path: str) -> Dict[str, Any]:
        """
        Get comprehensive information about a PDF file.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with PDF information
        """
        try:
            pdf_path = Path(pdf_path)

            if not pdf_path.exists():
                raise Exception(f"PDF file not found: {pdf_path}")

            logger.info(f"Getting info for PDF: {pdf_path.name}")

            # Open PDF document
            doc = fitz.open(str(pdf_path))

            # Extract basic information
            info = {
                "filename": pdf_path.name,
                "file_size": pdf_path.stat().st_size,
                "page_count": len(doc),
                "metadata": doc.metadata or {},
                "is_encrypted": doc.is_encrypted,
                "pdf_version": doc.pdf_version,
                "creation_date": doc.metadata.get('creationDate') if doc.metadata else None,
                "modification_date": doc.metadata.get('modDate') if doc.metadata else None
            }

            # Extract text statistics
            try:
                total_text = ""
                for page in doc:
                    total_text += page.get_text()

                info["text_statistics"] = {
                    "total_characters": len(total_text),
                    "total_words": len(total_text.split()),
                    "estimated_reading_time": len(total_text.split()) // 200  # ~200 words/minute
                }
            except Exception as e:
                logger.warning(f"Failed to extract text statistics: {e}")
                info["text_statistics"] = None

            doc.close()

            logger.info(f"Successfully retrieved info for {pdf_path.name}")

            return info

        except Exception as e:
            logger.error(f"Failed to get PDF info: {e}")
            raise Exception(f"Failed to get PDF information: {e}")

    def extract_text_by_pages(self, pdf_path: str) -> List[str]:
        """
        Extract text from PDF organized by pages.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of page texts
        """
        try:
            pdf_path = Path(pdf_path)

            if not pdf_path.exists():
                raise Exception(f"PDF file not found: {pdf_path}")

            logger.info(f"Extracting text by pages from: {pdf_path.name}")

            doc = fitz.open(str(pdf_path))
            pages_text = []

            for page_num, page in enumerate(doc, 1):
                try:
                    page_text = self._extract_page_text(page)
                    page_text = self._clean_text(page_text)

                    if page_text.strip():
                        pages_text.append({
                            "page_number": page_num,
                            "text": page_text,
                            "character_count": len(page_text),
                            "word_count": len(page_text.split())
                        })
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num}: {e}")
                    continue

            doc.close()

            logger.info(f"Extracted text from {len(pages_text)} pages")

            return pages_text

        except Exception as e:
            logger.error(f"Failed to extract text by pages: {e}")
            raise Exception(f"Page-based text extraction failed: {e}")

    def validate_pdf(self, pdf_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a file is a valid PDF.

        Args:
            pdf_path: Path to the file to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            pdf_path = Path(pdf_path)

            # Check file existence
            if not pdf_path.exists():
                return False, "File does not exist"

            # Check file extension
            if pdf_path.suffix.lower() not in self.supported_formats:
                return False, "Invalid file extension"

            # Check file size (basic validation)
            file_size = pdf_path.stat().st_size
            if file_size < 100:  # Less than 100 bytes is suspicious
                return False, "File too small to be a valid PDF"

            # Try to open and validate PDF structure
            doc = fitz.open(str(pdf_path))

            # Check if PDF is encrypted
            if doc.is_encrypted:
                doc.close()
                return False, "PDF is encrypted and password protected"

            # Check page count
            if len(doc) == 0:
                doc.close()
                return False, "PDF has no pages"

            # Check if we can extract text
            first_page = doc[0]
            test_text = first_page.get_text()

            if len(test_text.strip()) < 10:
                doc.close()
                return False, "PDF appears to be empty or image-only"

            doc.close()

            logger.info(f"PDF validation successful: {pdf_path.name}")
            return True, None

        except Exception as e:
            logger.error(f"PDF validation failed: {e}")
            return False, f"PDF validation failed: {str(e)}"

    def extract_text_by_range(
        self,
        pdf_path: str,
        start_page: int = 1,
        end_page: Optional[int] = None
    ) -> str:
        """
        Extract text from a specific page range.

        Args:
            pdf_path: Path to the PDF file
            start_page: Starting page number (1-indexed)
            end_page: Ending page number (None for all pages)

        Returns:
            Extracted text from specified range
        """
        try:
            pdf_path = Path(pdf_path)

            if not pdf_path.exists():
                raise Exception(f"PDF file not found: {pdf_path}")

            doc = fitz.open(str(pdf_path))
            total_pages = len(doc)

            # Validate page range
            if start_page < 1 or start_page > total_pages:
                raise Exception(f"Invalid start page: {start_page}")

            if end_page is None:
                end_page = total_pages

            if end_page < start_page or end_page > total_pages:
                raise Exception(f"Invalid end page: {end_page}")

            logger.info(f"Extracting text from pages {start_page}-{end_page}")

            text_parts = []

            # Convert to 0-indexed for internal use
            for page_num in range(start_page - 1, end_page):
                try:
                    page = doc[page_num]
                    page_text = self._extract_page_text(page)
                    text_parts.append(page_text)
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num + 1}: {e}")
                    continue

            doc.close()

            full_text = '\n'.join(text_parts)
            full_text = self._clean_text(full_text)

            logger.info(f"Extracted {len(full_text)} characters from pages {start_page}-{end_page}")

            return full_text

        except Exception as e:
            logger.error(f"Failed to extract text by range: {e}")
            raise Exception(f"Range-based text extraction failed: {e}")

    def is_pdf(self, file_path: str) -> bool:
        """
        Check if a file is a PDF by examining file signature.

        Args:
            file_path: Path to the file

        Returns:
            True if file is a PDF, False otherwise
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                return False

            # Check file extension
            if file_path.suffix.lower() != '.pdf':
                return False

            # Check file signature (magic bytes)
            with open(file_path, 'rb') as f:
                header = f.read(4)
                return header == b'%PDF'

        except Exception as e:
            logger.error(f"Failed to check if file is PDF: {e}")
            return False


# Convenience function to create PDF service
def create_pdf_service() -> EnhancedPDFService:
    """
    Create an enhanced PDF service instance.

    Returns:
        EnhancedPDFService instance
    """
    return EnhancedPDFService()
