from __future__ import annotations
from typing import Dict, List
from collections import defaultdict

def build_lab_matrix(qs) -> Dict[str, List]:

    dates: List[str] = []
    indicators: List[str] = []
    values = defaultdict(dict)

    for m in qs:
        ind = m.indicator.name if hasattr(m, "indicator") and m.indicator else "?"
        d = (m.measured_at or getattr(m, "medical_event", None).event_date).strftime("%Y-%m-%d") if (m.measured_at or getattr(m, "medical_event", None)) else ""
        if d and d not in dates:
            dates.append(d)
        if ind not in indicators:
            indicators.append(ind)
        unit = getattr(m.indicator, "unit", "") or ""
        val = f"{m.value} {unit}".strip()
        values[ind][d] = val

    headers = ["Показател"] + dates
    rows: List[List[str]] = []
    for ind in indicators:
        row = [ind] + [values[ind].get(d, "") for d in dates]
        rows.append(row)

    return {"headers": headers, "rows": rows}
