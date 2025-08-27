from django import template
import os
from django.utils.translation import gettext as _l

register = template.Library()

@register.filter
def filename_from_path(value):
    if value:
        return os.path.basename(value)
    return value