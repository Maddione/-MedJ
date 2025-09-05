from pathlib import Path
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string

def render_template_to_html(template_name, context):
    return render_to_string(template_name, context)

def _weasyprint_pdf(html, base_url):
    from weasyprint import HTML
    return HTML(string=html, base_url=base_url).write_pdf()

def _xhtml2pdf_pdf(html):
    from io import BytesIO
    from xhtml2pdf import pisa
    buf = BytesIO()
    pisa.CreatePDF(src=html, dest=buf, encoding="utf-8")
    return buf.getvalue()

def html_to_pdf_bytes(html, base_url=None):
    try:
        return _weasyprint_pdf(html, base_url)
    except Exception:
        return _xhtml2pdf_pdf(html)

def render_template_to_pdf_bytes(template_name, context, base_url=None):
    html = render_template_to_html(template_name, context)
    return html_to_pdf_bytes(html, base_url)

def pdf_response(pdf_bytes, filename, inline=True):
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    disposition = "inline" if inline else "attachment"
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    return response

def template_to_pdf_response(template_name, context, filename, inline=True, base_url=None):
    if base_url is None:
        base_url = str(Path(settings.BASE_DIR))
    pdf = render_template_to_pdf_bytes(template_name, context, base_url)
    return pdf_response(pdf, filename, inline=inline)
