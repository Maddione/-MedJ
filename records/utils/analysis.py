"""Utilities for working with document analysis payloads."""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
import re
from typing import Dict, Iterable, List, Mapping


@dataclass
class SummaryInfo:
    text: str
    word_count: int
    fallback_used: bool = False
    fallback_reason: str | None = None
    notice: str | None = None
    retry_suggested: bool = False


_WORD_RE = re.compile(r"[\wÀ-ÖØ-öø-ÿ]+", re.UNICODE)


def word_count(text: str) -> int:
    tokens = _WORD_RE.findall(text or "")
    return len(tokens)


def _sentences_from_text(text: str) -> Iterable[str]:
    if not text:
        return []
    chunks = re.split(r"(?<=[.!?\u2026])\s+", text.strip())
    for chunk in chunks:
        value = chunk.strip()
        if value:
            yield value


def _extended_summary(text: str, minimum_words: int) -> str:
    sentences = list(_sentences_from_text(text))
    if not sentences:
        tokens = (text or "").split()
        if len(tokens) >= minimum_words:
            return " ".join(tokens[:minimum_words])
        return text.strip()
    acc: List[str] = []
    total = 0
    for sentence in sentences:
        words = sentence.split()
        acc.append(sentence)
        total += len(words)
        if total >= minimum_words:
            break
    summary = " ".join(acc).strip()
    if summary and word_count(summary) >= minimum_words:
        return summary
    tokens = (text or "").split()
    if not tokens:
        return summary
    needed = max(minimum_words - word_count(summary), 0)
    if needed <= 0:
        return summary
    extra = " ".join(tokens[:needed])
    return (summary + " " + extra).strip()


def ensure_minimum_summary(summary: str, source_text: str, *, minimum_words: int = 50) -> SummaryInfo:
    clean_summary = (summary or "").strip()
    current_words = word_count(clean_summary)
    if current_words >= minimum_words:
        return SummaryInfo(text=clean_summary, word_count=current_words)
    extended = _extended_summary(source_text or "", minimum_words)
    extended_words = word_count(extended)
    if extended_words >= minimum_words:
        notice = "Обобщението беше разширено автоматично, за да покрие ключовите акценти."
        return SummaryInfo(
            text=extended,
            word_count=extended_words,
            fallback_used=True,
            fallback_reason="summary_short",
            notice=notice,
        )
    notice = "Анализът върна твърде кратко обобщение. Опитайте повторно, за да получите по-пълен резултат."
    return SummaryInfo(
        text=clean_summary,
        word_count=current_words,
        fallback_used=False,
        fallback_reason="summary_short",
        notice=notice,
        retry_suggested=True,
    )


def _clean(value) -> str:
    return (value or "").strip()


def render_analysis_tables(data: Mapping[str, object] | None) -> str:
    if not isinstance(data, Mapping):
        return ""
    tables = data.get("tables")
    if not isinstance(tables, Iterable):
        return ""
    parts: List[str] = []
    for table in tables:
        if not isinstance(table, Mapping):
            continue
        title = _clean(table.get("title"))
        columns = table.get("columns") if isinstance(table.get("columns"), Iterable) else []
        rows = table.get("rows") if isinstance(table.get("rows"), Iterable) else []
        if not columns or not rows:
            continue
        if title:
            parts.append(f'<h3 class="text-lg font-semibold mb-2">{escape(title)}</h3>')
        parts.append('<div class="overflow-x-auto"><table class="min-w-full text-sm border border-gray-200 rounded-xl">')
        parts.append("<thead><tr>")
        for col in columns:
            parts.append(f'<th class="px-3 py-2 bg-gray-50 text-left font-medium text-gray-700">{escape(str(col))}</th>')
        parts.append("</tr></thead><tbody>")
        for row in rows:
            if not isinstance(row, Iterable):
                continue
            cells = list(row)
            parts.append('<tr class="border-t border-gray-100">')
            for cell in cells:
                parts.append(f'<td class="px-3 py-2 text-gray-800">{escape(str(cell) if cell is not None else "")}</td>')
            parts.append("</tr>")
        parts.append("</tbody></table></div>")
    return "".join(parts)


def compose_analysis_text(data: Mapping[str, object] | None, summary_text: str) -> str:
    parts: List[str] = []
    summary = (summary_text or "").strip()
    if summary:
        parts.append(summary)
    if isinstance(data, Mapping):
        lab_overview = _clean(data.get("lab_overview")) if hasattr(data, "get") else ""
        if lab_overview:
            parts.append(lab_overview)
        diagnosis = _clean(data.get("diagnosis"))
        treatment = _clean(data.get("treatment_plan"))
        if diagnosis:
            parts.append(f"Диагноза: {diagnosis}")
        if treatment:
            parts.append(f"Терапия: {treatment}")
    return "\n\n".join([p for p in parts if p])


def normalize_analysis_payload(data: Mapping[str, object] | None) -> Dict[str, object]:
    if isinstance(data, Mapping):
        return dict(data)
    return {}
