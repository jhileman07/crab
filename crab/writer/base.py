from abc import ABC, abstractmethod
from pathlib import Path

import polars as pl


class OutputWriter(ABC):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @abstractmethod
    def write(self, df: pl.DataFrame) -> None: ...
