"""Source merging strategies for combining multiple glossary sources."""

import logging
from pathlib import Path
from typing import Any, Optional

from .data_cleaner import DataCleaner

logger = logging.getLogger(__name__)


class SourceMerger:
    """Merge glossary data from multiple files or dataframes with conflict resolution."""

    STRATEGIES = ("highest_confidence", "longest_translation", "most_sources", "most_recent", "manual")
    DEFAULT_STRATEGY = "highest_confidence"

    def __init__(self, strategy: str = DEFAULT_STRATEGY) -> None:
        if strategy not in self.STRATEGIES:
            raise ValueError(f"Unknown strategy '{strategy}'. Choose from {self.STRATEGIES}")
        self.strategy = strategy
        self._report: dict[str, Any] = {
            "sources_processed": 0,
            "total_input": 0,
            "total_output": 0,
            "duplicates_removed": 0,
            "conflicts_resolved": 0,
            "details": [],
        }

    def merge_csv_files(
        self,
        paths: list[str | Path],
        en_col: str = "en",
        ar_col: str = "ar",
    ) -> list[dict]:
        """Read multiple CSV files and merge into a deduplicated list."""
        all_terms: list[dict] = []
        for p in paths:
            p = Path(p)
            if not p.exists():
                logger.warning("File not found, skipping: %s", p)
                continue
            terms = self._read_csv(p, en_col, ar_col)
            all_terms.extend(terms)
            self._report["sources_processed"] += 1
        self._report["total_input"] = len(all_terms)
        merged = self.deduplicate(all_terms)
        self._report["total_output"] = len(merged)
        self._report["duplicates_removed"] = self._report["total_input"] - self._report["total_output"]
        return merged

    def merge_dataframes(
        self, df_list: list[tuple["Any", str]]
    ) -> "Any":
        """Merge a list of (DataFrame, source_name) tuples.

        Requires pandas. Falls back gracefully if not installed.
        """
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas is required for merge_dataframes")
            return None

        frames: list["pd.DataFrame"] = []
        for df, source_name in df_list:
            df = df.copy()
            df["_source"] = source_name
            frames.append(df)

        if not frames:
            return pd.DataFrame()

        combined = pd.concat(frames, ignore_index=True)
        self._report["sources_processed"] = len(df_list)
        self._report["total_input"] = len(combined)

        # Deduplicate by (english, arabic) keeping best
        combined["_key"] = (
            combined.get("english", pd.Series(dtype=str)).astype(str).str.strip().str.lower()
            + "||"
            + combined.get("arabic", pd.Series(dtype=str)).astype(str).str.strip()
        )

        def _pick(group: "pd.DataFrame") -> "pd.DataFrame":
            if self.strategy == "highest_confidence":
                col = "confidence" if "confidence" in group.columns else None
                if col:
                    return group.loc[group[col].astype(float).idxmax()]
            elif self.strategy == "longest_translation":
                ar_col_name = "arabic" if "arabic" in group.columns else None
                if ar_col_name:
                    return group.loc[group[ar_col_name].astype(str).str.len().idxmax()]
            return group.iloc[0]

        deduped = combined.groupby("_key", as_index=False).apply(_pick)
        deduped = deduped.drop(columns=["_key"], errors="ignore")
        self._report["total_output"] = len(deduped)
        self._report["duplicates_removed"] = self._report["total_input"] - self._report["total_output"]
        return deduped

    def deduplicate(
        self, terms: list[dict], key_cols: Optional[list[str]] = None
    ) -> list[dict]:
        """Deduplicate a list of term dicts by (english, arabic)."""
        if key_cols is None:
            key_cols = ["english", "arabic"]

        seen: dict[tuple[str, str], dict] = {}
        for t in terms:
            key = tuple(str(t.get(c, "")).strip().lower() if c == "english" else str(t.get(c, "")).strip() for c in key_cols)  # type: ignore[arg-type]
            if key in seen:
                self._report["conflicts_resolved"] += 1
                resolved = self._resolve_conflict(seen[key], t)
                seen[key] = resolved
            else:
                seen[key] = t
        return list(seen.values())

    def _resolve_conflict(self, existing: dict, new: dict) -> dict:
        """Pick the better of two conflicting entries using the configured strategy."""
        if self.strategy == "highest_confidence":
            if DataCleaner.normalize_confidence(new.get("confidence", 0)) > DataCleaner.normalize_confidence(existing.get("confidence", 0)):
                return new
            return existing
        elif self.strategy == "longest_translation":
            if len(str(new.get("arabic", ""))) > len(str(existing.get("arabic", ""))):
                return new
            return existing
        elif self.strategy == "most_sources":
            if str(new.get("source", "")) > str(existing.get("source", "")):
                return new
            return existing
        elif self.strategy == "most_recent":
            # Prefer entry with later timestamps
            for ts_col in ("updated_at", "created_at"):
                if ts_col in new and ts_col in existing:
                    if str(new[ts_col]) >= str(existing[ts_col]):
                        return new
                    return existing
            return existing
        # manual / default — keep existing
        return existing

    def merge_with_database(
        self, terms: list[dict], db_manager: Any
    ) -> int:
        """Merge terms into the database. Returns count of newly added terms."""
        added = 0
        for t in terms:
            try:
                db_manager.add_term(
                    english=t.get("english", ""),
                    arabic=t.get("arabic", ""),
                    category=t.get("category", ""),
                    source=t.get("source", ""),
                    confidence=DataCleaner.normalize_confidence(t.get("confidence", 0.5)),
                    type=DataCleaner.normalize_type(t.get("type", "")),
                    section=t.get("section", ""),
                    hash=DataCleaner.generate_hash(t.get("english", ""), t.get("arabic", "")),
                )
                added += 1
            except Exception:
                pass  # duplicate or constraint violation
        return added

    def smart_merge_glossary_directory(
        self, directory: str | Path, output_path: Optional[str | Path] = None
    ) -> list[dict]:
        """Scan a directory for glossary CSV/TSV/JSON files and merge them all."""
        directory = Path(directory)
        if not directory.is_dir():
            raise FileNotFoundError(f"Directory not found: {directory}")

        paths: list[Path] = []
        for ext in ("*.csv", "*.tsv", "*.json", "*.jsonl"):
            paths.extend(directory.rglob(ext))

        if not paths:
            logger.warning("No glossary files found in %s", directory)
            return []

        all_terms: list[dict] = []
        for p in paths:
            try:
                if p.suffix == ".csv":
                    all_terms.extend(self._read_csv(p, "en", "ar"))
                elif p.suffix == ".tsv":
                    all_terms.extend(self._read_tsv(p))
                elif p.suffix in (".json", ".jsonl"):
                    all_terms.extend(self._read_json(p))
                self._report["sources_processed"] += 1
            except Exception as exc:
                logger.warning("Failed to read %s: %s", p, exc)

        self._report["total_input"] = len(all_terms)
        merged = self.deduplicate(all_terms)
        self._report["total_output"] = len(merged)
        self._report["duplicates_removed"] = self._report["total_input"] - self._report["total_output"]

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if output_path.suffix == ".csv":
                self._write_csv(merged, output_path)
            elif output_path.suffix == ".json":
                import json
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(merged, f, ensure_ascii=False, indent=2)

        return merged

    def get_merge_report(self) -> dict[str, Any]:
        """Return statistics about the last merge operation."""
        return dict(self._report)

    # ------------------------------------------------------------------
    # Internal I/O helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _read_csv(path: Path, en_col: str, ar_col: str) -> list[dict]:
        import csv
        terms: list[dict] = []
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                en = row.get(en_col, row.get("english", row.get("en", "")))
                ar = row.get(ar_col, row.get("arabic", row.get("ar", "")))
                if en or ar:
                    row["english"] = str(en or "")
                    row["arabic"] = str(ar or "")
                    terms.append(row)
        return terms

    @staticmethod
    def _read_tsv(path: Path) -> list[dict]:
        import csv
        terms: list[dict] = []
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                en = row.get("en", row.get("english", ""))
                ar = row.get("ar", row.get("arabic", ""))
                if en or ar:
                    row["english"] = str(en or "")
                    row["arabic"] = str(ar or "")
                    terms.append(row)
        return terms

    @staticmethod
    def _read_json(path: Path) -> list[dict]:
        import json
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "terms" in data:
            return data["terms"]
        return []

    @staticmethod
    def _write_csv(terms: list[dict], path: Path) -> None:
        import csv
        if not terms:
            return
        fieldnames: list[str] = []
        for t in terms:
            for k in t:
                if k not in fieldnames:
                    fieldnames.append(k)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(terms)