import base64

import polars as pl

from .base import OutputWriter


class CsvWriter(OutputWriter):
    def write(self, df: pl.DataFrame) -> None:
        exportable = df.with_columns(
            pl.col("diff_b64")
            .map_elements(
                lambda x: base64.b64decode(x).decode() if x is not None else None,
                return_dtype=pl.String,
            )
            .alias("diff"),
            pl.col("time_all_s").map_elements(
                lambda x: str(list(x)) if x is not None else None,
                return_dtype=pl.String,
            ),
        ).drop("diff_b64")
        exportable.write_csv(self.path)
