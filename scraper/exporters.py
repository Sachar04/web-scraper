"""
Export module - handles saving scraped data in multiple formats.
Supports: TXT, HTML, JSON, Binary (pickle).
"""

import json
import pickle
import os
from datetime import datetime


class BaseExporter:
    """Base class for all exporters."""

    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _generate_filename(self, base_name, extension):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in base_name)
        return os.path.join(self.output_dir, f"{safe_name}_{timestamp}.{extension}")

    def export(self, data, filename=None):
        raise NotImplementedError


class TxtExporter(BaseExporter):
    """Export data as formatted plain text."""

    def export(self, data, filename=None):
        filepath = filename or self._generate_filename("scrape", "txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self._format_data(data))
        return filepath

    def _format_data(self, data, indent=0):
        lines = []
        prefix = "  " * indent
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(self._format_data(value, indent + 1))
                else:
                    lines.append(f"{prefix}{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                lines.append(f"{prefix}[{i}]")
                lines.append(self._format_data(item, indent + 1))
        else:
            lines.append(f"{prefix}{data}")
        return "\n".join(lines)


class HtmlExporter(BaseExporter):
    """Export data as a styled HTML report."""

    def export(self, data, filename=None):
        filepath = filename or self._generate_filename("scrape", "html")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self._build_html(data))
        return filepath

    def _build_html(self, data):
        html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Scrape Report</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    color: #e0e0e0; padding: 2rem; min-height: 100vh;
  }
  .container { max-width: 1000px; margin: 0 auto; }
  h1 {
    text-align: center; margin-bottom: 2rem; font-size: 2rem;
    background: linear-gradient(90deg, #667eea, #764ba2);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .card {
    background: rgba(255,255,255,0.08); backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.12); border-radius: 16px;
    padding: 1.5rem; margin-bottom: 1.5rem;
  }
  .card h2 { color: #a78bfa; margin-bottom: 1rem; font-size: 1.3rem; }
  table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }
  th, td {
    padding: 0.5rem 0.75rem; text-align: left;
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }
  th { color: #c084fc; font-weight: 600; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 6px;
    background: rgba(139,92,246,0.2); font-size: 0.85em; margin: 2px; }
  pre { background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 8px;
    overflow-x: auto; font-size: 0.9em; white-space: pre-wrap; }
  a { color: #818cf8; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .timestamp { text-align: center; color: #888; margin-top: 2rem; font-size: 0.85em; }
</style>
</head>
<body>
<div class="container">
<h1>Web Scrape Report</h1>
"""
        html += self._render_section(data)
        html += f'<p class="timestamp">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>'
        html += "</div></body></html>"
        return html

    def _render_section(self, data, depth=0):
        parts = []
        if isinstance(data, dict):
            for key, value in data.items():
                parts.append(f'<div class="card"><h2>{self._escape(str(key).replace("_", " ").title())}</h2>')
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    parts.append(self._render_table(value))
                elif isinstance(value, list):
                    parts.append("<ul>")
                    for item in value:
                        parts.append(f"<li>{self._escape(str(item))}</li>")
                    parts.append("</ul>")
                elif isinstance(value, dict):
                    parts.append(self._render_section(value, depth + 1))
                else:
                    parts.append(f"<pre>{self._escape(str(value))}</pre>")
                parts.append("</div>")
        elif isinstance(data, list):
            if data and isinstance(data[0], dict):
                parts.append(self._render_table(data))
            else:
                for item in data:
                    parts.append(f"<p>{self._escape(str(item))}</p>")
        else:
            parts.append(f"<pre>{self._escape(str(data))}</pre>")
        return "\n".join(parts)

    def _render_table(self, items):
        if not items:
            return "<p>No data</p>"
        keys = list(items[0].keys())
        html = "<table><thead><tr>"
        for k in keys:
            html += f"<th>{self._escape(str(k).title())}</th>"
        html += "</tr></thead><tbody>"
        for item in items:
            html += "<tr>"
            for k in keys:
                val = item.get(k, "")
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val)
                cell = str(val)
                if len(cell) > 200:
                    cell = cell[:200] + "..."
                html += f"<td>{self._escape(cell)}</td>"
            html += "</tr>"
        html += "</tbody></table>"
        return html

    def _escape(self, text):
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )


class JsonExporter(BaseExporter):
    """Export data as JSON."""

    def export(self, data, filename=None):
        filepath = filename or self._generate_filename("scrape", "json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        return filepath


class BinaryExporter(BaseExporter):
    """Export data as binary (pickle) format."""

    def export(self, data, filename=None):
        filepath = filename or self._generate_filename("scrape", "bin")
        with open(filepath, "wb") as f:
            pickle.dump(data, f)
        return filepath


class ExportManager:
    """Manages all export formats."""

    FORMATS = {
        "txt": TxtExporter,
        "html": HtmlExporter,
        "json": JsonExporter,
        "bin": BinaryExporter,
    }

    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        self.exporters = {
            fmt: cls(output_dir) for fmt, cls in self.FORMATS.items()
        }

    def export(self, data, fmt, filename=None):
        """Export data in the specified format."""
        if fmt not in self.exporters:
            raise ValueError(f"Unsupported format: {fmt}. Use one of: {list(self.FORMATS.keys())}")
        return self.exporters[fmt].export(data, filename)

    def export_all(self, data, base_name="scrape"):
        """Export data in all formats. Returns dict of format -> filepath."""
        results = {}
        for fmt, exporter in self.exporters.items():
            filepath = exporter._generate_filename(base_name, fmt)
            results[fmt] = exporter.export(data, filepath)
        return results
