#!/usr/bin/env python3
"""Draw the iPhone icon from v2's US silhouette and its blue/red map colors."""

import json
import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHAPE = ROOT / "v2" / "data" / "ctryshape.js"
OUT = Path(__file__).resolve().parents[1] / "USDistricts" / "Assets.xcassets" / "AppIcon.appiconset" / "AppIcon.png"

PAPER = (221, 221, 221)
WHITE = (255, 255, 255)
BLUE = (37, 99, 235)    # v2 Democratic color
RED = (220, 38, 38)     # v2 Republican color

# North to south, west to east. A coarse district map, not a precinct file.
BANDS = (
    (BLUE, RED, RED, BLUE, BLUE, BLUE),
    (BLUE, RED, RED, RED, BLUE, BLUE),
    (BLUE, RED, RED, RED, RED, RED),
)


def us_rings():
    text = SHAPE.read_text()
    start = text.find('"us":')
    opening = text.find("[", start)
    depth = 0
    for index in range(opening, len(text)):
        char = text[index]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return json.loads(text[opening:index + 1])
    raise SystemExit("US silhouette not found")


def party(lon, lat):
    col = int((lon + 125) / 10)
    col = max(0, min(5, col))
    if lat >= 41:
        row = 0
    elif lat >= 34:
        row = 1
    else:
        row = 2
    return BANDS[row][col]


def project(ring, rect, cos_lat):
    lons = [point[0] for point in ring]
    lats = [point[1] for point in ring]
    lon0, lon1 = min(lons), max(lons)
    lat0, lat1 = min(lats), max(lats)
    span_x = (lon1 - lon0) * cos_lat
    span_y = lat1 - lat0
    rx, ry, rw, rh = rect
    scale = min(rw / span_x, rh / span_y)
    drawn_w = span_x * scale
    ox = rx + (rw - drawn_w) / 2
    oy = ry

    def to_px(lon, lat):
        x = ox + (lon - lon0) * cos_lat * scale
        y = oy + (lat1 - lat) * scale
        return x, y

    def to_ll(x, y):
        lon = lon0 + (x - ox) / (cos_lat * scale)
        lat = lat1 - (y - oy) / scale
        return lon, lat

    return [to_px(lon, lat) for lon, lat in ring], to_ll


def fill(buf, width, pts, color_at):
    ys = [point[1] for point in pts]
    y0 = max(0, int(math.floor(min(ys))))
    y1 = min(width - 1, int(math.ceil(max(ys))))
    count = len(pts)
    for y in range(y0, y1 + 1):
        xs = []
        for index in range(count):
            x1, y1 = pts[index]
            x2, y2 = pts[(index + 1) % count]
            if (y1 <= y < y2) or (y2 <= y < y1):
                if y1 != y2:
                    xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        for index in range(0, len(xs) - 1, 2):
            left = max(0, int(math.ceil(xs[index])))
            right = min(width - 1, int(math.floor(xs[index + 1])))
            for x in range(left, right + 1):
                color = color_at(x, y)
                offset = (y * width + x) * 3
                buf[offset:offset + 3] = bytes(color)


def stroke(buf, width, pts, radius, color):
    count = len(pts)
    radius2 = radius * radius
    for index in range(count):
        x1, y1 = pts[index]
        x2, y2 = pts[(index + 1) % count]
        dist = math.hypot(x2 - x1, y2 - y1)
        steps = max(1, int(dist / 2))
        for step in range(steps + 1):
            t = step / steps
            cx = x1 + (x2 - x1) * t
            cy = y1 + (y2 - y1) * t
            x0 = max(0, int(cx - radius))
            x1b = min(width - 1, int(cx + radius))
            y0 = max(0, int(cy - radius))
            y1b = min(width - 1, int(cy + radius))
            for y in range(y0, y1b + 1):
                dy = y - cy
                for x in range(x0, x1b + 1):
                    if (x - cx) * (x - cx) + dy * dy <= radius2:
                        offset = (y * width + x) * 3
                        buf[offset:offset + 3] = bytes(color)


def downsample(src, size, scale):
    out = bytearray(size * size * 3)
    for y in range(size):
        for x in range(size):
            totals = [0, 0, 0]
            n = 0
            for dy in range(scale):
                for dx in range(scale):
                    offset = ((y * scale + dy) * size * scale + (x * scale + dx)) * 3
                    totals[0] += src[offset]
                    totals[1] += src[offset + 1]
                    totals[2] += src[offset + 2]
                    n += 1
            base = (y * size + x) * 3
            out[base] = totals[0] // n
            out[base + 1] = totals[1] // n
            out[base + 2] = totals[2] // n
    return out


def write_png(path, size, rgb):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + bytes(rgb[y * size * 3:(y + 1) * size * 3]) for y in range(size))
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def main():
    alaska, lower = us_rings()
    scale = 2
    size = 1024 * scale
    buf = bytearray(PAPER) * (size * size)
    lower_pts, lower_ll = project(lower, (140, 70, 1780, 1320), math.cos(math.radians(38)))
    alaska_pts, _ = project(alaska, (120, 1560, 640, 400), math.cos(math.radians(64)))
    fill(buf, size, lower_pts, lambda x, y: party(*lower_ll(x, y)))
    fill(buf, size, alaska_pts, lambda x, y: RED)
    stroke(buf, size, lower_pts, 22, WHITE)
    stroke(buf, size, alaska_pts, 16, WHITE)
    png = downsample(buf, 1024, scale)
    # The middle of the lower 48 should be a district color, not the gray page.
    sample = 1024 * 430 + 512
    pixel = tuple(png[sample * 3:sample * 3 + 3])
    if pixel == PAPER:
        raise SystemExit(f"icon center is still the background {pixel}")
    write_png(OUT, 1024, png)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes), sample {pixel}")


if __name__ == "__main__":
    main()
