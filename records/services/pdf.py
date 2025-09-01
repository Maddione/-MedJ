from __future__ import annotations

import importlib
from django.http import HttpResponse
from django.template.loader import render_to_string


def _get_weasy():

    try:
        mod = importlib.import_module("weasyprint")
        return mod.HTML, getattr(mod, "CSS", None)
    except Exception as e:
        raise RuntimeError(
            "WeasyPrint dependencies are missing. Install Pango/Cairo/GDK-PixBuf (see docs), "
            "или следвай инструкциите за MSYS2/GTK под Windows."
        ) from e


def render_html_to_pdf(html: str, base_url: str | None = None) -> bytes:

    HTML, CSS = _get_weasy()
    stylesheets = []
    if CSS is not None:
        stylesheets = [
            CSS(
                string="""
                @page { size: A4; margin: 1.5cm; }
                body { font-family: 'DejaVu Sans', sans-serif; }
                thead { display: table-header-group; }
                tfoot { display: table-footer-group; }
            """
            )
        ]
    return HTML(string=html, base_url=base_url).write_pdf(stylesheets=stylesheets)


def render_template_to_pdf(request, template_name: str, context: dict) -> bytes:

    html = render_to_string(template_name, context=context, request=request)
    base_url = request.build_absolute_uri("/")
    return render_html_to_pdf(html, base_url=base_url)


def pdf_response(filename: str, pdf_bytes: bytes, inline: bool = False) -> HttpResponse:

    disposition = "inline" if inline else "attachment"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    response["Content-Length"] = str(len(pdf_bytes))
    return response
