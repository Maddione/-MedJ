from __future__ import annotations
import csv
import io
from typing import List, Optional

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PyPDF2 import PdfReader, PdfWriter

PRIMARY_DARK = colors.HexColor("#0A4E75")
TEAL         = colors.HexColor("#43B8CF")
CREAM        = colors.HexColor("#FDFEE9")
BLOCK_BG     = colors.HexColor("#FDFEE9")


_FONT_MAIN = "Helvetica"
try:
    pdfmetrics.registerFont(TTFont("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    _FONT_MAIN = "DejaVuSans"
except Exception:
    pass

def _sniff_csv(text: str):

    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=";,|\t,")
        return dialect
    except Exception:
        d = csv.excel
        d.delimiter = ","
        return d

def _read_csv(file_obj) -> List[List[str]]:

    raw = file_obj.read()
    if isinstance(raw, bytes):
        raw_bytes = raw
    else:
        raw_bytes = raw.encode("utf-8", errors="replace")

    for enc in ("utf-8-sig", "utf-8", "cp1251", "windows-1252", "iso-8859-1"):
        try:
            text = raw_bytes.decode(enc)
            dialect = _sniff_csv(text)
            f = io.StringIO(text)
            reader = csv.reader(f, dialect=dialect)
            rows = [list(map(lambda s: s.strip(), r)) for r in reader]
            if rows:
                return rows
        except Exception:
            continue

    f = io.StringIO(raw_bytes.decode("utf-8", errors="replace"))
    reader = csv.reader(f)
    return [list(map(lambda s: s.strip(), r)) for r in reader]

def _clean_rows(rows: List[List[str]]) -> List[List[str]]:
    cleaned: List[List[str]] = []
    for r in rows:

        cleaned.append([ (c or "").replace("\ufeff","").replace("\xa0"," ").strip() for c in r ])
    return cleaned

def _style_table(table: Table, header_font_size: int = 11):
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), TEAL),
        ("TEXTCOLOR",  (0,0), (-1,0), CREAM),
        ("FONTNAME",   (0,0), (-1,0), f"{_FONT_MAIN}-Bold" if _FONT_MAIN != "Helvetica" else "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,0), header_font_size),
        ("GRID",       (0,0), (-1,-1), 0.25, PRIMARY_DARK),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, BLOCK_BG]),
    ]))

def _title_paragraph(text: str) -> Paragraph:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="TitleCyr",
        parent=styles["Title"],
        fontName=_FONT_MAIN,
        fontSize=16,
        textColor=PRIMARY_DARK,
        spaceAfter=8,
    ))
    return Paragraph(text, styles["TitleCyr"])

def _normal_paragraph(text: str) -> Paragraph:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="NormalCyr",
        parent=styles["Normal"],
        fontName=_FONT_MAIN,
        fontSize=10,
    ))
    return Paragraph(text, styles["NormalCyr"])

def _build_pdf_from_table(data: List[List[str]], title: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), rightMargin=12*mm, leftMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
    story: List = []
    story.append(_title_paragraph(title))
    story.append(Spacer(1, 6))

    col_count = len(data[0]) if data else 0

    col_widths = [ (landscape(A4)[0] - 24*mm) / max(col_count, 1) ] * max(col_count, 1)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    _style_table(table, header_font_size=11)
    story.append(table)

    doc.build(story)
    return buf.getvalue()

def events_csv_to_pdf(csv_file, title: Optional[str] = None) -> bytes:
    rows = _clean_rows(_read_csv(csv_file))
    if not rows:
        rows = [["No data"]]
    return _build_pdf_from_table(rows, title or "Медицински доклад")

def labs_csv_to_pdf(csv_file, title: Optional[str] = None) -> bytes:
    rows = _clean_rows(_read_csv(csv_file))
    if not rows:
        rows = [["No data"]]
    return _build_pdf_from_table(rows, title or "Лабораторни резултати")

def _overlay_pages_on_template(generated_pdf_bytes: bytes, template_pdf_path: str) -> bytes:

    try:
        template_reader = PdfReader(template_pdf_path)
        template_page = template_reader.pages[0]
    except Exception:

        return generated_pdf_bytes

    gen_reader = PdfReader(io.BytesIO(generated_pdf_bytes))
    writer = PdfWriter()

    for i in range(len(gen_reader.pages)):
        base = template_page
        overlay = gen_reader.pages[i]

        base.merge_page(overlay)
        writer.add_page(base)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()

def csv_to_pdf_with_template(csv_file, kind: str, template_pdf_path: str, title: Optional[str] = None) -> bytes:

    if kind == "labs":
        generated = labs_csv_to_pdf(csv_file, title or "Лабораторни резултати")
    else:
        generated = events_csv_to_pdf(csv_file, title or "Медицински доклад")
    return _overlay_pages_on_template(generated, template_pdf_path)
