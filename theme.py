import math

import cairo
from PIL import Image, ImageTk

WIDTH = 520
HEIGHT = 380
SS = 2  # supersample factor: draw at 2x, downscale with Lanczos for crispness

# Silver retro cassette palette
BODY_LIGHT = (0.84, 0.84, 0.82)
BODY_MID = (0.71, 0.71, 0.69)
BODY_DARK = (0.55, 0.55, 0.53)
WINDOW_BG = (0.11, 0.10, 0.10)
KEY_TOP = (0.34, 0.34, 0.34)
KEY_FACE = (0.16, 0.16, 0.16)
KEY_FACE_DARK = (0.07, 0.07, 0.07)
KEY_RED_TOP = (0.88, 0.26, 0.20)
KEY_RED_FACE = (0.62, 0.10, 0.08)
KEY_RED_DARK = (0.40, 0.06, 0.05)
LABEL_ENGRAVE = (0.24, 0.24, 0.22)

# Hex versions for Tk widgets
BODY_HEX = "#b5b5b2"
BODY_DARK_HEX = "#8c8c87"
WINDOW_HEX = "#1c1a1a"
KEY_HEX = "#262626"
KEY_TEXT = "#d9d9d4"
LABEL_TEXT = "#3a3a38"
WINDOW_TEXT = "#e8e4d8"
ACCENT = "#b82119"

FONT_TITLE = ("Courier New", 11, "bold")
FONT_LABEL = ("Courier New", 8, "bold")
FONT_TRACK = ("Courier New", 10, "bold")

# Layout: one MARGIN drives side spacing so everything lines up as a column
MARGIN = 24
WIN_X0, WIN_X1 = MARGIN, WIDTH - MARGIN
WIN_Y0, WIN_Y1 = 56, 234
TRACK_CX = WIDTH / 2
TRACK_Y = WIN_Y0 + 12

# reels sit at the quarter points of the window, symmetric about center
REEL_L_CX = WIN_X0 + (WIN_X1 - WIN_X0) * 0.25
REEL_R_CX = WIN_X0 + (WIN_X1 - WIN_X0) * 0.75
REEL_CY = 152
REEL_SIZE = 100
REEL_FRAMES = 48

# Key row: same width and edges as the cassette window above
KEY_LABELS = ["SHUFFLE", "PLAY", "REW", "F.FWD", "MUTE", "STOP"]
N_KEYS = len(KEY_LABELS)
KEY_GAP = 4
KEY_H = 102
KEY_W = ((WIN_X1 - WIN_X0) - (N_KEYS - 1) * KEY_GAP) / N_KEYS
KEYS_X0 = WIN_X0
KEYS_BOTTOM = HEIGHT - 6
KEYS_CY = KEYS_BOTTOM - KEY_H / 2
STRIP_Y = KEYS_BOTTOM - KEY_H - 12


def key_x(i):
    return KEYS_X0 + i * (KEY_W + KEY_GAP) + KEY_W / 2


def _new_ctx(w, h):
    """Supersampled surface + context scaled so drawing uses logical coords."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(w * SS), int(h * SS))
    ctx = cairo.Context(surface)
    ctx.scale(SS, SS)
    return surface, ctx


def _surface_to_pil(surface):
    buf = surface.get_data()
    img = Image.frombuffer(
        "RGBA", (surface.get_width(), surface.get_height()), buf, "raw", "BGRA", 0, 1
    )
    return img.copy()


def _finish(surface, w, h):
    """Downscale a supersampled surface to logical size, return PhotoImage."""
    surface.flush()
    img = _surface_to_pil(surface).resize((int(w), int(h)), Image.LANCZOS)
    return ImageTk.PhotoImage(img)


def _rounded_rect(ctx, x, y, w, h, r):
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def _grille(ctx, x0, y0, cols, rows):
    """Recessed speaker grille: inset panel w/ inner shadow, punched holes."""
    pitch = 9
    pad = 8
    w = (cols - 1) * pitch + pad * 2
    h = (rows - 1) * pitch + pad * 2

    # recess
    _rounded_rect(ctx, x0 - pad, y0 - pad, w, h, 5)
    grad = cairo.LinearGradient(0, y0 - pad, 0, y0 - pad + h)
    grad.add_color_stop_rgb(0, 0.52, 0.52, 0.50)
    grad.add_color_stop_rgb(0.35, 0.62, 0.62, 0.60)
    grad.add_color_stop_rgb(1, 0.66, 0.66, 0.64)
    ctx.set_source(grad)
    ctx.fill()
    # inner shadow at top of recess
    _rounded_rect(ctx, x0 - pad, y0 - pad, w, h, 5)
    ctx.save()
    ctx.clip()
    sh = cairo.LinearGradient(0, y0 - pad, 0, y0 - pad + 6)
    sh.add_color_stop_rgba(0, 0, 0, 0, 0.35)
    sh.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(sh)
    ctx.rectangle(x0 - pad, y0 - pad, w, 6)
    ctx.fill()
    ctx.restore()
    # bottom edge highlight of recess
    ctx.set_source_rgba(1, 1, 1, 0.35)
    ctx.set_line_width(1)
    ctx.move_to(x0 - pad + 4, y0 - pad + h - 0.5)
    ctx.line_to(x0 - pad + w - 4, y0 - pad + h - 0.5)
    ctx.stroke()

    # punched holes: dark hole + light lower-edge glint
    for row in range(rows):
        for col in range(cols):
            hx, hy = x0 + col * pitch, y0 + row * pitch
            ctx.set_source_rgba(1, 1, 1, 0.30)
            ctx.arc(hx, hy + 0.9, 2.0, 0, 2 * math.pi)
            ctx.fill()
            hole = cairo.RadialGradient(hx, hy - 0.5, 0.3, hx, hy, 2.0)
            hole.add_color_stop_rgb(0, 0.10, 0.10, 0.09)
            hole.add_color_stop_rgb(1, 0.22, 0.22, 0.21)
            ctx.set_source(hole)
            ctx.arc(hx, hy, 2.0, 0, 2 * math.pi)
            ctx.fill()


def render_body(width=WIDTH, height=HEIGHT):
    """Silver cassette-deck body. Runs flush to the window edge — no border."""
    surface, ctx = _new_ctx(width, height)

    # base plastic: vertical gradient, brightest just above mid
    grad = cairo.LinearGradient(0, 0, 0, height)
    grad.add_color_stop_rgb(0.00, *BODY_MID)
    grad.add_color_stop_rgb(0.10, *BODY_LIGHT)
    grad.add_color_stop_rgb(0.55, *BODY_MID)
    grad.add_color_stop_rgb(1.00, *BODY_DARK)
    ctx.set_source(grad)
    ctx.rectangle(0, 0, width, height)
    ctx.fill()

    # faint vignette on left/right edges for roundness
    for x_edge, flip in ((0, 1), (width, -1)):
        vg = cairo.LinearGradient(x_edge, 0, x_edge + flip * 26, 0)
        vg.add_color_stop_rgba(0, 0, 0, 0, 0.14)
        vg.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(vg)
        ctx.rectangle(min(x_edge, x_edge + flip * 26), 0, 26, height)
        ctx.fill()

    # brushed plastic: very subtle horizontal micro-lines
    ctx.set_line_width(0.7)
    for y in range(0, height, 2):
        ctx.set_source_rgba(1, 1, 1, 0.016)
        ctx.move_to(0, y + 0.5)
        ctx.line_to(width, y + 0.5)
        ctx.stroke()

    # twin speaker grilles, aligned to the same side margins as the window
    _grille(ctx, WIN_X0 + 8, 22, 12, 3)
    _grille(ctx, WIN_X1 - 8 - 11 * 9, 22, 12, 3)

    # --- cassette window: recessed smoked glass ---
    # drop shadow below the recess lip
    _rounded_rect(ctx, WIN_X0 - 1.5, WIN_Y0 - 1, WIN_X1 - WIN_X0 + 3, WIN_Y1 - WIN_Y0 + 4, 13)
    ctx.set_source_rgba(0, 0, 0, 0.22)
    ctx.fill()

    _rounded_rect(ctx, WIN_X0, WIN_Y0, WIN_X1 - WIN_X0, WIN_Y1 - WIN_Y0, 12)
    win_grad = cairo.LinearGradient(0, WIN_Y0, 0, WIN_Y1)
    win_grad.add_color_stop_rgb(0.0, WINDOW_BG[0] + 0.06, WINDOW_BG[1] + 0.06, WINDOW_BG[2] + 0.06)
    win_grad.add_color_stop_rgb(0.5, *WINDOW_BG)
    win_grad.add_color_stop_rgb(1.0, WINDOW_BG[0] + 0.02, WINDOW_BG[1] + 0.02, WINDOW_BG[2] + 0.02)
    ctx.set_source(win_grad)
    ctx.fill()

    _rounded_rect(ctx, WIN_X0, WIN_Y0, WIN_X1 - WIN_X0, WIN_Y1 - WIN_Y0, 12)
    ctx.save()
    ctx.clip()
    # inner shadow: top and left, glass sits below the lip
    sh = cairo.LinearGradient(0, WIN_Y0, 0, WIN_Y0 + 14)
    sh.add_color_stop_rgba(0, 0, 0, 0, 0.55)
    sh.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(sh)
    ctx.rectangle(WIN_X0, WIN_Y0, WIN_X1 - WIN_X0, 14)
    ctx.fill()
    shl = cairo.LinearGradient(WIN_X0, 0, WIN_X0 + 10, 0)
    shl.add_color_stop_rgba(0, 0, 0, 0, 0.35)
    shl.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(shl)
    ctx.rectangle(WIN_X0, WIN_Y0, 10, WIN_Y1 - WIN_Y0)
    ctx.fill()
    # diagonal glass reflection sweep
    ctx.set_source_rgba(1, 1, 1, 0.04)
    ctx.move_to(WIN_X0 + 60, WIN_Y0)
    ctx.line_to(WIN_X0 + 190, WIN_Y0)
    ctx.line_to(WIN_X0 + 90, WIN_Y1)
    ctx.line_to(WIN_X0 - 40, WIN_Y1)
    ctx.close_path()
    ctx.fill()

    # reel wells: recessed circles w/ soft edge gradient
    for cx in (REEL_L_CX, REEL_R_CX):
        well = cairo.RadialGradient(cx, REEL_CY, REEL_SIZE / 2 - 8, cx, REEL_CY, REEL_SIZE / 2 + 8)
        well.add_color_stop_rgba(0, 0, 0, 0.60, 1)
        well.add_color_stop_rgba(0, 0, 0, 0, 0.60)
        ctx.set_source_rgba(0, 0, 0, 0.5)
        ctx.arc(cx, REEL_CY, REEL_SIZE / 2 + 7, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.05)
        ctx.set_line_width(1.2)
        ctx.arc(cx, REEL_CY, REEL_SIZE / 2 + 7, math.pi * 0.15, math.pi * 0.85)
        ctx.stroke()
    ctx.restore()

    # bottom lip highlight under the window
    ctx.set_source_rgba(1, 1, 1, 0.30)
    ctx.set_line_width(1.2)
    ctx.move_to(WIN_X0 + 8, WIN_Y1 + 1.5)
    ctx.line_to(WIN_X1 - 8, WIN_Y1 + 1.5)
    ctx.stroke()

    # --- key bed: recessed tray, same width as window ---
    bed_y = STRIP_Y + 8
    _rounded_rect(ctx, WIN_X0, bed_y, WIN_X1 - WIN_X0, height - bed_y + 10, 8)
    bed = cairo.LinearGradient(0, bed_y, 0, height)
    bed.add_color_stop_rgb(0, 0.30, 0.30, 0.28)
    bed.add_color_stop_rgb(1, 0.24, 0.24, 0.22)
    ctx.set_source(bed)
    ctx.fill()
    # inner shadow at tray top
    _rounded_rect(ctx, WIN_X0, bed_y, WIN_X1 - WIN_X0, height - bed_y + 10, 8)
    ctx.save()
    ctx.clip()
    tsh = cairo.LinearGradient(0, bed_y, 0, bed_y + 8)
    tsh.add_color_stop_rgba(0, 0, 0, 0, 0.45)
    tsh.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(tsh)
    ctx.rectangle(WIN_X0, bed_y, WIN_X1 - WIN_X0, 8)
    ctx.fill()
    ctx.restore()

    # engraved key labels above keys
    ctx.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(9.5)
    for i, label in enumerate(KEY_LABELS):
        ext = ctx.text_extents(label)
        tx = key_x(i) - ext.width / 2
        ctx.set_source_rgba(1, 1, 1, 0.55)
        ctx.move_to(tx, STRIP_Y + 1)
        ctx.show_text(label)
        ctx.set_source_rgb(*LABEL_ENGRAVE)
        ctx.move_to(tx, STRIP_Y)
        ctx.show_text(label)

    return _finish(surface, width, height)


def render_reel_frames(size=REEL_SIZE, n_frames=REEL_FRAMES):
    """Pre-render spinning reel frames. Rotation happens at supersampled
    resolution, downscale per frame — crisp edges at any angle."""
    base_hi = _render_reel_base_hi(size)  # PIL image at size*SS
    frames = []
    for i in range(n_frames):
        angle = 360.0 * i / n_frames
        rotated = base_hi.rotate(-angle, resample=Image.BICUBIC)
        small = rotated.resize((size, size), Image.LANCZOS)
        frames.append(ImageTk.PhotoImage(small))
    return frames


def _render_reel_base_hi(size):
    """Cassette reel: dark tape pack w/ sheen rings + metallic hub w/ 6 teeth.
    Returned at supersampled resolution for rotation."""
    surface, ctx = _new_ctx(size, size)
    cx = cy = size / 2
    r = size / 2 - 1

    # tape pack: radial gradient, darker at rim
    tape = cairo.RadialGradient(cx, cy, r * 0.30, cx, cy, r)
    tape.add_color_stop_rgb(0, 0.32, 0.20, 0.11)
    tape.add_color_stop_rgb(0.75, 0.22, 0.14, 0.075)
    tape.add_color_stop_rgb(1, 0.15, 0.09, 0.05)
    ctx.set_source(tape)
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.fill()

    # wound-tape sheen: many fine concentric rings, alternating light/dark
    ctx.set_line_width(0.6)
    ring_r = r * 0.50
    i = 0
    while ring_r < r - 1.5:
        if i % 2 == 0:
            ctx.set_source_rgba(1, 1, 1, 0.045)
        else:
            ctx.set_source_rgba(0, 0, 0, 0.10)
        ctx.arc(cx, cy, ring_r, 0, 2 * math.pi)
        ctx.stroke()
        ring_r += 1.6
        i += 1

    # broad soft sheen band on the pack
    ctx.set_source_rgba(1, 1, 1, 0.05)
    ctx.set_line_width(r * 0.16)
    ctx.arc(cx, cy, r * 0.72, 0, 2 * math.pi)
    ctx.stroke()

    # hub outer ring: metallic
    hub_r = r * 0.44
    ring = cairo.RadialGradient(cx - hub_r * 0.3, cy - hub_r * 0.3, hub_r * 0.2, cx, cy, hub_r)
    ring.add_color_stop_rgb(0, 0.98, 0.97, 0.94)
    ring.add_color_stop_rgb(0.7, 0.88, 0.87, 0.84)
    ring.add_color_stop_rgb(1, 0.72, 0.71, 0.68)
    ctx.set_source(ring)
    ctx.arc(cx, cy, hub_r, 0, 2 * math.pi)
    ctx.fill()
    # hub rim line
    ctx.set_source_rgba(0, 0, 0, 0.35)
    ctx.set_line_width(1)
    ctx.arc(cx, cy, hub_r, 0, 2 * math.pi)
    ctx.stroke()

    # inner well of hub
    well_r = hub_r * 0.80
    well = cairo.RadialGradient(cx, cy, well_r * 0.2, cx, cy, well_r)
    well.add_color_stop_rgb(0, 0.80, 0.79, 0.76)
    well.add_color_stop_rgb(1, 0.62, 0.61, 0.58)
    ctx.set_source(well)
    ctx.arc(cx, cy, well_r, 0, 2 * math.pi)
    ctx.fill()

    # 6 sprocket teeth pointing inward from hub ring
    ctx.set_source_rgb(0.13, 0.12, 0.12)
    for i in range(6):
        a = i * math.pi / 3
        tx = cx + math.cos(a) * well_r * 0.72
        ty = cy + math.sin(a) * well_r * 0.72
        ctx.save()
        ctx.translate(tx, ty)
        ctx.rotate(a)
        _rounded_rect(ctx, -2.6, -6.5, 5.2, 13, 2)
        ctx.fill()
        ctx.restore()

    # center hole with slight bevel
    ctx.set_source_rgba(0, 0, 0, 0.30)
    ctx.arc(cx, cy + 0.6, well_r * 0.30, 0, 2 * math.pi)
    ctx.fill()
    ctx.set_source_rgb(0.10, 0.09, 0.09)
    ctx.arc(cx, cy, well_r * 0.28, 0, 2 * math.pi)
    ctx.fill()

    # specular glint top-left of hub
    ctx.set_source_rgba(1, 1, 1, 0.30)
    ctx.set_line_width(1.4)
    ctx.arc(cx, cy, hub_r * 0.92, math.pi * 1.05, math.pi * 1.45)
    ctx.stroke()

    surface.flush()
    return _surface_to_pil(surface)


def render_key(label, red=False, pressed=False, w=KEY_W, h=KEY_H):
    """Cassette piano-key: stepped cap + tall front face, drop shadow,
    side shading. Pressed: shifted down, darkened, inner top shadow."""
    w, h = int(w), int(h)
    surface, ctx = _new_ctx(w, h)

    top_c = KEY_RED_TOP if red else KEY_TOP
    face_c = KEY_RED_FACE if red else KEY_FACE
    dark_c = KEY_RED_DARK if red else KEY_FACE_DARK

    inset = 2.5
    press_shift = 4 if pressed else 0
    cap_h = 18
    kx, kw = inset, w - inset * 2
    ky = inset + press_shift
    kh = h - inset * 2 - press_shift

    # drop shadow under the key (soft, two layers)
    if not pressed:
        _rounded_rect(ctx, kx + 1, ky + 3, kw, kh, 5)
        ctx.set_source_rgba(0, 0, 0, 0.18)
        ctx.fill()
        _rounded_rect(ctx, kx + 0.5, ky + 1.5, kw, kh, 5)
        ctx.set_source_rgba(0, 0, 0, 0.14)
        ctx.fill()

    # front face
    base = dark_c if pressed else face_c
    _rounded_rect(ctx, kx, ky, kw, kh, 5)
    face = cairo.LinearGradient(kx, 0, kx + kw, 0)
    edge = tuple(c * 0.50 for c in base)
    face.add_color_stop_rgb(0.00, *edge)
    face.add_color_stop_rgb(0.10, *base)
    face.add_color_stop_rgb(0.90, *base)
    face.add_color_stop_rgb(1.00, *edge)
    ctx.set_source(face)
    ctx.fill()

    # vertical shading on face: slightly lighter high, darker low
    _rounded_rect(ctx, kx, ky, kw, kh, 5)
    ctx.save()
    ctx.clip()
    vsh = cairo.LinearGradient(0, ky, 0, ky + kh)
    vsh.add_color_stop_rgba(0, 1, 1, 1, 0.06)
    vsh.add_color_stop_rgba(0.5, 0, 0, 0, 0)
    vsh.add_color_stop_rgba(1, 0, 0, 0, 0.22)
    ctx.set_source(vsh)
    ctx.rectangle(kx, ky, kw, kh)
    ctx.fill()

    # stepped cap
    cap = cairo.LinearGradient(0, ky, 0, ky + cap_h)
    if pressed:
        cap.add_color_stop_rgb(0, *tuple(c * 0.7 for c in top_c))
    else:
        cap.add_color_stop_rgb(0, *top_c)
    cap.add_color_stop_rgb(1, *base)
    ctx.set_source(cap)
    ctx.rectangle(kx, ky, kw, cap_h)
    ctx.fill()

    # cap top highlight
    ctx.set_source_rgba(1, 1, 1, 0.10 if pressed else 0.35)
    ctx.set_line_width(1.2)
    ctx.move_to(kx + 3, ky + 1)
    ctx.line_to(kx + kw - 3, ky + 1)
    ctx.stroke()

    # pressed: inner shadow at top (finger pushed key under the bed lip)
    if pressed:
        ish = cairo.LinearGradient(0, ky, 0, ky + 10)
        ish.add_color_stop_rgba(0, 0, 0, 0, 0.55)
        ish.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(ish)
        ctx.rectangle(kx, ky, kw, 10)
        ctx.fill()
    ctx.restore()

    # label text on front face
    ctx.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(9)
    lines = label.split("\n")
    text_cy = ky + cap_h + (kh - cap_h) / 2
    line_h = 12
    y0 = text_cy - (len(lines) - 1) * line_h / 2 + 3
    for j, line in enumerate(lines):
        ext = ctx.text_extents(line)
        ctx.set_source_rgba(0, 0, 0, 0.55)
        ctx.move_to(w / 2 - ext.width / 2 + 0.8, y0 + j * line_h + 0.8)
        ctx.show_text(line)
        ctx.set_source_rgb(0.87, 0.87, 0.84)
        ctx.move_to(w / 2 - ext.width / 2, y0 + j * line_h)
        ctx.show_text(line)

    return _finish(surface, w, h)


if __name__ == "__main__":
    import tkinter as tk

    root = tk.Tk()
    root.title("theme test")
    root.geometry(f"{WIDTH}x{HEIGHT}")
    canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, highlightthickness=0)
    canvas.pack()
    body = render_body()
    canvas.create_image(0, 0, image=body, anchor="nw")
    frames = render_reel_frames()
    canvas.create_image(REEL_L_CX, REEL_CY, image=frames[0])
    canvas.create_image(REEL_R_CX, REEL_CY, image=frames[0])
    keys = [render_key(l, red=(i == 0)) for i, l in
            enumerate(["SHUFFLE", "PLAY\nPAUSE", "REW", "F.FWD", "MUTE", "STOP\nEJECT"])]
    for i, k in enumerate(keys):
        canvas.create_image(key_x(i), KEYS_CY, image=k)
    root.mainloop()
