from pathlib import Path
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string

def render_html_to_pdf(html, base_url=None):
    try:
        from weasyprint import HTML
        return HTML(string=html, base_url=base_url).write_pdf()
    except Exception:
        from io import BytesIO
        from xhtml2pdf import pisa
        buf = BytesIO()
        pisa.CreatePDF(src=html, dest=buf, encoding="utf-8")
        return buf.getvalue()

def render_template_to_pdf(template_name, context, base_url=None):
    html = render_to_string(template_name, context)
    if base_url is None:
        base_url = str(Path(settings.BASE_DIR))
    return render_html_to_pdf(html, base_url=base_url)

def pdf_http_response(pdf_bytes, filename, inline=True):
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    disposition = "inline" if inline else "attachment"
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    return response

def pdf_response(pdf_bytes, filename, inline=True):
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    disposition = "inline" if inline else "attachment"
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    return response

def render_template_to_pdf_response(template_name, context, filename, inline=True, base_url=None):
    pdf = render_template_to_pdf(template_name, context, base_url=base_url)
    return pdf_http_response(pdf, filename, inline=inline)

def create_pdf_from_template(template_name, context):
    return render_template_to_pdf(template_name, context)

def create_pdf_response(template_name, context, filename):
    return render_template_to_pdf_response(template_name, context, filename)
