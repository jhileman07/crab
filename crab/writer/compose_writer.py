import base64
import json
from abc import ABC, abstractmethod
from pathlib import Path

import polars as pl

from .html_writer import _CSS, _render_body


class ComposeWriter(ABC):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @abstractmethod
    def write(self, tabs: list[tuple[str, pl.DataFrame]]) -> None: ...


def _labeled(label: str, df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(pl.lit(label).alias("label"))


class CsvComposeWriter(ComposeWriter):
    def write(self, tabs: list[tuple[str, pl.DataFrame]]) -> None:
        pl.concat([_labeled(label, df) for label, df in tabs]).write_csv(self.path)


class ParquetComposeWriter(ComposeWriter):
    def write(self, tabs: list[tuple[str, pl.DataFrame]]) -> None:
        pl.concat([_labeled(label, df) for label, df in tabs]).write_parquet(self.path)


class JsonComposeWriter(ComposeWriter):
    def write(self, tabs: list[tuple[str, pl.DataFrame]]) -> None:
        def _serialize_row(row: dict) -> dict:
            if row.get("diff_b64") is not None:
                row = {**row, "diff_b64": base64.b64encode(row["diff_b64"]).decode()}
            return row

        data = [{"label": label, "results": [_serialize_row(r) for r in df.to_dicts()]} for label, df in tabs]
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class HtmlComposeWriter(ComposeWriter):
    def write(self, tabs: list[tuple[str, pl.DataFrame]]) -> None:
        self.path.write_text(_render_html_tabbed(tabs), encoding="utf-8")


def _render_html_tabbed(tabs: list[tuple[str, pl.DataFrame]]) -> str:
    tab_css_rules = []
    for i in range(len(tabs)):
        tab_css_rules.append(
            f"#tab-{i}:checked ~ .tab-panels #panel-{i} {{ display: block; }}\n"
            f'#tab-{i}:checked ~ .tab-bar label[for="tab-{i}"] {{ font-weight: bold; background: #fff; border-color: #ddd; }}'
        )

    tab_bar_css = (
        ".tab-bar { display: flex; border-bottom: 2px solid #ddd; margin-bottom: 1.5rem; }\n"
        ".tab-bar label { padding: 0.5rem 1.25rem; cursor: pointer; border: 1px solid transparent;"
        " border-bottom: none; margin-bottom: -2px; border-radius: 4px 4px 0 0; }\n"
        ".tab-panel { display: none; }"
    )

    inputs_html = "\n".join(
        f'<input type="radio" name="tabs" id="tab-{i}"{" checked" if i == 0 else ""} hidden>' for i in range(len(tabs))
    )

    labels_html = "\n".join(f'<label for="tab-{i}">{tabs[i][0]}</label>' for i in range(len(tabs)))

    panels_html = "\n".join(
        f'<div class="tab-panel" id="panel-{i}">{_render_body(df)}</div>' for i, (_, df) in enumerate(tabs)
    )

    combined_css = _CSS + "\n" + tab_bar_css + "\n" + "\n".join(tab_css_rules)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Test Results</title>
<style>{combined_css}</style>
</head>
<body>
<h1>Test Results</h1>
{inputs_html}
<div class="tab-bar">
{labels_html}
</div>
<div class="tab-panels">
{panels_html}
</div>
</body>
</html>
"""
