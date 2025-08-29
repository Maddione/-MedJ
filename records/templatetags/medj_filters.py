from django import template

register = template.Library()

@register.filter(name="add_class")
def add_class(field, css):
    attrs = dict(field.field.widget.attrs or {})
    # Ако вече има class, добавяме; иначе задаваме
    if "class" in attrs and attrs["class"]:
        attrs["class"] = f'{attrs["class"]} {css}'
    else:
        attrs["class"] = css
    return field.as_widget(attrs=attrs)
