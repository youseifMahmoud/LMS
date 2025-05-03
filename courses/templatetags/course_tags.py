from django import template

register = template.Library()

@register.filter
def contains(value, arg):
    """Check if a value is in a list."""
    return arg in value