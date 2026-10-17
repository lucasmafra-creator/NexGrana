def bucket(width):
    width = float(width or 360)
    return 'phone' if width < 700 else ('tablet' if width < 900 else ('compact' if width < 1180 else 'wide'))


def content_width(width):
    return max(280, float(width or 360) - (246 if float(width or 360) >= 900 else 0) - 32)
