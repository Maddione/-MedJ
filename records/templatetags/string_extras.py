from django import template

register = template.Library()

@register.filter
def endswith(value, suffix: str):
    try:
        return str(value).endswith(str(suffix))
    except Exception:
        return False

@register.filter
def startswith(value, prefix: str):
    try:
        return str(value).startswith(str(prefix))
    except Exception:
        return False
