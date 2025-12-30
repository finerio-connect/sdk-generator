import shutil
from pathlib import Path

from sdk_generator.domain.ports.file_system_port import FileSystemPort


class FileSystem(FileSystemPort):
    def exists(self, path: Path) -> bool:
        return path.exists()

    def remove(self, path: Path) -> None:
        shutil.rmtree(path)

    def mkdir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
