import json
from pathlib import Path
from typing import NamedTuple

REGISTRY_PATH = Path("reports_db") / "registry.json"

class ReportRecord(NamedTuple):
    report_path: Path
    source_pdfs: list[str]

class ReportRegistry:
    """Tracks which source PDFs generated each ticker's last saved report,
    so the pipeline can skip regeneration when nothing actually changed.
    """

    def __init__(self, registry_path: Path = REGISTRY_PATH):
        self._registry_path = registry_path

    def get_last_generation(self, ticker: str) -> ReportRecord | None:
        entry = self._read().get(ticker.upper())
        if entry is None:
            return None

        return ReportRecord(
            report_path=Path(entry["report_path"]),
            source_pdfs=entry["source_pdfs"]
        )

    def record_generation(self, ticker: str, report_path: Path, source_pdfs: list[str]) -> None:
        data = self._read()
        data[ticker.upper()] = {
            "report_path": str(report_path),
            "source_pdfs": source_pdfs,
        }
        self._write(data)

    def _read(self) -> dict:
        if not self._registry_path.exists():
            return {}

        return json.loads(self._registry_path.read_text(encoding="utf-8"))

    def _write(self, data: dict) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._registry_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")