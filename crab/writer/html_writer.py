import base64
import html
import statistics

import polars as pl

from .base import OutputWriter


class HtmlWriter(OutputWriter):
    def write(self, df: pl.DataFrame) -> None:
        self.path.write_text(_render_html(df), encoding="utf-8")


def _colorize_diff_html(diff_str: str) -> str:
    lines = []
    for line in diff_str.splitlines():
        escaped = html.escape(line)
        if line.startswith("+++") or line.startswith("---"):
            lines.append(f'<span class="diff-header">{escaped}</span>')
        elif line.startswith("+"):
            lines.append(f'<span class="diff-add">{escaped}</span>')
        elif line.startswith("-"):
            lines.append(f'<span class="diff-del">{escaped}</span>')
        elif line.startswith("@@"):
            lines.append(f'<span class="diff-hunk">{escaped}</span>')
        else:
            lines.append(escaped)
    return "\n".join(lines)


def _fmt_time(t: float) -> str:
    if t < 1:
        return f"{t * 1000:.1f} ms"
    return f"{t:.3f} s"


_CSS = """
body { font-family: system-ui, -apple-system, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; color: #222; }
h1 { font-size: 1.6rem; margin-bottom: 0.25rem; }
.summary { display: flex; gap: 2rem; margin: 1rem 0 1.5rem; font-size: 1rem; }
.summary span { padding: 0.3rem 0.8rem; border-radius: 4px; background: #f3f3f3; }
.pass-count { color: #2a7; font-weight: bold; }
.fail-count { color: #c33; font-weight: bold; }
table { border-collapse: collapse; width: 100%; font-size: 0.9rem; margin-bottom: 2rem; }
th { text-align: left; background: #f0f0f0; padding: 0.5rem 0.75rem; border-bottom: 2px solid #ddd; }
td { padding: 0.4rem 0.75rem; border-bottom: 1px solid #eee; }
tr:hover td { background: #fafafa; }
.badge-pass { color: #2a7; font-weight: bold; }
.badge-fail { color: #c33; font-weight: bold; }
.timing { color: #555; font-size: 0.85rem; }
details { border: 1px solid #ddd; border-radius: 4px; margin: 0.75rem 0; }
summary { cursor: pointer; padding: 0.6rem 1rem; background: #fff0f0; font-weight: bold; }
summary:hover { background: #ffe4e4; }
.detail-body { padding: 0.75rem 1rem; }
.stderr-block { background: #fff8f0; border-left: 3px solid #f90; padding: 0.5rem 0.75rem; margin-bottom: 0.75rem; font-size: 0.85rem; white-space: pre-wrap; word-break: break-all; }
.stdout-block { background: #f8f8f8; border-left: 3px solid #88c; padding: 0.5rem 0.75rem; margin-bottom: 0.75rem; font-size: 0.85rem; white-space: pre-wrap; word-break: break-all; font-family: monospace; }
pre.diff { background: #f8f8f8; border: 1px solid #ddd; border-radius: 3px; padding: 0.75rem; font-size: 0.82rem; overflow-x: auto; white-space: pre; line-height: 1.4; }
.diff-add { color: #2a7; background: #eaffea; display: block; }
.diff-del { color: #c33; background: #fff0f0; display: block; }
.diff-hunk { color: #06a; display: block; }
.diff-header { font-weight: bold; display: block; }
h2 { font-size: 1.2rem; margin-top: 2rem; }
"""


def _render_table(rows: list[dict]) -> str:
    table_rows = []
    for row in rows:
        badge = '<span class="badge-pass">PASS</span>' if row["passed"] else '<span class="badge-fail">FAIL</span>'
        mean_t = _fmt_time(row["time_mean_s"]) if row["time_mean_s"] else "—"
        all_t = row["time_all_s"]
        stdev_t = _fmt_time(statistics.stdev(all_t)) if len(all_t) >= 2 else "—"
        if row["stderr"]:
            lines = row["stderr"].splitlines()
            truncated = lines[:5]
            suffix = "\n..." if len(lines) > 5 else ""
            stderr_cell = html.escape("\n".join(truncated)) + suffix
        else:
            stderr_cell = ""
        table_rows.append(
            "<tr>"
            f"<td>{html.escape(row['test'])}</td>"
            f"<td>{badge}</td>"
            f'<td class="timing">{mean_t}</td>'
            f'<td class="timing">{stdev_t}</td>'
            f'<td style="white-space: pre-wrap">{stderr_cell}</td>'
            "</tr>"
        )
    return (
        "<table>"
        "<thead><tr><th>Test</th><th>Result</th><th>Mean Time</th><th>Stdev</th><th>Stderr</th></tr></thead>"
        "<tbody>" + "\n".join(table_rows) + "</tbody>"
        "</table>"
    )


def _render_summary(rows: list[dict]) -> str:
    total = len(rows)
    passed = sum(1 for r in rows if r["passed"])
    failed = total - passed
    total_time = sum(r["time_mean_s"] for r in rows)
    return (
        '<div class="summary">'
        f'<span class="pass-count">Passed: {passed}/{total}</span>'
        f'<span class="fail-count">Failed: {failed}</span>'
        f'<span class="timing">Total time: {_fmt_time(total_time)}</span>'
        "</div>"
    )


def _render_body(df: pl.DataFrame) -> str:
    suites: dict[str, list[dict]] = {}
    for row in df.iter_rows(named=True):
        suites.setdefault(row["suite"], []).append(row)

    multi = len(suites) > 1

    sections = []
    failure_sections = []
    for suite, rows in suites.items():
        heading = f"<h2>{html.escape(suite)}</h2>" if multi else ""
        sections.append(heading + _render_summary(rows) + _render_table(rows))

        suite_failures = []
        for row in rows:
            test_name = html.escape(row["test"])
            stderr_html = ""
            if row["stderr"]:
                stderr_html = f'<pre class="stderr-block">{html.escape(row["stderr"])}</pre>'
            diff_html = ""
            if row["diff_b64"]:
                diff_str = base64.b64decode(row["diff_b64"]).decode()
                diff_html = f'<pre class="diff">{_colorize_diff_html(diff_str)}</pre>'
            stdout_html = ""
            if row.get("stdout"):
                stdout_html = f'<pre class="stdout-block">{html.escape(row["stdout"])}</pre>'

            if not row["passed"]:
                suite_failures.append(
                    f'<details><summary>{test_name}</summary><div class="detail-body">{stderr_html}{diff_html}</div></details>'
                )
            elif stdout_html or stderr_html:
                suite_failures.append(
                    f'<details><summary>{test_name}</summary><div class="detail-body">{stderr_html}{stdout_html}</div></details>'
                )

        if suite_failures:
            suite_heading = f"<h3>{html.escape(suite)}</h3>" if multi else ""
            failure_sections.append(suite_heading + "\n".join(suite_failures))

    failures_html = ""
    if failure_sections:
        failures_html = "<h2>Details</h2>" + "\n".join(failure_sections)

    return "\n".join(sections) + "\n" + failures_html


def _render_html(df: pl.DataFrame) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Test Results</title>
<style>{_CSS}</style>
</head>
<body>
<h1>Test Results</h1>
{_render_body(df)}
</body>
</html>
"""
