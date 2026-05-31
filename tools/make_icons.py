from pathlib import Path
import math
import struct
import zlib


ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "assets" / "icons"


def chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def png(width, height, pixels):
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        row_start = y * width
        for x in range(width):
            raw.extend(pixels[row_start + x])

    return b"".join([
        b"\x89PNG\r\n\x1a\n",
        chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)),
        chunk(b"IDAT", zlib.compress(bytes(raw), 9)),
        chunk(b"IEND", b""),
    ])


def blend(base, overlay):
    alpha = overlay[3] / 255
    return tuple(int(overlay[i] * alpha + base[i] * (1 - alpha)) for i in range(3)) + (255,)


def inside_round_rect(px, py, x, y, w, h, r):
    dx = max(x - px, 0, px - (x + w))
    dy = max(y - py, 0, py - (y + h))
    if dx == 0 and dy == 0:
        corner_x = min(px - x, x + w - px)
        corner_y = min(py - y, y + h - py)
        if corner_x < r and corner_y < r:
            return (r - corner_x) ** 2 + (r - corner_y) ** 2 <= r ** 2
        return True
    return dx * dx + dy * dy <= r * r


def inside_ellipse(px, py, cx, cy, rx, ry):
    return ((px - cx) / rx) ** 2 + ((py - cy) / ry) ** 2 <= 1


def inside_poly(px, py, points):
    inside = False
    j = len(points) - 1
    for i in range(len(points)):
        xi, yi = points[i]
        xj, yj = points[j]
        intersects = (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi + 1e-9) + xi
        if intersects:
            inside = not inside
        j = i
    return inside


def stroke_near_segment(px, py, ax, ay, bx, by, width):
    vx = bx - ax
    vy = by - ay
    length_sq = vx * vx + vy * vy
    if length_sq == 0:
      return False
    t = max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / length_sq))
    cx = ax + t * vx
    cy = ay + t * vy
    return (px - cx) ** 2 + (py - cy) ** 2 <= (width / 2) ** 2


def make_icon(size, maskable=False):
    bg = (0, 76, 58, 255)
    panel = (0, 102, 77, 255)
    bone = (233, 255, 245, 255)
    glow = (242, 201, 76, 255)
    soft = (242, 201, 76, 72)

    pixels = []
    scale = size / 512
    safe = 58 * scale if maskable else 36 * scale
    panel_rect = (safe, safe, size - safe * 2, size - safe * 2, 56 * scale)
    center = size / 2

    vertebrae = [
        [(219, 118), (293, 118), (311, 149), (294, 179), (219, 179), (201, 149)],
        [(213, 184), (299, 184), (321, 218), (300, 252), (213, 252), (191, 218)],
        [(208, 258), (304, 258), (328, 296), (304, 335), (208, 335), (184, 296)],
        [(203, 346), (309, 346), (340, 390), (303, 432), (209, 432), (172, 390)],
    ]
    vertebrae = [[(x * scale, y * scale) for x, y in poly] for poly in vertebrae]

    for y in range(size):
        for x in range(size):
            px = x + 0.5
            py = y + 0.5
            color = bg

            if inside_round_rect(px, py, *panel_rect):
                color = panel

            if inside_ellipse(px, py, center, center, 170 * scale, 170 * scale):
                color = blend(color, soft)

            for poly in vertebrae:
                if inside_poly(px, py, poly):
                    color = bone

            for poly in vertebrae:
                if any(stroke_near_segment(px, py, *poly[i], *poly[(i + 1) % len(poly)], 10 * scale) for i in range(len(poly))):
                    color = glow

            if (
                stroke_near_segment(px, py, 185 * scale, 150 * scale, 118 * scale, 282 * scale, 15 * scale)
                or stroke_near_segment(px, py, 327 * scale, 150 * scale, 394 * scale, 282 * scale, 15 * scale)
                or stroke_near_segment(px, py, 169 * scale, 391 * scale, 256 * scale, 356 * scale, 15 * scale)
                or stroke_near_segment(px, py, 256 * scale, 356 * scale, 343 * scale, 391 * scale, 15 * scale)
            ):
                color = bone

            for cx, cy, r in [(256, 149, 10), (256, 218, 11), (256, 297, 12), (256, 391, 13)]:
                if inside_ellipse(px, py, cx * scale, cy * scale, r * scale, r * scale):
                    color = glow

            pixels.append(color)

    return png(size, size, pixels)


def main():
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        for version in ("", "-v2", "-v3", "-v4", "-v5"):
            (ICON_DIR / f"icon-{size}{version}.png").write_bytes(make_icon(size))
            (ICON_DIR / f"icon-{size}-maskable{version}.png").write_bytes(make_icon(size, maskable=True))


if __name__ == "__main__":
    main()
