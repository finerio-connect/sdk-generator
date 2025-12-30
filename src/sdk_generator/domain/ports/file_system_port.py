from abc import ABC, abstractmethod
from pathlib import Path


class FileSystemPort(ABC):
    @abstractmethod
    def exists(self, path: Path) -> bool:
        raise NotImplementedError

    @abstractmethod
    def remove(self, path: Path) -> None:
        raise NotImplementedError

    @abstractmethod
    def mkdir(self, path: Path) -> None:
        raise NotImplementedError
