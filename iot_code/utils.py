def hue_to_rgb(hue):
    """
    Convert hue (0–360) to RGB (0–255) with full saturation and brightness.
    Returns a tuple (r, g, b).
    """
    hue = hue % 360
    c = 1.0
    x = 1.0 - abs((hue / 60.0) % 2 - 1)
    m = 0.0

    if hue < 60:
        r_, g_, b_ = c, x, 0
    elif hue < 120:
        r_, g_, b_ = x, c, 0
    elif hue < 180:
        r_, g_, b_ = 0, c, x
    elif hue < 240:
        r_, g_, b_ = 0, x, c
    elif hue < 300:
        r_, g_, b_ = x, 0, c
    else:
        r_, g_, b_ = c, 0, x

    r = int((r_ + m) * 255)
    g = int((g_ + m) * 255)
    b = int((b_ + m) * 255)
    return r, g, b
