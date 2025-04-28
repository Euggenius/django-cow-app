from django import template

register = template.Library()

@register.filter
def to_str(value):
    return str(value)

@register.filter
def get_item(obj, attr):
    try:
        if isinstance(obj, dict):
            return obj.get(attr, 0)
        return getattr(obj, attr, 0)
    except Exception:
        return 0