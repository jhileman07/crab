import polars as pl

from .base import OutputWriter


class ParquetWriter(OutputWriter):
    def write(self, df: pl.DataFrame) -> None:
        df.write_parquet(self.path)
