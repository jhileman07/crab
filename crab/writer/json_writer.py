import polars as pl

from .base import OutputWriter


class JsonWriter(OutputWriter):
    def write(self, df: pl.DataFrame) -> None:
        df.write_json(self.path)
