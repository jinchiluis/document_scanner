import html
import socket
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response

from config import BACKEND_DIR


router = APIRouter(prefix="/api/runtime")


def _local_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return socket.gethostbyname(socket.gethostname())


def _ssl_available() -> bool:
    return (BACKEND_DIR / "cert.pem").exists() and (BACKEND_DIR / "key.pem").exists()


def desktop_url() -> str:
    return "http://localhost:8000/desktop"


def phone_scan_url() -> str:
    scheme = "https" if _ssl_available() else "http"
    port = 8443 if _ssl_available() else 8000
    return f"{scheme}://{_local_ip()}:{port}/scan"


@router.get("/urls")
async def runtime_urls():
    return JSONResponse(
        {
            "desktop_url": desktop_url(),
            "phone_scan_url": phone_scan_url(),
            "phone_uses_https": _ssl_available(),
        }
    )


@router.get("/phone-qr.svg")
async def phone_qr_svg():
    return Response(
        _qr_svg(phone_scan_url()),
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store"},
    )


def _qr_svg(text: str) -> str:
    modules = _qr_matrix(text)
    quiet = 4
    size = len(modules)
    total = size + quiet * 2
    rects = []

    for y, row in enumerate(modules):
        for x, dark in enumerate(row):
            if dark:
                rects.append(f'<rect x="{x + quiet}" y="{y + quiet}" width="1" height="1"/>')

    escaped = html.escape(text, quote=True)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" '
        f'role="img" aria-label="QR code for {escaped}">'
        '<rect width="100%" height="100%" fill="#fff"/>'
        f'<g fill="#111827">{"".join(rects)}</g>'
        "</svg>"
    )


def _qr_matrix(text: str) -> list[list[bool]]:
    data = text.encode("utf-8")
    version = 4
    size = 21 + 4 * (version - 1)
    data_codewords = 80
    ec_codewords = 20

    if len(data) > 78:
        raise ValueError("Phone scanner URL is too long for the built-in QR generator.")

    bits: list[int] = []
    _append_bits(bits, 0b0100, 4)
    _append_bits(bits, len(data), 8)
    for byte in data:
        _append_bits(bits, byte, 8)
    _append_bits(bits, 0, min(4, data_codewords * 8 - len(bits)))
    while len(bits) % 8:
        bits.append(0)

    codewords = [
        sum(bits[index + bit] << (7 - bit) for bit in range(8))
        for index in range(0, len(bits), 8)
    ]
    pad = 0xEC
    while len(codewords) < data_codewords:
        codewords.append(pad)
        pad ^= 0xEC ^ 0x11

    all_codewords = codewords + _reed_solomon_remainder(codewords, ec_codewords)
    data_bits = [
        (byte >> bit) & 1
        for byte in all_codewords
        for bit in range(7, -1, -1)
    ]

    modules: list[list[bool | None]] = [[None for _ in range(size)] for _ in range(size)]
    function: list[list[bool]] = [[False for _ in range(size)] for _ in range(size)]

    def set_function(x: int, y: int, dark: bool) -> None:
        modules[y][x] = dark
        function[y][x] = True

    def finder(x: int, y: int) -> None:
        for dy in range(-1, 8):
            for dx in range(-1, 8):
                xx = x + dx
                yy = y + dy
                if 0 <= xx < size and 0 <= yy < size:
                    dark = (
                        0 <= dx <= 6
                        and 0 <= dy <= 6
                        and (dx in (0, 6) or dy in (0, 6) or (2 <= dx <= 4 and 2 <= dy <= 4))
                    )
                    set_function(xx, yy, dark)

    finder(0, 0)
    finder(size - 7, 0)
    finder(0, size - 7)

    for i in range(size):
        if not function[6][i]:
            set_function(i, 6, i % 2 == 0)
        if not function[i][6]:
            set_function(6, i, i % 2 == 0)

    for center_y in (6, 26):
        for center_x in (6, 26):
            if function[center_y][center_x]:
                continue
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    set_function(
                        center_x + dx,
                        center_y + dy,
                        max(abs(dx), abs(dy)) != 1,
                    )

    set_function(8, 4 * version + 9, True)
    format_coords = [
        (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
        (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8),
        (size - 1, 8), (size - 2, 8), (size - 3, 8), (size - 4, 8),
        (size - 5, 8), (size - 6, 8), (size - 7, 8), (size - 8, 8),
        (8, size - 7), (8, size - 6), (8, size - 5), (8, size - 4),
        (8, size - 3), (8, size - 2), (8, size - 1),
    ]
    for xx, yy in format_coords:
        function[yy][xx] = True
        if modules[yy][xx] is None:
            modules[yy][xx] = False

    bit_index = 0
    direction = -1
    x = size - 1
    while x > 0:
        if x == 6:
            x -= 1
        y_range = range(size - 1, -1, -1) if direction == -1 else range(size)
        for y in y_range:
            for xx in (x, x - 1):
                if function[y][xx]:
                    continue
                dark = bit_index < len(data_bits) and data_bits[bit_index] == 1
                if (xx + y) % 2 == 0:
                    dark = not dark
                modules[y][xx] = dark
                bit_index += 1
        direction *= -1
        x -= 2

    format_bits = _format_bits(ecl_bits=1, mask=0)
    first_format_coords = [
        (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
        (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8),
    ]
    second_format_coords = [
        (size - 1, 8), (size - 2, 8), (size - 3, 8), (size - 4, 8),
        (size - 5, 8), (size - 6, 8), (size - 7, 8), (size - 8, 8),
        (8, size - 7), (8, size - 6), (8, size - 5), (8, size - 4),
        (8, size - 3), (8, size - 2), (8, size - 1),
    ]
    for i in range(15):
        dark = ((format_bits >> i) & 1) == 1
        a = first_format_coords[i]
        b = second_format_coords[i]
        modules[a[1]][a[0]] = dark
        modules[b[1]][b[0]] = dark

    return [[bool(cell) for cell in row] for row in modules]


def _append_bits(bits: list[int], value: int, length: int) -> None:
    for i in range(length - 1, -1, -1):
        bits.append((value >> i) & 1)


def _format_bits(ecl_bits: int, mask: int) -> int:
    data = (ecl_bits << 3) | mask
    rem = data << 10
    for i in range(14, 9, -1):
        if (rem >> i) & 1:
            rem ^= 0x537 << (i - 10)
    return ((data << 10) | rem) ^ 0x5412


def _reed_solomon_remainder(data: list[int], degree: int) -> list[int]:
    generator = [1]
    for i in range(degree):
        generator = _poly_multiply(generator, [1, _gf_pow(2, i)])

    result = [0] * degree
    for byte in data:
        factor = byte ^ result.pop(0)
        result.append(0)
        for i, coefficient in enumerate(generator[1:]):
            result[i] ^= _gf_multiply(coefficient, factor)
    return result


def _poly_multiply(left: list[int], right: list[int]) -> list[int]:
    result = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            result[i + j] ^= _gf_multiply(a, b)
    return result


def _gf_multiply(x: int, y: int) -> int:
    result = 0
    while y:
        if y & 1:
            result ^= x
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
        y >>= 1
    return result


def _gf_pow(x: int, power: int) -> int:
    result = 1
    for _ in range(power):
        result = _gf_multiply(result, x)
    return result
