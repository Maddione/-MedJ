from django import template

register = template.Library()

@register.filter
def ddmmyyyy(value):
    try:
        return value.strftime("%d-%m-%Y")
    except Exception:
        return ""
