import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import polars as pl

from crab.writer.compose_writer import ComposeWriter


class Composer:
    def __init__(self, writer: ComposeWriter) -> None:
        self.writer = writer
        self._entries: list[tuple[str, Path]] = []

    def add(self, crabfile: str | Path, label: str | None = None) -> None:
        p = Path(crabfile)
        self._entries.append((label if label is not None else p.name, p))

    def run(self) -> None:
        results: list[tuple[str, pl.DataFrame]] = []
        for label, path in self._entries:
            tmp_dir = Path(tempfile.mkdtemp(prefix="crab_"))
            env = {**os.environ, "CRAB_COMPOSE_OUTPUT": str(tmp_dir)}
            try:
                ret = subprocess.call([sys.executable, str(path.resolve())], env=env, cwd=path.parent)
                parquet_files = sorted(tmp_dir.glob("*.parquet"))
                if ret != 0 and not parquet_files:
                    print(f"[crab compose] warning: {path} exited with code {ret}, no output captured")
                    continue
                if not parquet_files:
                    print(f"[crab compose] warning: no output from {path}")
                    continue
                results.append((label, pl.concat([pl.read_parquet(f) for f in parquet_files])))
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)
        self.writer.write(results)
