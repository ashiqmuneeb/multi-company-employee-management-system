from django import template

register = template.Library()

@register.filter
def add_class(value, arg):
    try:
        return value.as_widget(attrs={"class": arg})
    except AttributeError:
        return value