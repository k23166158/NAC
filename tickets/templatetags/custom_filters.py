from django import template

register = template.Library()

@register.filter
def compact_number(value):
    """
    Formats a number into a compact string (1000 -> 1k, 1000000 -> 1m)
    """
    try:
        value = int(value)
    except (ValueError, TypeError):
        return value

    if value < 1000:
        return str(value)
    
    if value < 1000000:
        return f"{value / 1000:.1f}k".replace(".0k", "k")
    
    if value < 1000000000:
        return f"{value / 1000000:.1f}m".replace(".0m", "m")
    
    return f"{value / 1000000000:.1f}b".replace(".0b", "b")
