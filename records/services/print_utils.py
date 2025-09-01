from __future__ import annotations
import io
from typing import Dict, Any
from django.http import HttpResponse
from django.template.loader import render_to_string

try:

    from xhtml2pdf import pisa
except Exception as e:  # pragma: no cover
    pisa = None

def render_template_to_pdf(request, template_name: str, context: Dict[str, Any]) -> bytes:

    html = render_to_string(template_name, context=context, request=request)
    if not pisa:

        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.setFont("Helvetica", 12)
        c.drawString(40, 800, "xhtml2pdf не е инсталиран. Инсталирай 'xhtml2pdf' за HTML->PDF рендер.")
        c.drawString(40, 784, "Временно съдържанието (html) е налично само като текст в този PDF.")
        # По желание: запиши малка част от HTML-а
        snippet = (html or "")[:2000].replace("\n", " ")
        c.setFont("Helvetica", 8)
        c.drawString(40, 760, snippet)
        c.showPage()
        c.save()
        return buf.getvalue()

    out = io.BytesIO()

    pisa.CreatePDF(io.StringIO(html), dest=out)
    return out.getvalue()

def pdf_response(filename: str, pdf_bytes: bytes, inline: bool = True) -> HttpResponse:

    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    disp = "inline" if inline else "attachment"
    resp["Content-Disposition"] = f'{disp}; filename="{filename}"'
    return resp
