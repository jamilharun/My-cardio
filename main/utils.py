def sanitize_text(text):
    """
    Replace non-ASCII characters with ASCII equivalents.
    """
    return text.replace('\u2014', '--')  # Replace em dash with double hyphen

