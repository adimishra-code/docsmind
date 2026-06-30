from __future__ import annotations

import anyio
import pathlib
import shutil

from app.core.exceptions import NotFoundError
from app.services.storage.base import StorageInterface


class LocalStorage(StorageInterface):
    """Local disk adapter for development and testing environments."""

    def __init__(self, base_dir: str | pathlib.Path = "storage") -> None:
        self.base_path = pathlib.Path(base_dir).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload(self, file_content: bytes, destination_path: str) -> str:
        """Write file content to local disk using async file I/O."""
        # Sanitize path to prevent directory traversal
        target_path = self.base_path / pathlib.Path(destination_path).name
        
        # Write bytes asynchronously using anyio
        async_target = anyio.Path(target_path)
        await async_target.write_bytes(file_content)
        
        # Return path string relative to workspace root
        return str(target_path)

    async def download(self, storage_path: str) -> bytes:
        """Read file content from local disk."""
        target_path = pathlib.Path(storage_path).resolve()
        
        # Validate path remains within the base directory to prevent directory traversal
        if not str(target_path).startswith(str(self.base_path)):
            raise PermissionError("Directory traversal blocked.")

        async_target = anyio.Path(target_path)
        if not await async_target.exists():
            raise NotFoundError("Stored file not found.")

        return await async_target.read_bytes()

    async def delete(self, storage_path: str) -> None:
        """Remove file from local disk."""
        target_path = pathlib.Path(storage_path).resolve()
        
        if not str(target_path).startswith(str(self.base_path)):
            raise PermissionError("Directory traversal blocked.")

        async_target = anyio.Path(target_path)
        if await async_target.exists():
            await async_target.unlink()
