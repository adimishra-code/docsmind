from __future__ import annotations

import abc
import pathlib


class StorageInterface(abc.ABC):
    """Universal Storage Interface.

    Enforces contract for uploading, downloading, and deleting files
    across local file systems or S3-compatible cloud providers.
    """

    @abc.abstractmethod
    async def upload(self, file_content: bytes, destination_path: str) -> str:
        """Upload file content and return the resolved storage path or URL."""
        pass

    @abc.abstractmethod
    async def download(self, storage_path: str) -> bytes:
        """Retrieve file content from the storage target."""
        pass

    @abc.abstractmethod
    async def delete(self, storage_path: str) -> None:
        """Remove the file from storage."""
        pass
