from django import template

register = template.Library()

@register.filter
def compact_number(value):
    """Formats a number into a compact string (1000 -> 1k, 1000000 -> 1m)"""
    try:
        val = int(value)
    except (ValueError, TypeError):
        return value

    if val < 1000: return str(val)
    if val < 1000000: return f"{val/1000:.1f}k".replace(".0k", "k")
    if val < 1000000000: return f"{val/1000000:.1f}m".replace(".0m", "m")
    return f"{val/1000000000:.1f}b".replace(".0b", "b")
