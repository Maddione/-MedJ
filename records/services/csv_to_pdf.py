from __future__ import annotations
import csv, io
from typing import List, Optional

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from PyPDF2 import PdfReader, PdfWriter

PRIMARY_DARK = colors.HexColor("#0A4E75")
TEAL         = colors.HexColor("#43B8CF")
CREAM        = colors.HexColor("#FDFEE9")
BLOCK_BG     = colors.HexColor("#FDFEE9")

def _overlay_pages_on_template(generated_pdf: bytes, template_pdf_path: str) -> bytes:

    gen_reader = PdfReader(io.BytesIO(generated_pdf))
    tmpl_reader = PdfReader(template_pdf_path)
    writer = PdfWriter()
    base = tmpl_reader.pages[0]
    for i in range(len(gen_reader.pages)):
        page = base.clone()
        page.merge_page(gen_reader.pages[i])
        writer.add_page(page)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

def _read_csv(file_like) -> List[List[str]]:
    data = file_like.read()
    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("utf-8")
    else:
        text = data
    reader = csv.reader(io.StringIO(text))
    rows = [list(r) for r in reader]

    cleaned = []
    for r in rows:
        while r and r[-1] == "":
            r.pop()
        cleaned.append(r)
    return cleaned

def _style_table(table: Table, header_font_size: int = 11):
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), TEAL),
        ("TEXTCOLOR",  (0,0), (-1,0), CREAM),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,0), header_font_size),
        ("GRID",       (0,0), (-1,-1), 0.25, PRIMARY_DARK),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, BLOCK_BG]),
    ]))

def events_csv_to_pdf(csv_file, title: str = "Медицински доклад") -> bytes:
    rows = _read_csv(csv_file)
    if not rows:
        rows = [["date","category","specialty","summary"]]
    header, body = rows[0], rows[1:]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=15*mm, leftMargin=15*mm, rightMargin=15*mm, bottomMargin=15*mm
    )
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 6)]

    col_widths = [28*mm, 40*mm, 45*mm, 80*mm]
    data = [header] + body
    table = Table(data, colWidths=col_widths, repeatRows=1)
    _style_table(table, header_font_size=11)
    story.append(table)

    doc.build(story)
    return buf.getvalue()

def labs_csv_to_pdf(csv_file, title: str = "Лабораторни резултати") -> bytes:
    rows = _read_csv(csv_file)
    if not rows:
        rows = [["indicator"]]
    header, body = rows[0], rows[1:]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        topMargin=12*mm, leftMargin=12*mm, rightMargin=12*mm, bottomMargin=12*mm
    )
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 6)]

    if len(header) <= 1:
        col_widths = [80*mm]
    else:
        total = 270*mm
        first = 60*mm
        remain = total - first
        per = remain / (len(header) - 1)
        col_widths = [first] + [per]*(len(header)-1)

    data = [header] + body
    table = Table(data, colWidths=col_widths, repeatRows=1)
    _style_table(table, header_font_size=11)
    story.append(table)

    doc.build(story)
    return buf.getvalue()

def csv_to_pdf_with_template(csv_file, kind: str, template_pdf_path: str, title: Optional[str] = None) -> bytes:

    if kind == "labs":
        generated = labs_csv_to_pdf(csv_file, title or "Лабораторни резултати")
    else:
        generated = events_csv_to_pdf(csv_file, title or "Медицински доклад")
    return _overlay_pages_on_template(generated, template_pdf_path)
