from __future__ import annotations

import abc
import io
from typing import Any


class DocumentParserInterface(abc.ABC):
    """Universal contract for document parsers.

    Each subclass processes a specific format, returning parsed text
    and format-specific structural metadata.
    """

    @abc.abstractmethod
    def parse(self, file_content: bytes) -> tuple[str, dict[str, Any]]:
        """Parse raw file content.

        Returns a tuple of:
        1. Extracted raw text.
        2. Extracted metadata (headings, tables, page count).
        """
        pass
