"""
Generator Master Dokumen FigCraft: `design/00 - desi private.figcraft`
Gaya: Anti-Slop Minimalist Editorial, Full-Bleed Photo Fade (Teks Langsung Tanpa Card),
      Ikon Vektor Presisi (Stroke 1.75px Rounded), Logo Resmi Brand, & Interactive Transitions
Audiens: Gen Boomer & Gen Milenial (Nyaman dibaca, kontras tinggi, bebas em dash)

Palet:
  - Primary   : #0093D6 (Cerulean Sky) | Dark #0072A8 | Soft #EBF7FD | Deep #083A54
  - Secondary : #A66B37 (Warm Caramel) | Hover #8A5629 | Soft #F7F7F5
  - Tertiary  : #111827 (Ink) | #374151 (Body) | #6B7280 (Muted) | #F7F7F5 (Alabaster) | #FFFFFF | #E5E7EB

Mencakup 8 Halaman FigCraft: 1 Design System + seluruh 52 template halaman di `templates/`.
TIDAK mengekspor PNG.
"""
import json
import math
import os
import re
from pathlib import Path

FONT_HEAD = "Plus Jakarta Sans"
FONT_BODY = "DM Sans"

HERO_DIR = Path(r"c:\Users\Coding\04 - Desi Private\static\images\hero")
CLIENT_DIR = Path(r"c:\Users\Coding\04 - Desi Private\static\images\client")

PRIMARY = "#0093D6"
PRIMARY_DARK = "#0072A8"
PRIMARY_SOFT = "#EBF7FD"
PRIMARY_BORDER = "#BAE4F8"
PRIMARY_DEEP = "#083A54"

SECONDARY = "#A66B37"
SECONDARY_DARK = "#8A5629"
SECONDARY_SOFT = "#F7F7F5"
SECONDARY_BORDER = "#E5E7EB"

INK = "#111827"
BODY = "#374151"
MUTED = "#6B7280"
ALABASTER = "#F7F7F5"
SURFACE = "#FFFFFF"
SUBTLE_BG = "#F3F4F6"
HAIRLINE = "#E5E7EB"

OK_BG = "#ECFDF5"
OK_TXT = "#15803D"
DANGER_BG = "#FEF2F2"
DANGER_TXT = "#B91C1C"


# ==============================================================================
# CRISP 24x24 LUCIDE-STYLE VECTOR ICON PATHS (PURE M/L/H/V/C/Q/Z FOR EXACT SCALING)
# ==============================================================================
def _circle_path(cx, cy, r):
    k = 0.5522847498 * r
    return (
        f"M {cx} {cy - r} "
        f"C {cx + k} {cy - r} {cx + r} {cy - k} {cx + r} {cy} "
        f"C {cx + r} {cy + k} {cx + k} {cy + r} {cx} {cy + r} "
        f"C {cx - k} {cy + r} {cx - r} {cy + k} {cx - r} {cy} "
        f"C {cx - r} {cy - k} {cx - k} {cy - r} {cx} {cy - r} Z"
    )


def _rrect_path(x, y, w, h, r=2):
    r = min(r, w / 2, h / 2)
    return (
        f"M {x + r} {y} L {x + w - r} {y} Q {x + w} {y} {x + w} {y + r} "
        f"L {x + w} {y + h - r} Q {x + w} {y + h} {x + w - r} {y + h} "
        f"L {x + r} {y + h} Q {x} {y + h} {x} {y + h - r} "
        f"L {x} {y + r} Q {x} {y} {x + r} {y} Z"
    )


ICONS = {
    "dashboard": [
        _rrect_path(3, 3, 7, 9, 1.5),
        _rrect_path(14, 3, 7, 5, 1.5),
        _rrect_path(14, 12, 7, 9, 1.5),
        _rrect_path(3, 16, 7, 5, 1.5),
    ],
    "calendar": [
        _rrect_path(3, 4, 18, 17, 2.2),
        "M 16 2 L 16 6",
        "M 8 2 L 8 6",
        "M 3 10 L 21 10",
    ],
    "calendar-check": [
        _rrect_path(3, 4, 18, 17, 2.2),
        "M 16 2 L 16 6 M 8 2 L 8 6 M 3 10 L 21 10",
        "M 9 15 L 11 17 L 15 13",
    ],
    "users": [
        _circle_path(9, 7, 3.5),
        "M 2 20 C 2 16.5 5.2 14.5 9 14.5 C 12.8 14.5 16 16.5 16 20",
        "M 16 4.5 C 18.2 5.2 19.2 8 17.5 10",
        "M 18.5 14.8 C 20.8 15.6 22 17.4 22 20",
    ],
    "family": [
        _circle_path(8.5, 7.5, 3.2),
        "M 2.5 20 C 2.5 16.8 5.2 14.8 8.5 14.8 C 11.8 14.8 14.5 16.8 14.5 20",
        _circle_path(17, 9.5, 2.5),
        "M 15.5 20 C 16 17.4 18 16 21.5 16",
    ],
    "mentor": [
        _circle_path(9, 7.5, 3.5),
        "M 2 20 C 2 16.5 5 14.5 9 14.5 C 12.5 14.5 15 16.2 15.5 19.2",
        "M 16 11 L 18 13 L 22 9",
    ],
    "graduation": [
        "M 2 10 L 12 5 L 22 10 L 12 15 Z",
        "M 6 12 L 6 17.5 C 9 20 15 20 18 17.5 L 18 12",
        "M 22 10 L 22 16",
    ],
    "book": [
        "M 4 19.5 L 4 4.5 Q 4 2.5 6.5 2.5 L 20 2.5 L 20 21.5 L 6.5 21.5 Q 4 21.5 4 19.5 Z",
        "M 7.5 2.5 L 7.5 21.5 M 11 7 L 16.5 7 M 11 11 L 16.5 11",
    ],
    "receipt": [
        "M 4 2 L 4 22 L 6.5 20.5 L 9 22 L 12 20.5 L 15 22 L 17.5 20.5 L 20 22 L 20 2 L 17.5 3.5 L 15 2 L 12 3.5 L 9 2 L 6.5 3.5 Z",
        "M 8 8 L 16 8 M 8 12 L 16 12 M 8 16 L 13 16",
    ],
    "credit-card": [
        _rrect_path(2, 5, 20, 14, 2.2),
        "M 2 10 L 22 10 M 6 15 L 10 15",
    ],
    "wallet": [
        _rrect_path(2, 5, 20, 15, 2.2),
        "M 16 12.5 C 16 11.4 16.9 10.5 18 10.5 L 22 10.5 L 22 14.5 L 18 14.5 C 16.9 14.5 16 13.6 16 12.5 Z",
        "M 6 5 L 17 2.5 L 19 5",
    ],
    "key": [
        _circle_path(7.5, 16, 4.5),
        "M 11 12.5 L 20.5 3 M 17.5 6 L 20.5 9 M 15 8.5 L 17.5 11",
    ],
    "bell": [
        "M 6 9 C 6 5.5 8.7 3 12 3 C 15.3 3 18 5.5 18 9 C 18 14.5 20.5 16.5 20.5 16.5 L 3.5 16.5 C 3.5 16.5 6 14.5 6 9 Z",
        "M 10 19.5 C 10.5 21 13.5 21 14 19.5",
    ],
    "report": [
        "M 14 2 L 6 2 Q 4 2 4 4 L 4 20 Q 4 22 6 22 L 18 22 Q 20 22 20 20 L 20 8 Z",
        "M 14 2 L 14 8 L 20 8 M 8 13 L 16 13 M 8 17 L 14 17",
    ],
    "history": [
        "M 3 12 C 3 7 7 3 12 3 C 17 3 21 7 21 12 C 21 17 17 21 12 21 C 8.5 21 5.5 19 4 16",
        "M 3 7 L 3 12 L 8 12",
        "M 12 7 L 12 12 L 15.5 14",
    ],
    "backup": [
        "M 17 21 L 5 21 Q 3 21 3 19 L 3 5 Q 3 3 5 3 L 16 3 L 21 8 L 21 19 Q 21 21 19 21 Z",
        "M 7 21 L 7 13 L 17 13 L 17 21 M 7 3 L 7 8 L 15 8",
    ],
    "home": [
        "M 3 10 L 12 3 L 21 10 L 21 20 Q 21 21 20 21 L 4 21 Q 3 21 3 20 Z",
        "M 9 21 L 9 13 L 15 13 L 15 21",
    ],
    "clock": [
        _circle_path(12, 12, 9.5),
        "M 12 7 L 12 12 L 15.5 14",
    ],
    "check": [
        _circle_path(12, 12, 9.5),
        "M 8.5 12.2 L 11 14.8 L 16 9.5",
    ],
    "alert": [
        "M 12 3 L 21.5 19.5 L 2.5 19.5 Z",
        "M 12 9 L 12 13.5",
        _circle_path(12, 16.5, 0.8),
    ],
    "search": [
        _circle_path(10.5, 10.5, 6.8),
        "M 15.6 15.6 L 21 21",
    ],
    "plus": [
        "M 12 5 L 12 19 M 5 12 L 19 12",
    ],
    "arrow-right": [
        "M 5 12 L 19 12 M 13 6 L 19 12 L 13 18",
    ],
    "arrow-left": [
        "M 19 12 L 5 12 M 11 6 L 5 12 L 11 18",
    ],
    "arrow-up": [
        "M 12 19 L 12 5 M 5 12 L 12 5 L 19 12",
    ],
    "lock": [
        _rrect_path(4, 11, 16, 10, 2),
        "M 7.5 11 L 7.5 7.5 C 7.5 4.8 9.5 3 12 3 C 14.5 3 16.5 4.8 16.5 7.5 L 16.5 11",
    ],
    "user": [
        _circle_path(12, 7.5, 3.8),
        "M 4.5 20.5 C 4.5 16.8 7.8 14.5 12 14.5 C 16.2 14.5 19.5 16.8 19.5 20.5",
    ],
    "eye": [
        "M 2 12 C 5 6.8 8.5 5 12 5 C 15.5 5 19 6.8 22 12 C 19 17.2 15.5 19 12 19 C 8.5 19 5 17.2 2 12 Z",
        _circle_path(12, 12, 3),
    ],
    "camera": [
        "M 4 7 L 7.5 7 L 9.5 4.5 L 14.5 4.5 L 16.5 7 L 20 7 Q 22 7 22 9 L 22 18 Q 22 20 20 20 L 4 20 Q 2 20 2 18 L 2 9 Q 2 7 4 7 Z",
        _circle_path(12, 13, 3.2),
    ],
    "pencil": [
        "M 16.5 3.5 L 20.5 7.5 L 8 20 L 3 21 L 4 16 Z",
        "M 14 6 L 18 10",
    ],
    "trending-up": [
        "M 2.5 17 L 9 10.5 L 13.5 15 L 21.5 7",
        "M 16 7 L 21.5 7 L 21.5 12.5",
    ],
    "shield": [
        "M 12 2.5 L 20 6 L 20 12 C 20 16.8 16.4 20 12 21.5 C 7.6 20 4 16.8 4 12 L 4 6 Z",
        "M 9.2 12 L 11.2 14 L 15.2 9.8",
    ],
    "sparkles": [
        "M 12 2.5 L 14.2 9.8 L 21.5 12 L 14.2 14.2 L 12 21.5 L 9.8 14.2 L 2.5 12 L 9.8 9.8 Z",
    ],
    "download": [
        "M 12 3 L 12 15 M 7 10.5 L 12 15.5 L 17 10.5",
        "M 4 17 L 4 19.5 Q 4 21 5.5 21 L 18.5 21 Q 20 21 20 19.5 L 20 17",
    ],
    "printer": [
        "M 6 9 L 6 3 L 18 3 L 18 9",
        "M 6 17 L 3.5 17 Q 2.5 17 2.5 16 L 2.5 10 Q 2.5 9 3.5 9 L 20.5 9 Q 21.5 9 21.5 10 L 21.5 16 Q 21.5 17 20.5 17 L 18 17",
        _rrect_path(6, 14, 12, 7, 1),
    ],
    "phone": [
        "M 5 3 L 8.5 3 L 10 7.5 L 8 9.5 C 9.5 12.5 11.5 14.5 14.5 16 L 16.5 14 L 21 15.5 L 21 19 Q 21 21 19 21 C 10.5 20.5 3.5 13.5 3 5 Q 3 3 5 3 Z",
    ],
    "log-out": [
        "M 9 21 L 5 21 Q 3 21 3 19 L 3 5 Q 3 3 5 3 L 9 3",
        "M 16 17 L 21 12 L 16 7",
        "M 21 12 L 9 12",
    ],
}


def scale_svg_path(d, scale):
    """Skala presisi koordinat SVG path M/L/H/V/C/Q/Z tanpa arc flag distortion."""
    def _num(m):
        return f"{float(m.group(0)) * scale:.3f}".rstrip("0").rstrip(".") or "0"
    return re.sub(r"-?\d+(?:\.\d+)?", _num, d)


class FigBuilder:
    def __init__(self):
        self.steps = []
        self._id = 0

    def _uid(self, prefix="n"):
        self._id += 1
        return f"{prefix}_{self._id}"

    def page_rename(self, name):
        self.steps.append({"command": "page.rename", "params": {"name": name}})

    def page_add(self, name):
        alias = self._uid("pg")
        self.steps.append({"as": alias, "command": "page.add", "params": {"name": name}})
        return alias

    def page_bg(self, color="#EAEAE6"):
        self.steps.append({"command": "page.setBackground", "params": {"color": color}})

    def frame(self, name, x, y, w, h, fill=ALABASTER, radius=0, stroke=HAIRLINE, stroke_w=1, clip=True):
        alias = self._uid("frm")
        props = {"fill": fill, "cornerRadius": radius, "clip": clip}
        if stroke:
            props["stroke"] = stroke
            props["strokeWeight"] = stroke_w
        self.steps.append({
            "as": alias,
            "command": "frame.create",
            "params": {"name": name, "x": x, "y": y, "width": w, "height": h, "props": props, "select": False}
        })
        return alias

    def rect(self, parent, x, y, w, h, fill=SURFACE, radius=12, stroke=None, stroke_w=1, name="Box", opacity=None):
        alias = self._uid("rc")
        props = {"fill": fill, "cornerRadius": radius}
        if stroke:
            props["stroke"] = stroke
            props["strokeWeight"] = stroke_w
        if opacity is not None:
            props["opacity"] = opacity
        self.steps.append({
            "as": alias,
            "command": "shape.rectangle",
            "params": {"name": name, "x": x, "y": y, "width": w, "height": h, "parent": {"$ref": parent}, "props": props, "select": False}
        })
        return alias

    def gradient_rect(self, parent, x, y, w, h, stops, start=(0.0, 0.5), end=(1.0, 0.5), radius=0, name="Photo Fade"):
        alias = self._uid("gr")
        props = {
            "fills": [{
                "type": "linearGradient",
                "stops": stops,
                "from": list(start),
                "to": list(end),
            }],
            "cornerRadius": radius,
        }
        self.steps.append({
            "as": alias,
            "command": "shape.rectangle",
            "params": {"name": name, "x": x, "y": y, "width": w, "height": h, "parent": {"$ref": parent}, "props": props, "select": False}
        })
        return alias

    def image(self, parent, img_name, x, y, w, h, mode="fill", name=None):
        alias = self._uid("img")
        cand_client = CLIENT_DIR / img_name
        cand_hero = HERO_DIR / img_name
        src = cand_client if cand_client.exists() else cand_hero
        if not src.exists():
            webp_name = Path(img_name).with_suffix(".webp").name
            src = (CLIENT_DIR / webp_name) if (CLIENT_DIR / webp_name).exists() else (HERO_DIR / webp_name)
        path = str(src)
        self.steps.append({
            "as": alias,
            "command": "image.place",
            "params": {
                "path": path,
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "parent": {"$ref": parent},
                "mode": mode,
                "name": name or f"Photo {img_name}",
            }
        })
        return alias

    def vector(self, parent, svg_path, x, y, fill=PRIMARY, stroke=None, stroke_w=1.75, name="Vector", w=None, h=None):
        alias = self._uid("vec")
        props = {"fill": fill if fill else "none"}
        if stroke:
            props["stroke"] = stroke
            props["strokeWeight"] = stroke_w
            props["strokeCap"] = "round"
            props["strokeJoin"] = "round"
        params = {
            "path": svg_path,
            "x": x,
            "y": y,
            "parent": {"$ref": parent},
            "name": name,
            "props": props,
            "select": False,
        }
        if w is not None:
            params["width"] = w
        if h is not None:
            params["height"] = h
        self.steps.append({"as": alias, "command": "vector.create", "params": params})
        return alias

    def icon(self, parent, icon_name, x, y, size=18, color=PRIMARY_DARK, stroke_w=1.75):
        """Render Lucide-grade 24x24 icon dengan skala 1:1 proporsional & round cap."""
        paths = ICONS.get(icon_name, ICONS["sparkles"])
        sc = size / 24.0
        for idx, p in enumerate(paths):
            self.vector(
                parent,
                scale_svg_path(p, sc),
                x,
                y,
                fill="none",
                stroke=color,
                stroke_w=stroke_w,
                name=f"Icon {icon_name} #{idx + 1}",
            )

    def icon_badge(self, parent, icon_name, x, y, box_size=42, icon_size=20, bg=PRIMARY_SOFT, fg=PRIMARY_DARK, radius=12, stroke=None):
        r = self.rect(parent, x, y, box_size, box_size, fill=bg, radius=radius, stroke=stroke, name=f"Badge {icon_name}")
        off = (box_size - icon_size) / 2.0
        self.icon(parent, icon_name, x + off, y + off, size=icon_size, color=fg, stroke_w=1.85)
        return r

    def ellipse(self, parent, x, y, w, h, fill=PRIMARY_SOFT, stroke=None, stroke_w=1, name="Circle", opacity=None):
        alias = self._uid("el")
        props = {"fill": fill}
        if stroke:
            props["stroke"] = stroke
            props["strokeWeight"] = stroke_w
        if opacity is not None:
            props["opacity"] = opacity
        self.steps.append({
            "as": alias,
            "command": "shape.ellipse",
            "params": {"name": name, "x": x, "y": y, "width": w, "height": h, "parent": {"$ref": parent}, "props": props, "select": False}
        })
        return alias

    def text(self, parent, txt, x, y, size=14, color=INK, weight="Regular", family=FONT_BODY, width=None, align="left", line_h=None, name=None, max_lines=None):
        alias = self._uid("tx")
        props = {
            "fontSize": size,
            "fontFamily": family,
            "fontStyle": weight,
            "fill": color,
            "textAlign": align,
        }
        if line_h is not None:
            props["lineHeight"] = line_h
        if max_lines is not None:
            props["maxLines"] = max_lines
            props["textAutoResize"] = "truncate"
        params = {
            "text": txt,
            "x": x,
            "y": y,
            "parent": {"$ref": parent},
            "props": props,
            "select": False,
        }
        if width is not None:
            params["width"] = width
        if name:
            params["name"] = name
        self.steps.append({"as": alias, "command": "text.create", "params": params})
        return alias

    def pill(self, parent, x, y, w, h, label, bg, fg, size=12, weight="SemiBold", stroke=None, icon_name=None, icon_pos="left", elevate=False, radius=12):
        min_w = round(len(str(label)) * size * 0.64 + (44 if icon_name else 26))
        bw = max(w, min_w) if len(str(label)) > 1 else w
        r_px = (h / 2) if (radius is None) else radius
        r = self.rect(parent, x, y, bw, h, fill=bg, radius=r_px, stroke=stroke, name=f"Btn {label}")
        if elevate or (h >= 36 and bg in (PRIMARY, SECONDARY, INK)):
            self.shadow(r, blur=8, y=2, opacity=0.08 if bg != SURFACE else 0.04)
        if icon_name:
            ic_sz = max(13, round(size * 1.15))
            if icon_pos == "right":
                self.text(parent, label, x + 12, y + (h - size * 1.25) / 2, size=size, color=fg, weight=weight, width=max(24, bw - 40), align="center")
                self.icon(parent, icon_name, x + bw - ic_sz - 12, y + (h - ic_sz) / 2, size=ic_sz, color=fg, stroke_w=2.0)
            else:
                self.icon(parent, icon_name, x + 12, y + (h - ic_sz) / 2, size=ic_sz, color=fg, stroke_w=1.9)
                self.text(parent, label, x + 14 + ic_sz, y + (h - size * 1.25) / 2, size=size, color=fg, weight=weight, width=max(24, bw - 26 - ic_sz), align="center")
        else:
            self.text(parent, label, x + 8, y + (h - size * 1.25) / 2, size=size, color=fg, weight=weight, width=max(20, bw - 16), align="center")
        return r

    def shadow(self, target_id, blur=20, y=6, opacity=0.06):
        a_hex = f"{int(opacity * 255):02X}"
        self.steps.append({
            "command": "effect.add",
            "params": {
                "ids": [{"$ref": target_id}],
                "effect": {
                    "type": "dropShadow",
                    "color": f"#111827{a_hex}",
                    "offset": [0, y],
                    "radius": blur,
                    "spread": 0,
                }
            }
        })

    def flow(self, start_frame, name):
        self.steps.append({"command": "proto.flow.add", "params": {"start": {"$ref": start_frame}, "name": name}})

    def link(self, trigger_node, dest_frame, trans="slideIn", direction="left", duration=360, easing="easeOut"):
        transition = {"type": trans}
        if trans in ("moveIn", "moveOut", "push", "slideIn", "slideOut") and direction:
            transition["direction"] = direction
        self.steps.append({
            "command": "proto.interaction.add",
            "params": {
                "id": {"$ref": trigger_node},
                "trigger": {"type": "onClick"},
                "action": {"type": "navigate", "dest": {"$ref": dest_frame}},
                "transition": transition,
                "durationMs": duration,
                "easing": easing,
            }
        })

    def overlay_link(self, trigger_node, dest_frame, position="center", anchor="screen", trans="moveIn", direction="bottom", duration=240, easing="easeOut", dim="#11182766"):
        transition = {"type": trans}
        if trans in ("moveIn", "moveOut", "push", "slideIn", "slideOut") and direction:
            transition["direction"] = direction
        action = {
            "type": "openOverlay",
            "position": position,
            "anchor": anchor,
            "close_on_outside": True,
            "dest": {"$ref": dest_frame},
        }
        if dim:
            action["background"] = dim
        self.steps.append({
            "command": "proto.interaction.add",
            "params": {
                "id": {"$ref": trigger_node},
                "trigger": {"type": "onClick"},
                "action": action,
                "transition": transition,
                "durationMs": duration,
                "easing": easing,
            }
        })

    def swap_overlay_link(self, trigger_node, dest_frame, trans="dissolve", duration=200, easing="easeOut"):
        self.steps.append({
            "command": "proto.interaction.add",
            "params": {
                "id": {"$ref": trigger_node},
                "trigger": {"type": "onClick"},
                "action": {"type": "swapOverlay", "dest": {"$ref": dest_frame}},
                "transition": {"type": trans},
                "durationMs": duration,
                "easing": easing,
            }
        })

    def close_overlay_link(self, trigger_node, trans="dissolve", duration=180, easing="easeOut"):
        self.steps.append({
            "command": "proto.interaction.add",
            "params": {
                "id": {"$ref": trigger_node},
                "trigger": {"type": "onClick"},
                "action": {"type": "closeOverlay"},
                "transition": {"type": trans},
                "durationMs": duration,
                "easing": easing,
            }
        })

    def scroll_link(self, trigger_node, target_node, offset=(0, -76), duration=420, easing="easeInOut"):
        self.steps.append({
            "command": "proto.interaction.add",
            "params": {
                "id": {"$ref": trigger_node},
                "trigger": {"type": "onClick"},
                "action": {"type": "scrollTo", "offset": list(offset), "dest": {"$ref": target_node}},
                "durationMs": duration,
                "easing": easing,
            }
        })


def draw_modal_layer(b: FigBuilder, frame_name, x, y, title, subtitle, fields, primary_lbl, accent=PRIMARY, w=480, cancel_lbl="Batal"):
    row_h = 74
    h = 176 + len(fields) * row_h
    fm = b.frame(frame_name, x, y, w, h, fill=SURFACE, radius=12, stroke=HAIRLINE)
    b.shadow(fm, blur=16, y=6, opacity=0.10)
    b.text(fm, title, 24, 22, size=17, color=INK, weight="Bold", family=FONT_HEAD, width=w - 88, max_lines=1)
    close_x = b.pill(fm, w - 58, 20, 34, 34, "×", ALABASTER, INK, size=16, weight="Bold", stroke=HAIRLINE, radius=8)
    b.close_overlay_link(close_x)
    b.text(fm, subtitle, 24, 48, size=12, color=MUTED, width=w - 88, max_lines=1)
    b.rect(fm, 0, 82, w, 1, fill=HAIRLINE, radius=0)

    for fi, (flbl, fval) in enumerate(fields):
        fy = 98 + fi * row_h
        b.text(fm, flbl, 24, fy, size=12, color=INK, weight="Bold", width=w - 48, max_lines=1)
        b.rect(fm, 24, fy + 22, w - 48, 40, fill=ALABASTER, radius=8, stroke=HAIRLINE)
        b.text(fm, fval, 38, fy + 33, size=13, color=BODY, width=w - 76, max_lines=1)

    foot_y = h - 56
    b.rect(fm, 0, foot_y - 16, w, 72, fill=ALABASTER, radius=0, stroke=HAIRLINE)
    cancel_btn = b.pill(fm, w - 318, foot_y, 108, 40, cancel_lbl, SURFACE, INK, size=12.5, weight="SemiBold", stroke=HAIRLINE)
    b.close_overlay_link(cancel_btn)
    submit_btn = b.pill(fm, w - 198, foot_y, 174, 40, primary_lbl, accent, SURFACE, size=12.5, weight="Bold", elevate=True)
    return fm, submit_btn


def draw_toast_layer(b: FigBuilder, frame_name, x, y, title, msg, accent=OK_TXT, w=400, h=96):
    ft = b.frame(frame_name, x, y, w, h, fill=SURFACE, radius=12, stroke=HAIRLINE)
    b.shadow(ft, blur=12, y=4, opacity=0.08)
    b.rect(ft, 16, 20, 4, h - 40, fill=accent, radius=2)
    b.text(ft, title, 32, 22, size=14, color=INK, weight="Bold", family=FONT_HEAD, width=w - 124, max_lines=1)
    b.text(ft, msg, 32, 46, size=12, color=BODY, width=w - 124, max_lines=2)
    close_btn = b.pill(ft, w - 84, 30, 68, 34, "Tutup", ALABASTER, INK, size=11.5, weight="SemiBold", stroke=HAIRLINE)
    b.close_overlay_link(close_btn)
    return ft


def draw_popover_layer(b: FigBuilder, frame_name, x, y, title, items, footer_lbl=None, w=360):
    h = 92 + len(items) * 58 + (48 if footer_lbl else 0)
    fp = b.frame(frame_name, x, y, w, h, fill=SURFACE, radius=12, stroke=HAIRLINE)
    b.shadow(fp, blur=12, y=4, opacity=0.08)
    b.text(fp, title, 20, 20, size=14.5, color=INK, weight="Bold", family=FONT_HEAD, width=w - 72, max_lines=1)
    close_x = b.pill(fp, w - 48, 16, 28, 28, "×", ALABASTER, BODY, size=14, weight="Bold", stroke=HAIRLINE, radius=8)
    b.close_overlay_link(close_x)
    b.rect(fp, 20, 54, w - 40, 1, fill=HAIRLINE, radius=0)
    for ii, (it, idesc, icol) in enumerate(items):
        iy = 68 + ii * 58
        b.ellipse(fp, 22, iy + 14, 7, 7, fill=icol)
        b.text(fp, it, 38, iy + 6, size=12.5, color=INK, weight="Bold", width=w - 58, max_lines=1)
        b.text(fp, idesc, 38, iy + 26, size=11.5, color=MUTED, width=w - 58, max_lines=1)
    foot_btn = None
    if footer_lbl:
        foot_btn = b.pill(fp, 20, h - 52, w - 40, 36, footer_lbl, PRIMARY_SOFT, PRIMARY_DARK, size=12, weight="Bold")
    return fp, foot_btn


# ==============================================================================
# UNIFIED CLIENT BRAND LOGO (DARI `static/images/client/logo_desi_privat.webp`)
# ==============================================================================
def draw_brand_mark(b: FigBuilder, parent, x, y, size=36, light=False):
    """Logo resmi DESI PRIVAT dengan radius sudut seragam & lembut (12px / 10px)."""
    r_px = 12 if size >= 34 else 10
    bdr_col = "#FFFFFF55" if light else HAIRLINE
    b.rect(parent, x, y, size, size, fill=SURFACE, radius=r_px, stroke=bdr_col, name="Desi Privat Logo Box")
    pad = 2
    b.image(parent, "logo_desi_privat.webp", x + pad, y + pad, size - pad * 2, size - pad * 2, mode="fill", name="Desi Privat Logo WebP")


def draw_initials_avatar(b: FigBuilder, parent, x, y, size, initials, bg=PRIMARY_SOFT, fg=PRIMARY_DARK):
    b.ellipse(parent, x, y, size, size, fill=bg, name=f"Avatar {initials}")
    fsize = max(9.5, round(size * 0.36))
    b.text(parent, initials, x + 2, y + (size - fsize * 1.25) / 2, size=fsize, color=fg, weight="Bold", width=size - 4, align="center", max_lines=1)


# ==============================================================================
# SHARED MINIMALIST APP SHELL WITH CRISP SIDEBAR ICONS & SEARCH TOPBAR
# ==============================================================================
NAV_ICON_MAP = {
    "Dashboard Utama": "dashboard",
    "Dashboard Eksekutif": "dashboard",
    "Beranda Mentor": "home",
    "Ringkasan Belajar": "home",
    "Live Activity Feed": "trending-up",
    "Penjadwalan Les": "calendar",
    "Rekap Jadwal": "calendar",
    "Jadwal Mengajar": "calendar",
    "Jadwal & Kalender": "calendar",
    "Ketersediaan Waktu": "clock",
    "Data Siswa": "graduation",
    "Siswa Bimbingan": "graduation",
    "Data Mentor": "mentor",
    "Pergantian Mentor": "mentor",
    "Orang Tua / Wali": "family",
    "Data Orang Tua": "family",
    "Data Admin": "shield",
    "Program Les": "book",
    "Tagihan & Cicilan": "receipt",
    "Tagihan & Tunggakan": "receipt",
    "Tagihan & Pembayaran": "receipt",
    "Riwayat Pembayaran": "credit-card",
    "Keuangan & Honor": "wallet",
    "Arus Kas Bimbel": "trending-up",
    "Honor Mentor": "wallet",
    "Honor Tentor": "wallet",
    "Manajemen Akun": "key",
    "Pemberitahuan": "bell",
    "Laporan & Ekspor": "report",
    "Laporan Eksekutif": "report",
    "Perkembangan Siswa": "trending-up",
    "Laporan Perkembangan": "trending-up",
    "Dashboard Absensi": "camera",
    "Absensi & Foto Sesi": "camera",
    "Riwayat Kehadiran": "check",
    "Audit Log": "history",
    "Backup & Restore": "backup",
    "Ekspor Audit CSV/JSON": "download",
}

ROLE_MENUS = {
    "admin": (
        "PANEL ADMIN",
        "Admin Pengelola",
        "AP",
        [
            "Dashboard Utama", "Penjadwalan Les", "Data Siswa", "Data Mentor",
            "Orang Tua / Wali", "Program Les", "Tagihan & Cicilan", "Riwayat Pembayaran",
            "Honor Mentor", "Manajemen Akun", "Pemberitahuan", "Laporan & Ekspor",
            "Audit Log", "Backup & Restore"
        ]
    ),
    "owner": (
        "SUPERVISI PEMILIK",
        "Pemilik Lembaga",
        "PL",
        [
            "Dashboard Eksekutif", "Dashboard Absensi", "Data Siswa", "Data Mentor",
            "Data Orang Tua", "Data Admin", "Rekap Jadwal", "Pergantian Mentor",
            "Perkembangan Siswa", "Tagihan & Tunggakan", "Keuangan & Honor",
            "Arus Kas Bimbel", "Honor Tentor", "Laporan Eksekutif", "Audit Log"
        ]
    ),
    "mentor": (
        "PORTAL MENTOR",
        "Kak Sarah, S.Pd",
        "KS",
        [
            "Beranda Mentor", "Jadwal Mengajar", "Ketersediaan Waktu",
            "Siswa Bimbingan", "Absensi & Foto Sesi", "Laporan Perkembangan"
        ]
    ),
    "parent": (
        "PORTAL WALI MURID",
        "Ibu Ratna Sari",
        "IR",
        [
            "Ringkasan Belajar", "Jadwal & Kalender", "Riwayat Kehadiran",
            "Laporan Perkembangan", "Tagihan & Pembayaran"
        ]
    ),
    "developer": (
        "DEVELOPER CONSOLE",
        "Dev System",
        "DV",
        ["Live Activity Feed", "Ekspor Audit CSV/JSON"]
    ),
}


def draw_app_shell(
    b: FigBuilder,
    frame_name,
    x,
    y,
    role,
    active_nav,
    page_title,
    page_sub,
    primary_cta=None,
    secondary_cta=None,
    readonly_badge=False,
    primary_icon=None,
    secondary_icon=None,
):
    f = b.frame(frame_name, x, y, 1440, 960, fill=ALABASTER, stroke=HAIRLINE)
    role_sub, user_badge, initials, nav_items = ROLE_MENUS[role]

    # Sidebar (Ikon fungsional bersih, tanpa subtitle brand berlebih)
    b.rect(f, 0, 0, 248, 960, fill=SURFACE, radius=0, stroke=HAIRLINE, name="Sidebar")
    draw_brand_mark(b, f, 20, 22, size=34, light=False)
    b.text(f, "DESI", 64, 28, size=15, color=PRIMARY, weight="Bold", family=FONT_HEAD, width=48, max_lines=1)
    b.text(f, "PRIVAT", 106, 28, size=15, color=SECONDARY, weight="Bold", family=FONT_HEAD, width=80, max_lines=1)
    b.rect(f, 20, 72, 208, 1, fill=HAIRLINE, radius=0)

    nav_nodes = {}
    for idx, item in enumerate(nav_items):
        ny = 84 + idx * 44
        is_act = (item == active_nav)
        hit = b.rect(f, 14, ny, 220, 38, fill=PRIMARY_SOFT if is_act else SURFACE, radius=12, stroke=PRIMARY_BORDER if is_act else None, name=f"Nav {item}")
        if is_act:
            b.rect(f, 14, ny + 8, 3.5, 22, fill=PRIMARY, radius=2)
        nav_ic = NAV_ICON_MAP.get(item, "dashboard")
        b.icon(f, nav_ic, 28, ny + 10, size=16.5, color=PRIMARY_DARK if is_act else MUTED, stroke_w=1.9 if is_act else 1.65)
        b.text(f, item, 54, ny + 10, size=12.5, color=PRIMARY_DARK if is_act else BODY, weight="Bold" if is_act else "Medium", width=168, max_lines=1)
        nav_nodes[item] = hit

    # Quiet Sidebar Footer (clickable Logout hitbox)
    b.rect(f, 20, 898, 208, 1, fill=HAIRLINE, radius=0)
    logout_hit = b.rect(f, 14, 906, 220, 36, fill=SURFACE, radius=12, name="Sidebar Logout Hit")
    nav_nodes["__logout__"] = logout_hit
    b.icon(f, "log-out", 28, 916, size=15.5, color=MUTED, stroke_w=1.7)
    b.text(f, "Keluar", 54, 915, size=12.5, color=MUTED, weight="SemiBold", width=148, max_lines=1)

    # Topbar Minimalis
    b.rect(f, 248, 0, 1192, 76, fill=SURFACE, radius=0, stroke=HAIRLINE, name="Topbar")
    b.text(f, page_title, 284, 25, size=19, color=INK, weight="Bold", family=FONT_HEAD, width=640, max_lines=1)

    if readonly_badge:
        b.text(f, "Mode Baca Saja", 988, 30, size=12, color=SECONDARY_DARK, weight="SemiBold", width=116, align="right", max_lines=1)
    else:
        search_hit = b.rect(f, 926, 21, 182, 34, fill=ALABASTER, radius=12, stroke=HAIRLINE, name="Topbar Search")
        nav_nodes["__search__"] = search_hit
        b.icon(f, "search", 940, 30, size=14.5, color=MUTED, stroke_w=1.7)
        b.text(f, "Cari...", 962, 30, size=12, color=MUTED, width=132, max_lines=1)

    # Minimal bell icon hitbox + icon (uniform 12px softer corner radius)
    bell_hit = b.rect(f, 1126, 20, 36, 36, fill=ALABASTER, radius=12, stroke=HAIRLINE, name="Topbar Bell Hit")
    nav_nodes["__bell__"] = bell_hit
    b.icon(f, "bell", 1135, 29, size=18, color=BODY, stroke_w=1.75)
    b.ellipse(f, 1150, 27, 6, 6, fill=SECONDARY, name="Bell Dot")

    # Clean user avatar + name (tanpa pill pembungkus)
    draw_initials_avatar(b, f, 1178, 24, 28, initials, bg=PRIMARY_SOFT, fg=PRIMARY_DARK)
    b.text(f, user_badge, 1216, 30, size=12.5, color=INK, weight="SemiBold", width=188, max_lines=1)

    cur_y = 100
    cta_btn = None
    sec_btn = None
    if primary_cta or secondary_cta:
        if secondary_cta:
            sec_btn = b.pill(f, 284, cur_y, 200, 40, secondary_cta, SURFACE, INK, size=12.5, weight="SemiBold", stroke=HAIRLINE)
        if primary_cta:
            pw = max(172, round(len(primary_cta) * 8.2 + 32))
            cta_btn = b.pill(f, 1404 - pw, cur_y, pw, 40, primary_cta, PRIMARY, SURFACE, size=13, weight="Bold", elevate=True)
        cur_y += 56

    return f, cur_y, nav_nodes, cta_btn, sec_btn


def draw_kpi_strip(b: FigBuilder, f, y, items):
    """KPI strip seragam #FFFFFF + 1px border #E5E7EB + radius 12px (tanpa ikon dekoratif)."""
    n = len(items)
    gap = 20
    card_w = (1120 - gap * (n - 1)) / n
    for i, item in enumerate(items):
        val, title, _sub, _accent_bg, _accent_fg = item[:5]
        cx = 284 + i * (card_w + gap)
        card = b.rect(f, cx, y, card_w, 88, fill=SURFACE, radius=12, stroke=HAIRLINE, name=f"KPI {title}")
        b.shadow(card, blur=8, y=2, opacity=0.03)
        b.text(f, title, cx + 20, y + 18, size=12, color=MUTED, weight="SemiBold", width=card_w - 40, max_lines=1)
        b.text(f, val, cx + 20, y + 40, size=26, color=INK, weight="Bold", family=FONT_HEAD, width=card_w - 40, max_lines=1)
    return y + 108


def draw_table_card(b: FigBuilder, f, y, title, columns, rows, filter_hint="Cari...", badge_col_idx=-1, h=None, x=284, w=1120):
    card_h = h if h else (932 - y)
    card = b.rect(f, x, y, w, card_h, fill=SURFACE, radius=12, stroke=HAIRLINE, name=f"Table {title}")
    b.shadow(card, blur=8, y=2, opacity=0.03)
    b.text(f, title, x + 20, y + 20, size=15.5, color=INK, weight="Bold", family=FONT_HEAD, width=w - 40, max_lines=1)

    search_w = w - 268
    b.rect(f, x + 20, y + 54, search_w, 38, fill=ALABASTER, radius=8, stroke=HAIRLINE)
    b.icon(f, "search", x + 32, y + 65, size=15, color=MUTED, stroke_w=1.7)
    b.text(f, "Cari...", x + 55, y + 66, size=12, color=MUTED, width=search_w - 44, max_lines=1)
    b.pill(f, x + 20 + search_w + 12, y + 54, 112, 38, "Terapkan", PRIMARY, SURFACE, size=12, weight="Bold")
    b.pill(f, x + 20 + search_w + 134, y + 54, 94, 38, "Reset", SURFACE, BODY, size=12, weight="SemiBold", stroke=HAIRLINE)

    hy = y + 108
    tbl_w = w - 40
    b.rect(f, x + 20, hy, tbl_w, 38, fill=ALABASTER, radius=8)
    col_n = len(columns)
    col_w = (tbl_w - 16) / max(col_n, 1)
    for ci, cname in enumerate(columns):
        b.text(f, cname.upper(), x + 32 + ci * col_w, hy + 12, size=10.5, color=MUTED, weight="Bold", width=col_w - 12, max_lines=1)

    first_row = None
    for ri, row in enumerate(rows):
        ry = hy + 46 + ri * 58
        if ry + 50 > y + card_h - 14:
            break
        row_rect = b.rect(f, x + 20, ry, tbl_w, 50, fill=SURFACE, radius=8, stroke=HAIRLINE, name=f"Row {ri + 1}")
        if ri == 0:
            first_row = row_rect
        for ci, cell in enumerate(row):
            cx = x + 32 + ci * col_w
            is_ok = any(k in cell for k in ["Aktif", "Lunas", "Hadir", "Disetujui", "Valid", "Terkirim", "Siap", "Tersedia", "Sudah Ditransfer"])
            is_warn = any(k in cell for k in ["Menunggu", "Cicilan", "Proses", "Pengganti", "Ganti"])
            is_bad = any(k in cell for k in ["Tunggakan", "Bentrok", "Gagal", "Alpa", "Berhalangan", "Arsip"])
            if ci == badge_col_idx or (ci == col_n - 1 and (is_ok or is_warn or is_bad)):
                fg = OK_TXT if is_ok else (DANGER_TXT if is_bad else SECONDARY_DARK)
                b.text(f, cell, cx, ry + 16, size=12.5, color=fg, weight="SemiBold", width=col_w - 12, max_lines=1)
            else:
                b.text(f, cell, cx, ry + 16, size=12.5, color=INK if ci == 0 else BODY, weight="SemiBold" if ci == 0 else "Regular", width=col_w - 12, max_lines=1)
    return first_row


# ==============================================================================
# EDITORIAL MICRO-UI SPECIMENS (PENGGANTI STICK ILLUSTRATION)
# ==============================================================================
def draw_micro_specimen(b: FigBuilder, parent, x, y, variant="learning", title="Siklus 8 Pertemuan", subtitle="Progres terpantau otomatis"):
    card = b.rect(parent, x, y, 316, 134, fill=SURFACE, radius=16, stroke=HAIRLINE, name=f"Specimen {variant}")
    b.shadow(card, blur=18, y=5, opacity=0.04)
    if variant == "learning":
        b.icon_badge(parent, "book", x + 16, y + 16, box_size=38, icon_size=18, bg=PRIMARY_SOFT, fg=PRIMARY_DARK, radius=10)
        b.text(parent, title, x + 64, y + 16, size=13.5, color=INK, weight="Bold", width=234, max_lines=1)
        b.text(parent, subtitle, x + 64, y + 36, size=11.5, color=MUTED, width=234, max_lines=1)
        b.rect(parent, x + 16, y + 70, 284, 8, fill=SUBTLE_BG, radius=4)
        b.rect(parent, x + 16, y + 70, 214, 8, fill=PRIMARY, radius=4)
        b.pill(parent, x + 16, y + 90, 128, 28, "Pertemuan 6 / 8", OK_BG, OK_TXT, size=11, weight="Bold", icon_name="check")
        b.text(parent, "Kak Sarah", x + 156, y + 96, size=11.5, color=BODY, weight="SemiBold", width=140, align="right", max_lines=1)
    elif variant == "schedule":
        b.icon_badge(parent, "calendar-check", x + 16, y + 16, box_size=38, icon_size=18, bg=SECONDARY_SOFT, fg=SECONDARY_DARK, radius=10)
        b.text(parent, title, x + 64, y + 16, size=13.5, color=INK, weight="Bold", width=234, max_lines=1)
        b.text(parent, subtitle, x + 64, y + 36, size=11.5, color=MUTED, width=234, max_lines=1)
        b.rect(parent, x + 16, y + 68, 284, 50, fill=ALABASTER, radius=10, stroke=HAIRLINE)
        b.icon(parent, "clock", x + 28, y + 85, size=15, color=PRIMARY_DARK)
        b.text(parent, "Senin, 15:30 WIB", x + 50, y + 85, size=12, color=INK, weight="SemiBold", width=136, max_lines=1)
        b.pill(parent, x + 194, y + 79, 96, 28, "0 Bentrok", OK_BG, OK_TXT, size=10.5, weight="Bold")
    elif variant == "empty":
        b.icon_badge(parent, "family", x + 16, y + 16, box_size=38, icon_size=18, bg=PRIMARY_SOFT, fg=PRIMARY_DARK, radius=10)
        b.text(parent, title, x + 64, y + 16, size=13.5, color=INK, weight="Bold", width=234, max_lines=1)
        b.text(parent, subtitle, x + 64, y + 36, size=11.5, color=MUTED, width=234, max_lines=1)
        b.pill(parent, x + 16, y + 74, 136, 36, "Naufal (8 SMP)", PRIMARY, SURFACE, size=11.5, weight="Bold", icon_name="check")
        b.pill(parent, x + 162, y + 74, 138, 36, "Alisha (3 SD)", ALABASTER, BODY, size=11.5, weight="SemiBold", stroke=HAIRLINE)
    else:
        b.icon_badge(parent, "shield", x + 16, y + 16, box_size=38, icon_size=18, bg=OK_BG, fg=OK_TXT, radius=10)
        b.text(parent, title, x + 64, y + 16, size=13.5, color=INK, weight="Bold", width=234, max_lines=1)
        b.text(parent, subtitle, x + 64, y + 36, size=11.5, color=MUTED, width=234, max_lines=1)
        b.rect(parent, x + 16, y + 68, 284, 50, fill=ALABASTER, radius=10, stroke=HAIRLINE)
        b.icon(parent, "backup", x + 28, y + 85, size=15, color=SECONDARY_DARK)
        b.text(parent, "Snapshot SQLite Tervalidasi", x + 50, y + 85, size=12, color=INK, weight="SemiBold", width=236, max_lines=1)


# ==============================================================================
# PAGE 1: DESIGN SYSTEM, PALETTE, VECTOR ICON LIBRARY & TRANSITIONS
# ==============================================================================
def build_page_00_design_system(b: FigBuilder):
    b.page_rename("00 - Design System & Palette")
    b.page_bg("#EAEAE6")

    f = b.frame("00 - Design System: Plus Jakarta Sans, DM Sans, Motion & States", 0, 0, 1520, 1340, fill=ALABASTER, stroke=HAIRLINE)
    draw_brand_mark(b, f, 56, 36, size=44, light=False)
    b.text(f, "DESI PRIVAT: Minimalist Design, Typography & Motion System", 114, 42, size=26, color=INK, weight="Bold", family=FONT_HEAD, width=1320, max_lines=1)

    # 1. Color Swatches (Strict 70-25-5)
    b.text(f, "1. PALET WARNA RESMI (70% PRIMARY NEUTRAL, 25% SECONDARY BRAND, 5% ACCENT)", 56, 112, size=11.5, color=MUTED, weight="Bold")
    swatches = [
        ("70% PRIMARY", "#FFFFFF", "Pure Surface", SURFACE, INK),
        ("70% NEUTRAL", "#F7F7F5", "Warm Alabaster", ALABASTER, INK),
        ("70% INK", "#111827", "Charcoal Ink", INK, SURFACE),
        ("25% SECONDARY", "#0093D6", "Cerulean Sky", PRIMARY, SURFACE),
        ("25% DEEP", "#083A54", "Ocean Navy", PRIMARY_DEEP, SURFACE),
        ("5% ACCENT", "#A66B37", "Caramel (Sparing)", SECONDARY, SURFACE),
    ]
    for i, (tag, hx, nm, bg, fg) in enumerate(swatches):
        sx = 56 + i * 238
        sw_card = b.rect(f, sx, 138, 222, 138, fill=SURFACE, radius=12, stroke=HAIRLINE)
        b.shadow(sw_card, blur=8, y=2, opacity=0.03)
        b.rect(f, sx + 12, 150, 198, 68, fill=bg, radius=8, stroke=HAIRLINE if bg in (SURFACE, ALABASTER) else None)
        b.text(f, hx, sx + 22, 175, size=14, color=fg, weight="Bold")
        b.text(f, tag, sx + 14, 230, size=10, color=PRIMARY_DARK if "25%" in tag else (SECONDARY_DARK if "5%" in tag else MUTED), weight="Bold")
        b.text(f, nm, sx + 14, 248, size=13, color=INK, weight="Bold")

    # 2. Typography + Button State Spec
    t_card = b.rect(f, 56, 298, 690, 176, fill=SURFACE, radius=16, stroke=HAIRLINE)
    b.shadow(t_card, blur=14, y=4, opacity=0.03)
    b.text(f, "2. TIPOGRAFI TERUNIFIKASI (DISPLAY + UI)", 84, 320, size=11.5, color=MUTED, weight="Bold")
    b.text(f, "Plus Jakarta Sans", 84, 348, size=24, color=INK, weight="Bold", family=FONT_HEAD, width=310, max_lines=1)
    b.text(f, "Heading, Display, KPI Angka, Judul Babak", 84, 384, size=12, color=PRIMARY_DARK, weight="SemiBold", width=310, max_lines=1)
    b.text(f, "DM Sans", 420, 348, size=24, color=INK, weight="SemiBold", family=FONT_BODY, width=290, max_lines=1)
    b.text(f, "Body, Tabel, Form Label, Button, Metadata", 420, 384, size=12, color=SECONDARY_DARK, weight="SemiBold", width=290, max_lines=1)
    b.text(f, "Scale: 48px Hero, 32px Section, 16px Body, 12px Micro, Bebas Em Dash", 84, 426, size=12, color=BODY, width=630, max_lines=1)

    b_card = b.rect(f, 774, 298, 690, 176, fill=SURFACE, radius=16, stroke=HAIRLINE)
    b.shadow(b_card, blur=14, y=4, opacity=0.03)
    b.text(f, "3. SPESIFIKASI BUTTON & INTERACTION STATES (20 MOTION RULES)", 802, 320, size=11.5, color=MUTED, weight="Bold")
    b.pill(f, 802, 354, 152, 42, "Primary Default", SECONDARY, SURFACE, size=12.5, weight="Bold", elevate=True)
    b.pill(f, 968, 354, 152, 42, "Hover Lift -1px", SECONDARY_DARK, SURFACE, size=12.5, weight="Bold", elevate=True)
    b.pill(f, 1134, 356, 146, 38, "Press 0.97", PRIMARY_DEEP, SURFACE, size=12, weight="Bold")
    b.pill(f, 1294, 354, 142, 42, "Secondary", SURFACE, INK, size=12.5, weight="SemiBold", stroke=HAIRLINE, elevate=True)
    b.text(f, "Ease-Out Entrances, 150-250ms Dropdown, 30ms Row Stagger, Exit 20% Shorter, Blur 2px Settle, Popover 0.95", 802, 422, size=12, color=BODY, width=634, max_lines=2)

    # 3. Full-Bleed Photo Fade + Clean Typography
    b.rect(f, 56, 498, 690, 296, fill=PRIMARY_DEEP, radius=18, stroke=HAIRLINE, name="Contoh Photo Fade Box")
    b.image(f, "galeri_01.webp", 56, 498, 690, 296, mode="fill", name="Contoh Faded Photo")
    b.gradient_rect(f, 56, 498, 690, 296, ["#083A54F2", "#0093D6B0", "#0093D610"], start=(0.0, 0.5), end=(1.0, 0.5), radius=18)
    b.text(f, "4. FULL FOTO + FADE + TEKS LANGSUNG", 86, 528, size=11, color="#BAE4F8", weight="Bold")
    b.text(f, "Teks Langsung di Atas Foto,\nTanpa Card Pembungkus.", 86, 560, size=24, color=SURFACE, weight="Bold", family=FONT_HEAD, width=420, line_h=32)
    b.pill(f, 86, 718, 190, 44, "Masuk Portal", SECONDARY, SURFACE, size=13, weight="Bold", elevate=True)

    # 4. Lenis + Scroll-Craft + AOS Choreography
    m_card = b.rect(f, 774, 498, 690, 296, fill=SURFACE, radius=18, stroke=HAIRLINE)
    b.shadow(m_card, blur=16, y=4, opacity=0.03)
    b.text(f, "5. LENIS + SCROLL-CRAFT + AOS PARALLAX ENGINE (8 BABAK)", 804, 528, size=11.5, color=MUTED, weight="Bold")
    motions = [
        ("Lenis Smooth Scroll", "Gulir inersia halus disinkronkan rAF bersama Scroll-Craft.", PRIMARY_SOFT, PRIMARY_DARK),
        ("Layered Hero Pin", "Foto latar + potret kedalaman bergerak pada kecepatan berbeda.", SECONDARY_SOFT, SECONDARY_DARK),
        ("AOS + Diptych Parallax", "Foto asimetris muncul bertahap (fade-up) saat digulir.", PRIMARY_SOFT, PRIMARY_DARK),
        ("Pan Rail + Feathers", "Program bergeser horizontal & gradasi lembut antar-babak.", SECONDARY_SOFT, SECONDARY_DARK),
    ]
    for i, (mt, md, mbg, mfg) in enumerate(motions):
        my = 560 + i * 54
        b.rect(f, 804, my, 630, 44, fill=ALABASTER, radius=10, stroke=HAIRLINE)
        b.pill(f, 816, my + 8, 152, 28, mt, mbg, mfg, size=11, weight="Bold")
        b.text(f, md, 984, my + 14, size=12, color=BODY, width=438, max_lines=1)

    # 5. Minimalist Icon Kit (12 Ikon Inti, tanpa kotak warna berlebih)
    ic_panel = b.rect(f, 56, 822, 1408, 148, fill=SURFACE, radius=18, stroke=HAIRLINE)
    b.shadow(ic_panel, blur=14, y=4, opacity=0.03)
    b.text(f, "6. IKON FUNGSIONAL INTI (12 IKON, STROKE 1.75PX)", 84, 846, size=11.5, color=MUTED, weight="Bold")
    showcase_icons = [
        ("dashboard", "Dashboard"), ("calendar", "Jadwal"), ("graduation", "Siswa"),
        ("mentor", "Mentor"), ("family", "Wali"), ("book", "Program"),
        ("receipt", "Tagihan"), ("wallet", "Honor"), ("bell", "Notifikasi"),
        ("camera", "Foto Sesi"), ("report", "Laporan"), ("search", "Cari"),
    ]
    for i, (inm, ilbl) in enumerate(showcase_icons):
        ix = 84 + i * 114
        b.icon(f, inm, ix + 34, 884, size=22, color=PRIMARY_DARK if i % 2 == 0 else SECONDARY_DARK, stroke_w=1.75)
        b.text(f, ilbl, ix, 920, size=11, color=BODY, weight="SemiBold", width=90, align="center", max_lines=1)

    # 6. Page Map
    pm_card = b.rect(f, 56, 996, 1408, 226, fill=SURFACE, radius=18, stroke=HAIRLINE)
    b.shadow(pm_card, blur=14, y=4, opacity=0.03)
    b.text(f, "7. PETA 52 TEMPLATE HALAMAN (8 HALAMAN FIGCRAFT)", 84, 1022, size=11.5, color=MUTED, weight="Bold")
    pages_summary = [
        ("Page 01", "Public & Auth (2)", "landing.html (8 Babak Parallax), login.html"),
        ("Page 02", "Admin Operasional (8)", "dashboard, schedules, students, mentors, parents, programs, notif"),
        ("Page 03", "Admin Keuangan & Sistem (8)", "bills, payments, receipt_print, honor, accounts, reports, audit, backup"),
        ("Page 04", "Owner Eksekutif (16)", "Seluruh 16 halaman supervisi Read-Only Pemilik"),
        ("Page 05", "Mentor Portal (6)", "dashboard, schedules, availability, students, attendance, progress"),
        ("Page 06", "Parent Portal (6)", "dashboard, schedules, attendance, progress, bills, no_children"),
        ("Page 07", "Developer & Error (6)", "developer/login, developer/dashboard, errors 400 / 403 / 404 / 500"),
        ("Standar", "Tenang & Minimalis", "Plus Jakarta Sans + DM Sans, bebas em dash & bebas ekspor PNG"),
    ]
    for i, (pg, title, desc) in enumerate(pages_summary):
        col = i % 4
        row = i // 4
        px = 84 + col * 340
        py = 1058 + row * 74
        b.rect(f, px, py, 322, 62, fill=ALABASTER, radius=10, stroke=HAIRLINE)
        b.text(f, f"{pg}: {title}", px + 14, py + 10, size=12, color=PRIMARY_DARK, weight="Bold", width=294, max_lines=1)
        b.text(f, desc, px + 14, py + 30, size=11, color=BODY, width=294, max_lines=1)


# ==============================================================================
# PAGE 2: PUBLIC & AUTH (FULL-BLEED PHOTO FADE + GROW+ ACTIVITY PILLS)
# ==============================================================================
def _draw_sophie_achievement_card(b: FigBuilder, parent, x, y, w, h, img_name, student_name, desc, meta_left, outer_r=28, inner_r=20):
    """Kartu Pencapaian Siswa (Concentric radius R_inner = R_outer - 8px + Animated Eye Icon-Only 44x44)."""
    outer = b.rect(parent, x, y, w, h, fill=SURFACE, radius=outer_r, stroke=HAIRLINE, name=f"Sophie Card {student_name}")
    b.shadow(outer, blur=16, y=6, opacity=0.06)
    pad = 8
    ix, iy, iw, ih = x + pad, y + pad, w - pad * 2, h - pad * 2
    b.rect(parent, ix, iy, iw, ih, fill=ALABASTER, radius=inner_r, name=f"Sophie Photo Frame {img_name}")
    b.image(parent, img_name, ix, iy, iw, ih, mode="fill", name=f"Client {img_name}")

    # Bottom frosted milky white gradient overlay (bottom 48% of photo)
    gh = round(ih * 0.50)
    gy = iy + ih - gh
    b.gradient_rect(parent, ix, gy, iw, gh, ["#FFFFFF00", "#FFFFFFCC", "#FFFFFFF5", "#FFFFFFFC"], start=(0.5, 0.0), end=(0.5, 1.0), radius=inner_r, name="Milky Frost Overlay")

    # Student Name + Green Verified Check Badge
    tx = ix + 18
    ty = iy + ih - 134
    name_w = min(iw - 62, max(130, round(len(student_name) * 9.5)))
    b.text(parent, student_name, tx, ty, size=16.5, color=INK, weight="Bold", family=FONT_HEAD, width=name_w, max_lines=1)
    vx = tx + min(name_w + 4, iw - 54)
    b.ellipse(parent, vx, ty + 1, 18, 18, fill="#16A34A", name="Verified Badge Green")
    b.vector(parent, scale_svg_path("M 6 12.5 L 10.2 16.5 L 18 8.2", 18 / 24.0), vx, ty + 1, fill="none", stroke=SURFACE, stroke_w=2.1, name="Verified Checkmark")

    # 2-Line Achievement Description
    b.text(parent, desc, tx, ty + 28, size=12.5, color=BODY, width=iw - 36, line_h=18, max_lines=2)

    # Bottom Row: Metadata left + Icon-Only Animated Eye Button (44x44, centered 20px icon, concentric 14px radius)
    by = iy + ih - 56
    b.text(parent, meta_left, tx, by + 13, size=12, color=MUTED, weight="SemiBold", width=iw - 96, max_lines=1)
    eye_x = ix + iw - 60
    eye_btn = b.rect(parent, eye_x, by, 44, 44, fill=ALABASTER, radius=14, stroke=HAIRLINE, name="Animated Eye Icon Button")
    b.shadow(eye_btn, blur=8, y=2, opacity=0.06)
    b.icon(parent, "eye", eye_x + 12, by + 12, size=20, color=INK, stroke_w=1.75)
    return eye_btn


def build_page_01_public_auth(b: FigBuilder):
    b.page_add("01 - Public & Auth (4x2 Hero + Eye Cards)")
    b.page_bg("#EAEAE6")

    # --- 1. landing.html (4-Screen Editorial: Framed 4x2 Diagonal Hero + Top Whitespace + 6 Sophie Eye Cards + 4 Programs + Closing with galeri_09) ---
    f = b.frame("landing.html: Beranda Publik (4x2 Hero + Whitespace + Eye Icon + Zero Duplikat)", 0, 0, 1440, 2980, fill=ALABASTER, stroke=HAIRLINE)

    # SCREEN 1: FRAMED HERO WITH BREATHING TOP WHITESPACE + 4x2 COLLAGE AT TOP (8 UNIQUE PHOTOS, ZERO DUPLICATES)
    act1_hero = b.rect(f, 24, 24, 1392, 752, fill="#075B8E", radius=28, name="Screen 1 Framed Hero Stage (Concentric 28px)")
    b.shadow(act1_hero, blur=24, y=10, opacity=0.12)
    hero_tiles = [
        "galeri_01.webp", "galeri_02.webp", "galeri_03.webp", "galeri_04.webp",
        "galeri_05.webp", "galeri_06.webp", "galeri_07.webp", "galeri_08.webp",
    ]
    tile_w, tile_h, tile_gap = 328, 244, 14
    for gi, gfile in enumerate(hero_tiles):
        col = gi % 4
        row = gi // 4
        diag_y = col * -8
        gx = 40 + col * (tile_w + tile_gap)
        gy = 48 + row * (tile_h + tile_gap) + diag_y
        b.rect(f, gx, gy, tile_w, tile_h, fill=PRIMARY_DEEP, radius=20, name=f"Hero 4x2 Tile Frame #{gi+1}")
        b.image(f, gfile, gx, gy, tile_w, tile_h, mode="fill", name=f"Hero 4x2 Unique #{gi+1} {gfile}")

    # Open Blue Wash Over 4x2 Mosaic + Clean Open Lower Band (Like Gambar 1)
    b.gradient_rect(f, 24, 24, 1392, 752, ["#064E77B8", "#0076B2CC", "#075B8EF5", "#075B8EFF"], start=(0.5, 0.0), end=(0.5, 1.0), radius=28, name="Hero OKLCH Blue Wash")

    # Floating Transparent Hero Navbar with Breathing Top Space (Unified Logo 12px + Centered Nav + Masuk CTA)
    draw_brand_mark(b, f, 68, 52, size=38, light=True)
    b.text(f, "DESI PRIVAT", 118, 60, size=17, color=SURFACE, weight="Bold", family=FONT_HEAD, width=160, max_lines=1)
    nav_links = {}
    for idx, nav in enumerate(["Beranda", "Prestasi", "Program"]):
        nx = 580 + idx * 116
        hit = b.rect(f, nx - 10, 54, 96, 34, fill="#FFFFFF10", radius=12, name=f"Landing Nav {nav}")
        b.text(f, nav, nx, 61, size=13.5, color=SURFACE, weight="SemiBold" if idx == 0 else "Medium", width=80, max_lines=1)
        nav_links[nav] = hit
    nav_login_btn = b.pill(f, 1248, 50, 120, 42, "Masuk", SECONDARY, SURFACE, size=13.5, weight="Bold", elevate=True, radius=12)

    # Centered Hero Copy & Bounded CTAs with Generous Top Whitespace
    b.text(f, "Bimbingan Belajar Privat\nyang Tenang & Terarah.", 300, 224, size=48, color=SURFACE, weight="Bold", family=FONT_HEAD, width=840, align="center", line_h=58)
    b.text(f, "Mentor terkurasi datang ke rumah dengan jadwal rapi dan laporan belajar langsung untuk orang tua.", 380, 364, size=17, color="#EBF7FD", width=680, align="center", line_h=27)

    cta_portal = b.pill(f, 558, 436, 162, 44, "Lihat Program", SECONDARY, SURFACE, size=14, weight="Bold", elevate=True, radius=12)
    cta_consult = b.pill(f, 736, 436, 146, 44, "Kontak Kami", "#FFFFFF22", SURFACE, size=14, weight="Bold", stroke="#FFFFFF88", radius=12)

    # Consistent 72px after-space between CTAs and metrics bar
    hero_metrics = [("84+", "Siswa Aktif"), ("18+", "Mentor"), ("8+", "Program"), ("98%", "Kepuasan Wali")]
    for i, (num, lbl) in enumerate(hero_metrics):
        mx = 360 + i * 180
        b.text(f, num, mx, 552, size=28, color=SURFACE, weight="Bold", family=FONT_HEAD, width=180, align="center", max_lines=1)
        b.text(f, lbl, mx, 590, size=13, color="#EBF7FD", weight="Medium", width=180, align="center", max_lines=1)

    # SCREEN 2: 3x2 PENCAPAIAN SISWA (GAMBAR 2 CARDS + ANIMATED EYE ICON-ONLY, ALL 6 POSTERS .WEBP)
    sec_prestasi = b.rect(f, 0, 824, 1440, 1316, fill=ALABASTER, radius=0, name="Section Pencapaian Siswa")
    b.text(f, "Pencapaian Siswa.", 72, 868, size=30, color=INK, weight="Bold", family=FONT_HEAD, width=620, max_lines=1)
    b.text(f, "Langkah nyata para siswa DESI PRIVAT di berbagai kompetisi akademik.", 72, 912, size=15.5, color=BODY, width=620, max_lines=1)

    achievements = [
        ("pencapaian_01.webp", "M. Ian Ramadhan", "Juara 3 Olimpiade Matematika SD pada Expo SMAFT 2026.", "Expo SMAFT 2026"),
        ("pencapaian_02.webp", "M. Ian Ramadhan", "Predikat Silver pada IOB Rising Star Mathematics.", "IOB Rising Star"),
        ("pencapaian_03.webp", "Kontingen DESI", "Melaju ke Babak Final Provinsi ajang lomba KMSI 2026.", "Final KMSI 2026"),
        ("pencapaian_04.webp", "M. Izhar Ismed", "Gold Medals Penyisihan Venus Kompetisi Rayon Makassar.", "Lolos Nasional"),
        ("pencapaian_05.webp", "M. Izhar Ismed", "Peserta Lomba Cerdas Cermat SEACOM 2026.", "SEACOM 2026"),
        ("pencapaian_06.webp", "M. Ian Ramadhan", "Peserta Lomba Cerdas Cermat SEACOM 2026.", "SEACOM 2026"),
    ]
    ach_btns = []
    for pi, (pimg, sname, sdesc, smeta) in enumerate(achievements):
        col = pi % 3
        row = pi // 3
        px = 72 + col * 438
        py = 964 + row * 572
        abtn = _draw_sophie_achievement_card(b, f, px, py, 418, 548, pimg, sname, sdesc, smeta, outer_r=28, inner_r=20)
        ach_btns.append(abtn)

    # SCREEN 3: PROGRAM BIMBINGAN (RINGKAS 1 BARIS, 4 KARTU SERAGAM CONCENTRIC RADIUS 20PX)
    act6_program = b.rect(f, 0, 2148, 1440, 360, fill=SURFACE, radius=0, name="Section Program Ringkas")
    b.text(f, "Program Bimbingan.", 72, 2200, size=30, color=INK, weight="Bold", family=FONT_HEAD, width=600, max_lines=1)
    b.text(f, "Setiap periode terdiri dari 8 pertemuan tatap muka berdurasi 90 menit.", 72, 2244, size=15.5, color=BODY, width=640, max_lines=1)
    progs = [
        ("01", "Privat SD", "Tematik, berhitung dasar & PR harian."),
        ("02", "Privat SMP", "Matematika, IPA terpadu & asesmen."),
        ("03", "Privat SMA & SNBT", "Saintek, Soshum & persiapan PTN."),
        ("04", "Inggris & Calistung", "Percakapan aktif & baca tulis dasar."),
    ]
    prog_btns = []
    for i, (no, pt, pd) in enumerate(progs):
        px = 72 + i * 328
        pcard = b.rect(f, px, 2292, 312, 180, fill=ALABASTER, radius=20, stroke=HAIRLINE, name=f"Program Card {pt}")
        b.text(f, no, px + 20, 2310, size=12, color=PRIMARY_DARK, weight="Bold", width=60, max_lines=1)
        b.text(f, pt, px + 20, 2334, size=17, color=INK, weight="Bold", family=FONT_HEAD, width=272, max_lines=1)
        b.text(f, pd, px + 20, 2362, size=13, color=BODY, width=272, max_lines=2)
        pbtn = b.pill(f, px + 20, 2414, 272, 38, "Rincian", PRIMARY_DEEP, SURFACE, size=12.5, weight="Bold", elevate=True, radius=12)
        prog_btns.append(pbtn)

    # SCREEN 4: PENUTUP RINGKAS + KONTAK TRANSPARAN
    sec_kontak = b.rect(f, 72, 2556, 1296, 136, fill=SURFACE, radius=24, stroke=HAIRLINE, name="Light Closing CTA Card")
    b.shadow(sec_kontak, blur=8, y=2, opacity=0.04)
    b.text(f, "Pantau Jadwal & Progres Belajar Anak.", 112, 2608, size=24, color=INK, weight="Bold", family=FONT_HEAD, width=680, max_lines=1)
    cta_wa = b.pill(f, 1020, 2602, 136, 44, "WhatsApp", SURFACE, INK, size=13.5, weight="Bold", stroke=HAIRLINE, radius=12)
    cta_close = b.pill(f, 1170, 2602, 158, 44, "Masuk Portal", SECONDARY, SURFACE, size=13.5, weight="Bold", elevate=True, radius=12)

    # Transparent Minimal Contact Line (No Solid Footer Color Block)
    b.rect(f, 72, 2784, 1296, 1, fill=HAIRLINE, radius=0, name="Minimal Contact Hairline")
    draw_brand_mark(b, f, 72, 2810, size=32, light=False)
    b.text(f, "DESI PRIVAT", 114, 2818, size=14, color=INK, weight="Bold", family=FONT_HEAD, width=140, max_lines=1)
    b.text(f, "0852-4200-9811    @desi_private    Makassar, Sulawesi Selatan    © 2026 DESI PRIVAT", 640, 2818, size=13, color=MUTED, width=728, align="right", max_lines=1)

    fl_bar = b.rect(f, 1344, 2890, 46, 46, fill=SURFACE, radius=14, stroke=HAIRLINE, name="Floating Icon-Only Back To Top")
    b.shadow(fl_bar, blur=12, y=4, opacity=0.14)
    b.icon(f, "arrow-up", 1358, 2904, size=18, color=PRIMARY_DEEP, stroke_w=1.75)

    # --- 2. login.html (Closing Gate Entrance, Unified Logo + Eye Icon Toggle) ---
    f2 = b.frame("login.html: Masuk ke Sistem", 1560, 0, 1440, 920, fill=ALABASTER, stroke=HAIRLINE)
    b.image(f2, "galeri_02.webp", 0, 0, 720, 920, mode="fill", name="Login Photo Left")
    b.gradient_rect(f2, 0, 0, 720, 920, ["#083A54F2", "#0093D6CC", "#0093D699"], start=(0.0, 1.0), end=(1.0, 0.0), name="Login Photo Fade")
    draw_brand_mark(b, f2, 64, 48, size=38, light=True)
    b.text(f2, "DESI PRIVAT", 114, 56, size=17, color=SURFACE, weight="Bold", family=FONT_HEAD, width=180, max_lines=1)

    b.text(f2, "Belajar Lebih Teratur.", 64, 386, size=38, color=SURFACE, weight="Bold", family=FONT_HEAD, width=540, max_lines=1)
    b.text(f2, "Jadwal, absensi, dan laporan perkembangan dalam satu portal.", 64, 444, size=16, color="#EBF7FD", width=480, line_h=25)

    back_home_btn = b.rect(f2, 1344, 32, 44, 44, fill=ALABASTER, radius=12, stroke=HAIRLINE, name="Login Top-Right Home Icon")
    b.icon(f2, "home", 1356, 44, size=20, color=INK, stroke_w=1.75)
    card = b.rect(f2, 850, 208, 460, 504, fill=SURFACE, radius=20, stroke=HAIRLINE, name="Centered Login Card")
    b.shadow(card, blur=12, y=4, opacity=0.05)
    b.text(f2, "Masuk", 890, 250, size=24, color=INK, weight="Bold", family=FONT_HEAD, width=380, max_lines=1)

    b.text(f2, "ID Pengguna", 890, 306, size=13.5, color=INK, weight="Bold")
    b.rect(f2, 890, 334, 380, 48, fill=ALABASTER, radius=12, stroke=HAIRLINE)
    b.text(f2, "Masukkan ID pengguna Anda", 906, 349, size=14, color=MUTED, width=348, max_lines=1)

    b.text(f2, "Kata Sandi", 890, 404, size=13.5, color=INK, weight="Bold")
    b.rect(f2, 890, 432, 380, 48, fill=ALABASTER, radius=12, stroke=HAIRLINE)
    b.text(f2, "Masukkan kata sandi", 906, 447, size=14, color=MUTED, width=300, max_lines=1)
    pw_eye_btn = b.rect(f2, 1222, 438, 36, 36, fill=SURFACE, radius=10, stroke=HAIRLINE, name="Animated Password Eye Toggle")
    b.icon(f2, "eye", 1231, 447, size=18, color=BODY, stroke_w=1.75)

    b.rect(f2, 890, 502, 16, 16, fill=SURFACE, radius=4, stroke=HAIRLINE)
    b.text(f2, "Ingat Saya", 914, 502, size=13, color=BODY, weight="Medium")
    forgot_hit = b.rect(f2, 1140, 496, 134, 28, fill=SURFACE, radius=10, name="Forgot Password Hit")
    b.text(f2, "Lupa Kata Sandi?", 1150, 502, size=13, color=SECONDARY_DARK, weight="Bold", width=120, align="right")

    login_submit_btn = b.pill(f2, 890, 546, 380, 48, "Masuk", SECONDARY, SURFACE, size=14.5, weight="Bold", elevate=True, radius=12)
    help_hit = b.rect(f2, 950, 616, 260, 30, fill=SURFACE, radius=10, name="Login Help Hit")
    b.text(f2, "Butuh bantuan? Hubungi Admin", 890, 622, size=13, color=MUTED, width=380, align="center", max_lines=1)
    b.rect(f2, 718, 0, 4, 920, fill="#38BDF866", radius=0, name="Closing Gate Center Seam")

    # --- 3. Post-Click Interactive Layers on Page 01 ---
    ov_poster = b.frame("Overlay: Lightbox Poster Pencapaian", 1560, 1020, 440, 600, fill=SURFACE, radius=28, stroke=HAIRLINE)
    b.shadow(ov_poster, blur=20, y=8, opacity=0.14)
    b.text(ov_poster, "Poster Pencapaian Siswa", 20, 20, size=16, color=INK, weight="Bold", family=FONT_HEAD, width=340, max_lines=1)
    ov_poster_x = b.pill(ov_poster, 384, 14, 36, 36, "×", ALABASTER, INK, size=16, weight="Bold", stroke=HAIRLINE, radius=12)
    b.close_overlay_link(ov_poster_x)
    b.rect(ov_poster, 10, 62, 420, 528, fill=ALABASTER, radius=18, stroke=HAIRLINE, name="Poster Rounded 18px Frame")
    b.image(ov_poster, "pencapaian_01.webp", 10, 62, 420, 528, mode="fill", name="Poster Lightbox Preview")

    ov_prog = b.frame("Overlay: Drawer Detail Program", 2100, 1020, 460, 520, fill=SURFACE, radius=16, stroke=HAIRLINE)
    b.shadow(ov_prog, blur=16, y=6, opacity=0.10)
    ov_prog_x = b.pill(ov_prog, 396, 20, 36, 36, "×", ALABASTER, INK, size=16, weight="Bold", stroke=HAIRLINE, radius=12)
    b.close_overlay_link(ov_prog_x)
    b.text(ov_prog, "Privat SMP", 24, 24, size=22, color=INK, weight="Bold", family=FONT_HEAD, width=356, max_lines=1)
    b.text(ov_prog, "Penguatan konsep inti Matematika, IPA, dan Bahasa Inggris dengan latihan terstruktur sesuai ritme siswa.", 24, 64, size=14, color=BODY, width=412, line_h=22)
    b.rect(ov_prog, 24, 144, 412, 100, fill=ALABASTER, radius=12, stroke=HAIRLINE)
    b.text(ov_prog, "FOKUS PEMBELAJARAN", 40, 160, size=11, color=PRIMARY_DARK, weight="Bold", width=380, max_lines=1)
    b.text(ov_prog, "Aljabar, geometri, fisika dasar, biologi terpadu, dan asesmen sekolah.", 40, 182, size=13, color=INK, width=380, line_h=20)
    b.rect(ov_prog, 24, 258, 412, 88, fill=ALABASTER, radius=12, stroke=HAIRLINE)
    b.text(ov_prog, "RITME PERTEMUAN", 40, 274, size=11, color=PRIMARY_DARK, weight="Bold", width=380, max_lines=1)
    b.text(ov_prog, "8 Sesi per periode (90 menit/sesi) dan evaluasi lengkap.", 40, 296, size=13, color=INK, width=380, line_h=20)
    ov_prog_login = b.pill(ov_prog, 24, 388, 412, 44, "Konsultasi", SECONDARY, SURFACE, size=13.5, weight="Bold", elevate=True, radius=12)
    ov_prog_close = b.pill(ov_prog, 24, 444, 412, 40, "Tutup", ALABASTER, INK, size=13, weight="SemiBold", stroke=HAIRLINE, radius=12)
    b.close_overlay_link(ov_prog_login)
    b.close_overlay_link(ov_prog_close)

    ov_forgot, ov_forgot_sub = draw_modal_layer(
        b, "Overlay: Modal Lupa Kata Sandi", 2620, 1020,
        "Lupa Kata Sandi",
        "Pemulihan akses akun ditangani aman melalui verifikasi Admin",
        [("ID Pengguna Terdaftar", "Contoh: parent1 / mentor1 / admin"),
         ("Nomor WhatsApp Wali/Mentor", "0852-4200-9811")],
        "Kirim Permintaan", accent=SECONDARY, w=480
    )

    ov_help, ov_help_sub = draw_modal_layer(
        b, "Overlay: Modal Hubungi Admin WA", 1560, 1700,
        "Hubungi Admin DESI PRIVAT",
        "Bantuan aktivasi akun portal orang tua, mentor, dan penjadwalan",
        [("Layanan WhatsApp Resmi", "0852-4200-9811 (Senin sampai Sabtu)"),
         ("Kebutuhan Bantuan", "Reset kata sandi atau penautan akun siswa")],
        "Tutup & Salin Kontak", accent=PRIMARY, w=480, cancel_lbl="Batal"
    )

    ov_pub_toast = draw_toast_layer(
        b, "Overlay: Toast Konfirmasi Terkirim", 2100, 1700,
        "Permintaan Diterima",
        "Admin DESI PRIVAT akan memverifikasi akun Anda segera.",
        accent=OK_TXT
    )

    # Wire ALL interactions cleanly across Page 01
    b.flow(f, "Public & Auth Flow (4x3 Hero Mosaic + Sophie Cards)")
    b.scroll_link(nav_links["Beranda"], act1_hero)
    b.scroll_link(nav_links["Prestasi"], sec_prestasi)
    b.scroll_link(nav_links["Program"], act6_program)
    b.scroll_link(cta_portal, act6_program)
    b.scroll_link(cta_consult, sec_kontak)

    b.link(nav_login_btn, f2, trans="moveIn", direction="left", duration=360, easing="easeOut")
    b.link(cta_close, f2, trans="moveIn", direction="left", duration=360, easing="easeOut")
    b.link(back_home_btn, f, trans="slideIn", direction="right", duration=288, easing="easeOut")

    for ab in ach_btns:
        b.overlay_link(ab, ov_poster, trans="dissolve", duration=220, easing="easeOut")
    for pb in prog_btns:
        b.overlay_link(pb, ov_prog, trans="moveIn", direction="left", duration=260, easing="easeOut")
    b.overlay_link(cta_wa, ov_help, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    b.overlay_link(forgot_hit, ov_forgot, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    b.overlay_link(help_hit, ov_help, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    b.overlay_link(pw_eye_btn, ov_pub_toast, trans="dissolve", duration=180, easing="easeOut")
    b.swap_overlay_link(ov_forgot_sub, ov_pub_toast)
    b.swap_overlay_link(ov_help_sub, ov_pub_toast)
    b.overlay_link(login_submit_btn, ov_pub_toast, trans="dissolve", duration=200, easing="easeOut")


# ==============================================================================
# PAGE 3: ADMIN OPERASIONAL (8) + ASYMMETRIC DASHBOARD & TRANSITIONS
# ==============================================================================
def build_page_02_admin_ops(b: FigBuilder):
    b.page_add("02 - Admin Operasional (8)")
    b.page_bg("#EAEAE6")

    # 1. admin/dashboard.html — Seragam, Tenang, Tanpa Ikon/3D Berlebih + Agenda Scroll
    fd, cy, nav_d, cta_d, _ = draw_app_shell(
        b, "admin/dashboard.html", 0, 0, "admin", "Dashboard Utama",
        "Pusat Operasional DESI PRIVAT",
        "Ringkasan jadwal hari ini, mentor siap mengajar, dan tindakan cepat",
        "+ Jadwal", None, primary_icon="plus"
    )
    # Left Column (720px): Sheet KPI Seragam + Tabel Jadwal & Kehadiran
    sheet = b.rect(fd, 284, cy, 720, 260, fill=SURFACE, radius=12, stroke=HAIRLINE, name="Admin KPI Sheet")
    b.shadow(sheet, blur=8, y=2, opacity=0.03)
    for pi, plbl in enumerate(["Siswa", "Mentor", "Tagihan", "Notifikasi"]):
        b.pill(fd, 304 + pi * 92, cy + 16, 82, 28, plbl, ALABASTER, BODY, size=11.5, weight="SemiBold", stroke=HAIRLINE)
    b.text(fd, "Total Sesi Terabsen", 304, cy + 58, size=11.5, color=MUTED, weight="Bold", width=220, max_lines=1)
    b.text(fd, "136", 304, cy + 78, size=34, color=INK, weight="Bold", family=FONT_HEAD, width=110, max_lines=1)
    b.text(fd, "142 sesi bulan ini, 6 hari ini", 392, cy + 92, size=12, color=PRIMARY_DARK, weight="Bold", width=320, max_lines=1)

    for ki, (klbl, kval, ksub) in enumerate([
        ("Siswa Aktif", "84", "Terdaftar resmi"),
        ("Perlu Perhatian", "3", "Kendala / ganti mentor"),
        ("Mentor Aktif", "18", "Tenaga pengajar"),
    ]):
        kx = 304 + ki * 232
        b.rect(fd, kx, cy + 128, 216, 82, fill=SURFACE, radius=12, stroke=HAIRLINE, name=f"Uniform KPI {klbl}")
        b.text(fd, klbl, kx + 16, cy + 140, size=11.5, color=MUTED, weight="SemiBold", width=184, max_lines=1)
        b.text(fd, kval, kx + 16, cy + 160, size=22, color=INK, weight="Bold", family=FONT_HEAD, width=184, max_lines=1)
        b.text(fd, ksub, kx + 16, cy + 188, size=11, color=MUTED, width=184, max_lines=1)

    b.rect(fd, 304, cy + 224, 680, 8, fill="#F1F1EE", radius=4)
    b.rect(fd, 304, cy + 224, 624, 8, fill=PRIMARY, radius=4)
    b.text(fd, "92% Terabsen (136 sesi) ,  8% Belum Terabsen (12 sesi)", 304, cy + 238, size=11.5, color=MUTED, weight="SemiBold", width=580, max_lines=1)

    draw_table_card(
        b, fd, cy + 280,
        "Jadwal Bimbingan & Kehadiran Hari Ini",
        ["Waktu", "Siswa", "Mentor", "Status"],
        [
            ["15:30 - 17:00", "Naufal Pratama", "Kak Sarah", "Disetujui"],
            ["16:00 - 17:30", "Alisha Putri", "Kak Dian", "Disetujui"],
            ["17:00 - 18:30", "Kevin Ardiansyah", "Kak Budi", "Perlu Pengganti"],
            ["18:30 - 20:00", "Rania Azzahra", "Kak Sarah", "Disetujui"],
            ["19:00 - 20:30", "Dimas Pratama", "Kak Raka", "Menunggu"],
        ],
        x=284, w=720, h=498
    )

    # Right Rail (1028px, 376px): Agenda Hari Ini dengan Scroll Area (> 3 agenda)
    rail = b.rect(fd, 1028, cy, 376, 778, fill=SURFACE, radius=12, stroke=HAIRLINE, name="Admin Scrollable Agenda Rail")
    b.shadow(rail, blur=8, y=2, opacity=0.03)
    b.text(fd, "Agenda Hari Ini", 1048, cy + 20, size=15.5, color=INK, weight="Bold", family=FONT_HEAD, width=220, max_lines=1)
    b.text(fd, "6 sesi", 1304, cy + 22, size=12, color=MUTED, weight="Bold", width=78, align="right", max_lines=1)

    b.rect(fd, 1048, cy + 54, 336, 94, fill=SECONDARY_SOFT, radius=12, stroke=SECONDARY_BORDER)
    b.text(fd, "1 Mentor Berhalangan", 1064, cy + 66, size=13, color=SECONDARY_DARK, weight="Bold", width=304, max_lines=1)
    b.text(fd, "Kevin (17:00), Kak Budi berhalangan hadir.", 1064, cy + 86, size=12, color=BODY, width=304, max_lines=1)
    alert_btn = b.pill(fd, 1064, cy + 110, 120, 30, "Pengganti", DANGER_TXT, SURFACE, size=11.5, weight="Bold")

    # Scrollable Viewport (cy+164 .. cy+686) showing 4 cards + peeking 5th + right scrollbar
    scroll_vp = b.rect(fd, 1048, cy + 164, 336, 514, fill=ALABASTER, radius=12, stroke=HAIRLINE, name="Agenda Scroll Viewport (>3 Sesi)")
    agenda_cards = [
        ("15:30 WIB", "Matematika SMP", "Naufal Pratama", "Kak Sarah"),
        ("16:00 WIB", "Calistung SD", "Alisha Putri", "Kak Dian"),
        ("17:00 WIB", "Fisika SMA", "Kevin Ardiansyah", "Kak Raka"),
        ("18:30 WIB", "Bahasa Inggris", "Rania Azzahra", "Kak Sarah"),
        ("19:30 WIB", "Persiapan SNBT", "Dimas Pratama", "Kak Raka"),
    ]
    for ti, (tt, tprog, tst, tmn) in enumerate(agenda_cards):
        ty = cy + 174 + ti * 102
        if ty >= cy + 670:
            break
        card_h = 92 if ti < 4 else 58
        b.rect(fd, 1058, ty, 304, card_h, fill=SURFACE, radius=12, stroke=HAIRLINE, name=f"Agenda Item {ti+1}")
        b.text(fd, tst, 1072, ty + 12, size=13.5, color=INK, weight="Bold", family=FONT_HEAD, width=168, max_lines=1)
        b.text(fd, tprog, 1244, ty + 14, size=11, color=MUTED, weight="SemiBold", width=106, align="right", max_lines=1)
        b.text(fd, tmn, 1072, ty + 32, size=11.5, color=MUTED, width=168, max_lines=1)
        if ti < 4:
            b.text(fd, f"{tt}, 90 Menit", 1072, ty + 58, size=11.5, color=BODY, weight="SemiBold", width=160, max_lines=1)
            b.pill(fd, 1266, ty + 52, 84, 30, "Detail", PRIMARY_DEEP, SURFACE, size=11.5, weight="Bold")
    # Fade overlay indicating scrollable overflow + slim scrollbar thumb
    b.gradient_rect(fd, 1050, cy + 610, 316, 66, ["#F7F7F500", "#F7F7F5EE", "#F7F7F5FF"], start=(0.5, 0.0), end=(0.5, 1.0), radius=12, name="Agenda Bottom Scroll Fade")
    b.rect(fd, 1372, cy + 174, 5, 494, fill="#EAEAE6", radius=2.5, name="Agenda Scrollbar Track")
    b.rect(fd, 1372, cy + 178, 5, 224, fill="#94A3B8", radius=2.5, name="Agenda Scrollbar Thumb")
    b.text(fd, "Gulir untuk melihat 6 agenda hari ini", 1048, cy + 688, size=11.5, color=MUTED, weight="SemiBold", width=336, align="center", max_lines=1)
    b.pill(fd, 1048, cy + 716, 336, 42, "+ Jadwal", PRIMARY, SURFACE, size=13, weight="Bold")

    specs = [
        ("admin/schedules.html", "Penjadwalan Les", "Penjadwalan Les Privat", "Kelola jadwal satuan, jadwal rutin mingguan & deteksi bentrokan", "Tambah Jadwal Rutin", None, "calendar",
         [("142", "Jadwal Aktif", "Periode berjalan", PRIMARY_SOFT, PRIMARY_DARK, "calendar"), ("0", "Bentrok Terdeteksi", "Validasi otomatis", OK_BG, OK_TXT, "calendar-check"), ("4", "Menunggu Konfirmasi", "Koordinasi wali/mentor", SECONDARY_SOFT, SECONDARY_DARK, "clock")],
         "Daftar Jadwal Les Rutin & Satuan",
         ["Hari & Jam", "Siswa & Kelas", "Program & Fokus", "Mentor", "Wali Murid", "Status"],
         [["Senin, 15:30", "Naufal (8 SMP)", "Matematika", "Kak Sarah", "Ibu Ratna", "Disetujui"],
          ["Selasa, 16:00", "Alisha (3 SD)", "Calistung", "Kak Dian", "Ibu Ratna", "Disetujui"],
          ["Rabu, 17:00", "Kevin (11 SMA)", "Fisika SNBT", "Kak Budi", "Bpk. Hendra", "Ganti Sementara"],
          ["Kamis, 18:30", "Rania (6 SD)", "Bahasa Inggris", "Kak Sarah", "Ibu Sinta", "Menunggu"]]),

        ("admin/students.html", "Data Siswa", "Kelola Data Siswa", "Daftar lengkap peserta bimbingan aktif, nonaktif, dan arsip", "Tambah Siswa Baru", None, "plus",
         [("84", "Siswa Aktif", "Sedang berjalan", PRIMARY_SOFT, PRIMARY_DARK, "graduation"), ("12", "Siswa Baru", "Bulan ini", SECONDARY_SOFT, SECONDARY_DARK, "sparkles"), ("6", "Arsip / Lulus", "Riwayat tersimpan", SUBTLE_BG, MUTED, "history")],
         "Direktori Siswa DESI PRIVAT",
         ["ID", "Nama Siswa", "Sekolah & Kelas", "Wali Murid", "Program Les", "Status"],
         [["#101", "Naufal Pratama", "SMPN 1, 8B", "Ibu Ratna", "Matematika SMP", "Aktif"],
          ["#102", "Alisha Putri", "SDN 3, 3A", "Ibu Ratna", "Calistung & SD", "Aktif"],
          ["#103", "Kevin Ardiansyah", "SMAN 2, 11 IPA", "Bpk. Hendra", "Fisika SMA", "Aktif"],
          ["#104", "Dimas Pratama", "SMAN 1, 12 IPA", "Ibu Maya", "Persiapan SNBT", "Arsip"]]),

        ("admin/student_detail.html", "Data Siswa", "Detail Profil Siswa: Naufal Pratama", "Siklus periode pertemuan, program les terdaftar & riwayat belajar", "Tambah Program", "Kembali ke Daftar Siswa", "plus",
         [("2", "Program Terdaftar", "Matematika & Inggris", PRIMARY_SOFT, PRIMARY_DARK, "book"), ("6 / 8", "Siklus Periode", "Pertemuan ke-6 aktif", SECONDARY_SOFT, SECONDARY_DARK, "clock"), ("100%", "Kehadiran", "Bulan berjalan", OK_BG, OK_TXT, "check")],
         "Program Les & Siklus Pertemuan Siswa",
         ["Program Les", "Siklus Periode", "Mentor Pengampu", "Mulai / Selesai", "Status"],
         [["Matematika SMP", "Periode #3 (6/8)", "Kak Sarah", "01 Nov - 30 Nov", "Aktif"],
          ["Bahasa Inggris SMP", "Periode #1 (4/8)", "Kak Sarah", "10 Nov - 10 Des", "Aktif"],
          ["Matematika SMP", "Periode #2 (8/8)", "Kak Sarah", "01 Okt - 31 Okt", "Selesai"]]),

        ("admin/mentors.html", "Data Mentor", "Kelola Data Mentor Pengajar", "Profil, bidang keahlian, ketersediaan waktu, dan beban mengajar", "Tambah Mentor Baru", None, "plus",
         [("18", "Mentor Aktif", "Tersertifikasi", PRIMARY_SOFT, PRIMARY_DARK, "mentor"), ("5", "Tersedia Sore", "Slot 15:00 - 18:00", OK_BG, OK_TXT, "clock"), ("1", "Izin Sementara", "Butuh backup", SECONDARY_SOFT, SECONDARY_DARK, "alert")],
         "Daftar Mentor Pengajar",
         ["ID", "Nama Lengkap", "Kontak", "Bidang Keahlian", "Beban Aktif", "Status"],
         [["M-01", "Sarah Amelia, S.Pd", "0812-3400-1122", "Matematika & Inggris", "14 Sesi/mg", "Aktif"],
          ["M-02", "Budi Santoso, S.Si", "0813-5522-8899", "Fisika & Kimia SMA", "10 Sesi/mg", "Aktif"],
          ["M-03", "Dian Permata, S.Pd", "0856-9911-3344", "Calistung & Tematik SD", "12 Sesi/mg", "Aktif"]]),

        ("admin/parents.html", "Orang Tua / Wali", "Kelola Data Orang Tua / Wali Murid", "Hubungan multi-anak, kontak WhatsApp resmi, dan akun portal wali", "Tambah Data Wali", None, "plus",
         [("68", "Wali Terdaftar", "Terhubung siswa", PRIMARY_SOFT, PRIMARY_DARK, "family"), ("64", "Akun Portal Aktif", "Login mandiri", OK_BG, OK_TXT, "key"), ("14", "Multi-Anak", ">= 2 anak", SECONDARY_SOFT, SECONDARY_DARK, "users")],
         "Daftar Orang Tua / Wali Murid",
         ["ID", "Nama Wali", "Kontak & WhatsApp", "Anak Terhubung", "Akun Login", "Status"],
         [["W-01", "Ibu Ratna Sari", "0812-8800-4821", "Naufal, Alisha (2)", "parent1 (Aktif)", "Aktif"],
          ["W-02", "Bapak Hendra Wijaya", "0811-7722-9012", "Kevin Ardiansyah", "parent2 (Aktif)", "Aktif"],
          ["W-03", "Ibu Sinta Dewi", "0857-4411-6620", "Rania Azzahra", "Belum Ada", "Menunggu"]]),

        ("admin/programs.html", "Program Les", "Kelola Program Les Privat", "Pengaturan jenjang pendidikan, paket pertemuan, dan status layanan", "Tambah Program Baru", None, "plus",
         [("8", "Program Aktif", "SD, SMP, SMA, Umum", PRIMARY_SOFT, PRIMARY_DARK, "book"), ("84", "Siswa Terdaftar", "Total paket aktif", SECONDARY_SOFT, SECONDARY_DARK, "graduation"), ("2", "Program Arsip", "Nonaktif", SUBTLE_BG, MUTED, "history")],
         "Katalog Program Bimbingan Belajar",
         ["No", "Nama Program / Mapel", "Jenjang", "Jenis Layanan", "Kode", "Siswa", "Status"],
         [["1", "Matematika Terpadu", "SMP", "Privat Rumah", "MTK-SMP", "26", "Aktif"],
          ["2", "Calistung & Tematik", "SD", "Privat Rumah", "CAL-SD", "22", "Aktif"],
          ["3", "Fisika & Persiapan SNBT", "SMA", "Intensif", "FIS-SMA", "18", "Aktif"],
          ["4", "English Kids Conversation", "Umum", "Privat Rumah", "ENG-KID", "18", "Aktif"]]),

        ("admin/notifications.html", "Pemberitahuan", "Pusat Pemberitahuan Sistem & WhatsApp", "Notifikasi in-app dan log pengiriman WhatsApp Business API", "Tandai Semua Dibaca", None, "check",
         [("24", "Notifikasi Hari Ini", "In-app & WA", PRIMARY_SOFT, PRIMARY_DARK, "bell"), ("100%", "Log Tervalidasi", "Tercatat real-time", OK_BG, OK_TXT, "shield"), ("1", "Perlu Tindak Lanjut", "Respon mentor >24j", SECONDARY_SOFT, SECONDARY_DARK, "alert")],
         "Riwayat Notifikasi & Pengiriman WhatsApp",
         ["Waktu", "Penerima", "Kategori", "Ringkasan Pesan", "Status"],
         [["Hari ini 14:00", "Ibu Ratna (0812xxx)", "Pengingat Sesi", "Jadwal Naufal pukul 15:30 WIB", "Terkirim"],
          ["Hari ini 11:20", "Kak Budi", "Konfirmasi Jadwal", "Menunggu konfirmasi sesi Fisika", "Menunggu"],
          ["Kemarin 19:05", "Bapak Hendra", "Laporan Belajar", "Laporan perkembangan Kevin tersedia", "Terkirim"]]),
    ]

    frames = {"admin/dashboard.html": fd}
    nav_maps = {"admin/dashboard.html": nav_d}
    ctas = {"admin/dashboard.html": cta_d}
    secs = {"admin/dashboard.html": None}
    row0s = {}
    for idx, (fname, anav, ptitle, psub, pcta, scta, pic, kpis, ttitle, cols, rows) in enumerate(specs, start=1):
        col = idx % 4
        row = idx // 4
        f, cy, navs, cta_b, sec_b = draw_app_shell(
            b, fname, col * 1540, row * 1060, "admin", anav, ptitle, psub, pcta, scta,
            primary_icon=pic, secondary_icon="arrow-left" if scta else None
        )
        cy = draw_kpi_strip(b, f, cy, kpis)
        row0 = draw_table_card(b, f, cy, ttitle, cols, rows)
        frames[fname] = f
        nav_maps[fname] = navs
        ctas[fname] = cta_b
        secs[fname] = sec_b
        row0s[fname] = row0

    b.flow(frames["admin/dashboard.html"], "Admin Operasional Flow")

    # Page 02 Post-Click Interactive Layers (y=2160)
    ov_sched, ov_sched_sub = draw_modal_layer(
        b, "Overlay: Modal Buat Jadwal Rutin", 0, 2160,
        "Buat Jadwal Rutin & Satuan",
        "Penjadwalan otomatis 8 sesi dengan validasi anti-bentrok",
        [("Siswa & Program", "Naufal Pratama, Matematika SMP"),
         ("Mentor Pengampu", "Kak Sarah Amelia (Tersedia)"),
         ("Hari & Jam Belajar", "Senin & Kamis, 15:30 - 17:00 WIB")],
        "Simpan Jadwal", accent=SECONDARY, w=480
    )
    ov_replace, ov_replace_sub = draw_modal_layer(
        b, "Overlay: Modal Ganti Mentor Pengganti", 520, 2160,
        "Pilih Mentor Pengganti",
        "Kevin Ardiansyah (17:00 WIB), Pengganti Kak Budi",
        [("Mentor Pengganti Tersedia", "Kak Raka Pratama (0 Bentrok)"),
         ("Alasan Pergantian Wajib", "Mentor awal berhalangan tugas mendadak")],
        "Tetapkan Pengganti", accent=DANGER_TXT, w=480
    )
    ov_student, ov_student_sub = draw_modal_layer(
        b, "Overlay: Modal Tambah Siswa Baru", 1040, 2160,
        "Tambah Data Siswa Baru",
        "Tautkan otomatis dengan akun Orang Tua / Wali Murid",
        [("Nama Lengkap & Sekolah", "Contoh: Nadia Azzahra, SMPN 2"),
         ("Wali Murid Terhubung", "Ibu Sinta Dewi (0857-4411-6620)"),
         ("Program Awal", "Bahasa Inggris SMP (8 Sesi)")],
        "Simpan Data Siswa", accent=PRIMARY, w=480
    )
    ov_master, ov_master_sub = draw_modal_layer(
        b, "Overlay: Modal Tambah Master Data", 1560, 2160,
        "Tambah Mentor / Wali / Program",
        "Formulir pencatatan master data operasional DESI PRIVAT",
        [("Nama / Judul Entitas", "Isi nama lengkap mentor atau program"),
         ("Kategori & Kontak", "Bidang keahlian / Nomor WhatsApp aktif")],
        "Simpan Perubahan", accent=SECONDARY, w=480
    )
    ov_notif_pop, ov_notif_all = draw_popover_layer(
        b, "Overlay: Popover Notifikasi Topbar", 2080, 2160,
        "Notifikasi Terbaru",
        [("1 Mentor Berhalangan", "Kevin (17:00) menunggu mentor pengganti", DANGER_TXT),
         ("Pengingat WA Terkirim", "Ibu Ratna, Jadwal Naufal 15:30 WIB", OK_TXT),
         ("Laporan Belajar Masuk", "Kak Sarah menyimpan rapor Naufal", PRIMARY)],
        footer_lbl="Lihat Semua Pemberitahuan"
    )
    ov_logout, ov_logout_btn = draw_modal_layer(
        b, "Overlay: Modal Konfirmasi Keluar", 2480, 2160,
        "Keluar dari Sesi Admin?",
        "Semua data operasional tersimpan aman di database SQLite",
        [("Pengguna Aktif", "Admin Pengelola (admin)")],
        "Keluar Sekarang", accent=INK, w=440, cancel_lbl="Tetap Masuk"
    )
    ov_ops_toast = draw_toast_layer(
        b, "Overlay: Toast Operasional Tersimpan", 2960, 2160,
        "Perubahan Berhasil Disimpan",
        "Jadwal, data master, dan log aktivitas telah diperbarui.",
        accent=OK_TXT
    )

    b.overlay_link(alert_btn, ov_replace, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    if row0s.get("admin/students.html"):
        b.link(row0s["admin/students.html"], frames["admin/student_detail.html"], trans="moveIn", direction="left", duration=320, easing="easeOut")
    if ctas["admin/dashboard.html"]:
        b.overlay_link(ctas["admin/dashboard.html"], ov_sched, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    if ctas.get("admin/schedules.html"):
        b.overlay_link(ctas["admin/schedules.html"], ov_sched, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    if ctas.get("admin/students.html"):
        b.overlay_link(ctas["admin/students.html"], ov_student, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    if ctas.get("admin/student_detail.html"):
        b.overlay_link(ctas["admin/student_detail.html"], ov_student, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    for m_cta in ["admin/mentors.html", "admin/parents.html", "admin/programs.html"]:
        if ctas.get(m_cta):
            b.overlay_link(ctas[m_cta], ov_master, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    if ctas.get("admin/notifications.html"):
        b.overlay_link(ctas["admin/notifications.html"], ov_ops_toast, trans="dissolve", duration=200, easing="easeOut")
    if secs["admin/student_detail.html"]:
        b.link(secs["admin/student_detail.html"], frames["admin/students.html"], trans="slideIn", direction="right", duration=256, easing="easeOut")

    b.link(ov_notif_all, frames["admin/notifications.html"], trans="moveIn", direction="left", duration=260, easing="easeOut")
    for sub in [ov_sched_sub, ov_replace_sub, ov_student_sub, ov_master_sub, ov_logout_btn]:
        b.swap_overlay_link(sub, ov_ops_toast)

    nav_targets = {
        "Dashboard Utama": "admin/dashboard.html",
        "Penjadwalan Les": "admin/schedules.html",
        "Data Siswa": "admin/students.html",
        "Data Mentor": "admin/mentors.html",
        "Orang Tua / Wali": "admin/parents.html",
        "Program Les": "admin/programs.html",
        "Pemberitahuan": "admin/notifications.html",
    }
    for src_name, n_dict in nav_maps.items():
        if "__bell__" in n_dict:
            b.overlay_link(n_dict["__bell__"], ov_notif_pop, trans="dissolve", duration=180, easing="easeOut", dim="#11182722")
        if "__logout__" in n_dict:
            b.overlay_link(n_dict["__logout__"], ov_logout, trans="moveIn", direction="bottom", duration=220, easing="easeOut")
        if "__search__" in n_dict:
            b.link(n_dict["__search__"], frames["admin/students.html"], trans="dissolve", duration=200, easing="easeOut")
        for lbl, dst_name in nav_targets.items():
            if dst_name != src_name and lbl in n_dict:
                b.link(n_dict[lbl], frames[dst_name], trans="push", direction="left", duration=280, easing="easeInOut")


# ==============================================================================
# PAGE 4: ADMIN KEUANGAN & SISTEM (8)
# ==============================================================================
def build_page_03_admin_fin_sys(b: FigBuilder):
    b.page_add("03 - Admin Keuangan & Sistem (8)")
    b.page_bg("#EAEAE6")

    specs = [
        ("admin/bills.html", "Tagihan & Cicilan", "Tagihan & Pembayaran Siswa", "Monitor invoice per periode, cicilan wali murid, dan penagihan WhatsApp", "Buat Tagihan Baru", "Tagih via WA", "receipt", "phone",
         [("Rp 24,5 Jt", "Total Tagihan Aktif", "Periode November", PRIMARY_SOFT, PRIMARY_DARK, "receipt"), ("Rp 19,2 Jt", "Sudah Dibayar", "78% terkumpul", OK_BG, OK_TXT, "check"), ("Rp 5,3 Jt", "Sisa Tunggakan", "5 siswa cicilan", SECONDARY_SOFT, SECONDARY_DARK, "alert")],
         "Daftar Tagihan & Cicilan Siswa",
         ["Kode Tagihan", "Siswa & Program", "Wali Murid", "Total", "Dibayar", "Status"],
         [["INV-2026-081", "Naufal, Matematika", "Ibu Ratna", "Rp 800.000", "Rp 800.000", "Lunas"],
          ["INV-2026-082", "Alisha, Calistung", "Ibu Ratna", "Rp 650.000", "Rp 325.000", "Cicilan"],
          ["INV-2026-083", "Kevin, Fisika SMA", "Bpk. Hendra", "Rp 1.000.000", "Rp 0", "Tunggakan"]]),

        ("admin/payments.html", "Riwayat Pembayaran", "Riwayat Pembayaran & Transaksi Murid", "Catatan kuitansi resmi, metode transfer/tunai, dan koreksi pembayaran", None, "Kembali ke Tagihan", "plus", "arrow-left",
         [("42", "Transaksi Masuk", "Bulan ini", PRIMARY_SOFT, PRIMARY_DARK, "credit-card"), ("Rp 19,2 Jt", "Total Diterima", "Terverifikasi", OK_BG, OK_TXT, "check"), ("100%", "Kuitansi Siap Cetak", "Format PDF/Print", SECONDARY_SOFT, SECONDARY_DARK, "printer")],
         "Riwayat Transaksi Pembayaran",
         ["No. Kuitansi", "Tanggal Bayar", "Siswa & Program", "Wali Murid", "Nominal", "Metode"],
         [["KW-2611-019", "25 Nov 2026", "Naufal, Matematika", "Ibu Ratna", "Rp 800.000", "Transfer BCA"],
          ["KW-2611-018", "22 Nov 2026", "Alisha, Calistung", "Ibu Ratna", "Rp 325.000", "QRIS"],
          ["KW-2611-017", "20 Nov 2026", "Rania, Inggris", "Ibu Sinta", "Rp 700.000", "Tunai"]]),

        ("admin/mentor_honor.html", "Honor Mentor", "Monitoring & Rekapitulasi Honor Mentor", "Perhitungan sesi terlaksana, izin siswa, dan kelayakan pencairan periode 8 sesi", None, None, "wallet", None,
         [("18", "Mentor Aktif", "Periode berjalan", PRIMARY_SOFT, PRIMARY_DARK, "mentor"), ("136", "Sesi Terabsen", "Terverifikasi foto", OK_BG, OK_TXT, "camera"), ("Rp 11,8 Jt", "Estimasi Honor", "Siap disalurkan", SECONDARY_SOFT, SECONDARY_DARK, "wallet")],
         "Rekapitulasi Honor Mengajar Mentor",
         ["Nama Mentor", "Keahlian", "Sesi Terlaksana", "Izin/Batal", "Periode 8 Sesi", "Estimasi Honor"],
         [["Kak Sarah", "Matematika & Inggris", "28 Sesi", "1 Izin", "3 Periode Penuh", "Rp 2.800.000"],
          ["Kak Dian", "Calistung & SD", "24 Sesi", "0", "3 Periode Penuh", "Rp 2.160.000"],
          ["Kak Budi", "Fisika & Kimia SMA", "18 Sesi", "2 Izin", "2 Periode Penuh", "Rp 1.980.000"]]),

        ("admin/accounts.html", "Manajemen Akun", "Manajemen Akun Pengguna", "Pengaturan akses login Admin, Pemilik, Mentor, dan Wali Murid", "Buat Akun Baru", None, "key", None,
         [("92", "Total Akun", "Semua peran resmi", PRIMARY_SOFT, PRIMARY_DARK, "users"), ("89", "Akun Aktif", "Hash Scrypt aman", OK_BG, OK_TXT, "shield"), ("3", "Nonaktif", "Diarsipkan", SUBTLE_BG, MUTED, "lock")],
         "Daftar Akun Pengguna Sistem",
         ["ID", "Username", "Peran (Role)", "Nama Lengkap", "Status", "Aksi"],
         [["1", "admin", "Admin Pengelola", "Desi Pengelola", "Aktif", "Reset Sandi"],
          ["2", "owner", "Pemilik (Read-Only)", "Pemilik Lembaga", "Aktif", "Reset Sandi"],
          ["3", "mentor1", "Mentor", "Sarah Amelia", "Aktif", "Reset Sandi"],
          ["4", "parent1", "Wali Murid", "Ibu Ratna Sari", "Aktif", "Reset Sandi"]]),

        ("admin/reports.html", "Laporan & Ekspor", "Laporan & Ekspor Data Operasional", "Rekap multi-dimensi jadwal, kehadiran, perkembangan & ekspor CSV aman", "Ekspor Data ke CSV", "Cetak Laporan", "download", "printer",
         [("148", "Total Sesi", "Periode terpilih", PRIMARY_SOFT, PRIMARY_DARK, "calendar"), ("94%", "Rasio Kehadiran", "Hadir tepat waktu", OK_BG, OK_TXT, "check"), ("CSV", "Format Ekspor", "Bebas hash/token", SECONDARY_SOFT, SECONDARY_DARK, "report")],
         "Pratinjau Laporan Operasional Siap Ekspor",
         ["ID", "Tanggal & Jam", "Siswa & Program", "Mentor", "Status Jadwal", "Kehadiran"],
         [["S-401", "25 Nov 15:30", "Naufal, Matematika", "Kak Sarah", "Disetujui", "Hadir"],
          ["S-402", "25 Nov 16:00", "Alisha, Calistung", "Kak Dian", "Disetujui", "Hadir"],
          ["S-403", "24 Nov 17:00", "Kevin, Fisika SMA", "Kak Budi", "Disetujui", "Hadir"]]),

        ("admin/audit_logs.html", "Audit Log", "Riwayat Audit Log Aktivitas", "Catatan append-only seluruh perubahan penting operasional & database", None, None, "history", None,
         [("1.420", "Total Catatan", "Append-only aman", PRIMARY_SOFT, PRIMARY_DARK, "history"), ("38", "Aktivitas Hari Ini", "Tercatat otomatis", SECONDARY_SOFT, SECONDARY_DARK, "trending-up"), ("100%", "Integritas Log", "Tidak dapat diubah", OK_BG, OK_TXT, "shield")],
         "Jejak Aktivitas Sistem (Audit Log)",
         ["Waktu & Tanggal", "Pengguna", "Jenis Tindakan", "Entitas", "Rincian Aktivitas"],
         [["26 Nov 21:15", "admin", "SETUJUI_JADWAL", "Jadwal #412", "Menyetujui jadwal rutin Naufal"],
          ["26 Nov 19:40", "mentor1", "SIMPAN_LAPORAN", "Siswa #101", "Mempublikasikan laporan Persamaan Linear"],
          ["26 Nov 08:00", "admin", "BACKUP_DB", "desi_privat.db", "Membuat cadangan database valid"]]),

        ("admin/backups.html", "Backup & Restore", "Pencadangan & Pemulihan Database", "Snapshot atomic SQLite dengan validasi PRAGMA quick_check & pre-restore snapshot", "Cadangkan Database Sekarang", None, "backup", None,
         [("12", "Berkas Snapshot", "Tersimpan di backups/", PRIMARY_SOFT, PRIMARY_DARK, "backup"), ("Valid", "Status Integritas", "PRAGMA quick_check OK", OK_BG, OK_TXT, "check"), ("Aman", "Proteksi Restore", "Wajib ketik PULIHKAN", SECONDARY_SOFT, SECONDARY_DARK, "shield")],
         "Riwayat Berkas Cadangan Database (.db)",
         ["ID", "Nama Berkas Backup", "Ukuran", "Waktu Pembuatan", "Dibuat Oleh", "Status"],
         [["B-12", "desi_privat_backup_20261126_0800.db", "480 KB", "26 Nov 2026 08:00", "admin", "Valid"],
          ["B-11", "desi_privat_backup_20261125_2000.db", "478 KB", "25 Nov 2026 20:00", "admin", "Valid"],
          ["B-10", "desi_privat_backup_20261124_0800.db", "472 KB", "24 Nov 2026 08:00", "admin", "Valid"]]),
    ]

    frames = {}
    nav_maps = {}
    ctas = {}
    secs = {}
    row0s = {}
    for idx, (fname, anav, ptitle, psub, pcta, scta, pic, sic, kpis, ttitle, cols, rows) in enumerate(specs):
        col = idx % 4
        row = idx // 4
        f, cy, navs, cta_b, sec_b = draw_app_shell(
            b, fname, col * 1540, row * 1060, "admin", anav, ptitle, psub, pcta, scta,
            primary_icon=pic, secondary_icon=sic
        )
        cy = draw_kpi_strip(b, f, cy, kpis)
        row0 = draw_table_card(b, f, cy, ttitle, cols, rows)
        frames[fname] = f
        nav_maps[fname] = navs
        ctas[fname] = cta_b
        secs[fname] = sec_b
        row0s[fname] = row0

    # 8th frame: admin/receipt_print.html
    fp = b.frame("admin/receipt_print.html: Cetak Kuitansi", 3 * 1540, 1060, 1440, 960, fill=ALABASTER, stroke=HAIRLINE)
    b.rect(fp, 0, 0, 1440, 72, fill=SURFACE, radius=0, stroke=HAIRLINE)
    draw_brand_mark(b, fp, 48, 18, size=36, light=False)
    b.text(fp, "Pratinjau Cetak Kuitansi Resmi", 96, 23, size=18, color=INK, weight="Bold", family=FONT_HEAD, width=420, max_lines=1)
    close_rcp = b.pill(fp, 1044, 17, 136, 38, "Tutup", SURFACE, BODY, size=13, weight="SemiBold", stroke=HAIRLINE, icon_name="arrow-left", elevate=True)
    print_rcp = b.pill(fp, 1196, 17, 198, 38, "Cetak / Simpan PDF", SECONDARY, SURFACE, size=13, weight="Bold", icon_name="printer", elevate=True)

    rcp = b.rect(fp, 340, 116, 760, 768, fill=SURFACE, radius=18, stroke=HAIRLINE, name="Printable Receipt Card")
    b.shadow(rcp, blur=28, y=8, opacity=0.06)
    draw_brand_mark(b, fp, 396, 162, size=42, light=False)
    b.text(fp, "DESI PRIVAT", 450, 162, size=20, color=PRIMARY, weight="Bold", family=FONT_HEAD, width=220, max_lines=1)
    b.text(fp, "KUITANSI PEMBAYARAN RESMI", 450, 190, size=12, color=MUTED, weight="Bold", width=260, max_lines=1)
    b.text(fp, "LUNAS", 910, 174, size=13, color=OK_TXT, weight="Bold", width=134, align="right")
    b.rect(fp, 396, 238, 648, 2, fill=HAIRLINE, radius=1)
    b.text(fp, "No. Kuitansi: KW-2611-019\nTanggal Bayar: 25 November 2026\nDiterima Dari: Ibu Ratna Sari (Wali dari Naufal Pratama)", 396, 266, size=14.5, color=INK, line_h=26)
    b.rect(fp, 396, 376, 648, 42, fill=SUBTLE_BG, radius=8)
    b.text(fp, "DESKRIPSI PEMBAYARAN", 416, 389, size=11, color=MUTED, weight="Bold")
    b.text(fp, "PERIODE", 720, 389, size=11, color=MUTED, weight="Bold")
    b.text(fp, "JUMLAH", 930, 389, size=11, color=MUTED, weight="Bold")
    b.rect(fp, 396, 430, 648, 68, fill=SURFACE, radius=8, stroke=HAIRLINE)
    b.text(fp, "Paket Bimbingan Matematika SMP (8 Sesi)", 416, 454, size=14, color=INK, weight="SemiBold")
    b.text(fp, "Periode #3", 720, 454, size=14, color=BODY)
    b.text(fp, "Rp 800.000", 920, 454, size=14, color=INK, weight="Bold")
    b.rect(fp, 396, 530, 648, 74, fill=PRIMARY_SOFT, radius=12, stroke=PRIMARY_BORDER)
    b.icon(fp, "receipt", 418, 557, size=20, color=PRIMARY_DARK)
    b.text(fp, "Total Pembayaran Diterima", 448, 556, size=15, color=PRIMARY_DARK, weight="Bold")
    b.text(fp, "Rp 800.000", 880, 552, size=20, color=PRIMARY_DARK, weight="Bold", family=FONT_HEAD)
    b.text(fp, "Metode: Transfer BCA, Dicatat oleh Admin Pengelola DESI PRIVAT", 396, 650, size=13, color=MUTED)
    frames["admin/receipt_print.html"] = fp

    b.flow(frames["admin/bills.html"], "Admin Keuangan & Sistem Flow")

    # Page 03 Post-Click Interactive Layers (y=2160)
    ov_bill, ov_bill_sub = draw_modal_layer(
        b, "Overlay: Modal Buat Tagihan Baru", 0, 2160,
        "Buat Tagihan / Input Cicilan",
        "Pembuatan tagihan SPP periode 8 sesi dan pencatatan cicilan",
        [("Siswa & Program", "Kevin Ardiansyah, Fisika SMA"),
         ("Nominal Tagihan / Cicilan", "Rp 1.000.000 (Metode: Transfer BCA)")],
        "Simpan Tagihan", accent=SECONDARY, w=480
    )
    ov_wa, ov_wa_sub = draw_modal_layer(
        b, "Overlay: Modal Kirim Tagihan WA", 520, 2160,
        "Kirim Penagihan via WhatsApp",
        "Pratinjau pesan pengingat tagihan resmi ke nomor WhatsApp wali murid",
        [("Penerima", "Bapak Hendra Wijaya (0811-7722-9012)"),
         ("Ringkasan Pesan", "Tagihan Fisika SMA Periode #3 sebesar Rp 1.000.000")],
        "Kirim Pengingat WA", accent=OK_TXT, w=480
    )
    ov_acc, ov_acc_sub = draw_modal_layer(
        b, "Overlay: Modal Buat Akun Baru", 1040, 2160,
        "Buat Akun Pengguna Baru",
        "Hash kata sandi Scrypt aman sesuai RBAC DESI PRIVAT",
        [("Username & Peran", "mentor_baru, Role: Mentor"),
         ("Nama Lengkap & Sandi Awal", "Kak Raka Pratama, Sandi sementara")],
        "Buat Akun Aman", accent=PRIMARY, w=480
    )
    ov_exp, ov_exp_sub = draw_modal_layer(
        b, "Overlay: Modal Ekspor & Cetak", 1560, 2160,
        "Ekspor Laporan / Cetak PDF",
        "Output bersih bebas hash/token sensitif",
        [("Format Berkas", "CSV Operasional / Kuitansi PDF Resmi"),
         ("Cakupan Periode", "November 2026 (Semua program aktif)")],
        "Unduh Berkas", accent=PRIMARY, w=480
    )
    ov_bkp, ov_bkp_sub = draw_modal_layer(
        b, "Overlay: Modal Backup & Restore DB", 2080, 2160,
        "Cadangkan & Validasi Database",
        "Snapshot SQLite atomic dengan validasi PRAGMA quick_check",
        [("Nama Snapshot Baru", "desi_privat_backup_20261127.db"),
         ("Proteksi Restore", "Ketik PULIHKAN sebelum menimpa database")],
        "Buat Cadangan Sekarang", accent=SECONDARY, w=480
    )
    ov_fin_toast = draw_toast_layer(
        b, "Overlay: Toast Keuangan & Sistem", 2600, 2160,
        "Tindakan Berhasil",
        "Transaksi, tagihan, atau berkas ekspor telah diproses.",
        accent=OK_TXT
    )

    if ctas.get("admin/bills.html"):
        b.overlay_link(ctas["admin/bills.html"], ov_bill, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    if secs.get("admin/bills.html"):
        b.overlay_link(secs["admin/bills.html"], ov_wa, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    if ctas.get("admin/accounts.html"):
        b.overlay_link(ctas["admin/accounts.html"], ov_acc, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    if ctas.get("admin/reports.html"):
        b.overlay_link(ctas["admin/reports.html"], ov_exp, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    if secs.get("admin/reports.html"):
        b.overlay_link(secs["admin/reports.html"], ov_exp, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    if ctas.get("admin/backups.html"):
        b.overlay_link(ctas["admin/backups.html"], ov_bkp, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    b.overlay_link(print_rcp, ov_exp, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    for sub in [ov_bill_sub, ov_wa_sub, ov_acc_sub, ov_exp_sub, ov_bkp_sub]:
        b.swap_overlay_link(sub, ov_fin_toast)

    if row0s.get("admin/payments.html"):
        b.link(row0s["admin/payments.html"], frames["admin/receipt_print.html"], trans="moveIn", direction="bottom", duration=320, easing="easeOut")
    if secs.get("admin/payments.html"):
        b.link(secs["admin/payments.html"], frames["admin/bills.html"], trans="slideIn", direction="right", duration=256, easing="easeOut")
    b.link(close_rcp, frames["admin/payments.html"], trans="moveOut", direction="bottom", duration=256, easing="easeOut")
    fin_targets = {
        "Tagihan & Cicilan": "admin/bills.html",
        "Riwayat Pembayaran": "admin/payments.html",
        "Honor Mentor": "admin/mentor_honor.html",
        "Manajemen Akun": "admin/accounts.html",
        "Laporan & Ekspor": "admin/reports.html",
        "Audit Log": "admin/audit_logs.html",
        "Backup & Restore": "admin/backups.html",
    }
    for src_name, n_dict in nav_maps.items():
        if "__bell__" in n_dict:
            b.overlay_link(n_dict["__bell__"], ov_fin_toast, trans="dissolve", duration=180, easing="easeOut")
        for lbl, dst_name in fin_targets.items():
            if dst_name != src_name and lbl in n_dict:
                b.link(n_dict[lbl], frames[dst_name], trans="push", direction="left", duration=280, easing="easeInOut")


# ==============================================================================
# PAGE 5: OWNER EKSEKUTIF (16) + ASYMMETRIC EXECUTIVE DASHBOARD
# ==============================================================================
def build_page_04_owner(b: FigBuilder):
    b.page_add("04 - Owner Eksekutif (16)")
    b.page_bg("#EAEAE6")

    # 1. owner/dashboard.html — Asymmetric Executive Read-Only Overview
    fo, cy, nav_o, _, _ = draw_app_shell(
        b, "owner/dashboard.html", 0, 0, "owner", "Dashboard Eksekutif",
        "Dashboard Pengawasan Eksekutif (Pemilik)",
        "Ringkasan kas, honor mentor, kesehatan lembaga & supervisi read-only",
        None, None, readonly_badge=True
    )
    # Owner Uniform Analytics Sheet (Zero 3D, Zero Dark Card)
    ows = b.rect(fo, 284, cy, 1120, 212, fill=SURFACE, radius=12, stroke=HAIRLINE, name="Owner Analytics Sheet")
    b.shadow(ows, blur=8, y=2, opacity=0.03)
    own_cash_btn = b.pill(fo, 308, cy + 18, 164, 32, "Buku Kas", PRIMARY, SURFACE, size=12, weight="Bold")
    own_rep_btn = b.pill(fo, 484, cy + 18, 152, 32, "Laporan", ALABASTER, INK, size=12, weight="SemiBold", stroke=HAIRLINE)
    b.text(fo, "Sesi Tervalidasi Lembaga", 308, cy + 60, size=11.5, color=MUTED, weight="Bold", width=240, max_lines=1)
    b.text(fo, "136", 308, cy + 78, size=34, color=INK, weight="Bold", family=FONT_HEAD, width=110, max_lines=1)
    b.text(fo, "84 siswa aktif, 3 honor siap kirim", 396, cy + 92, size=11.5, color=MUTED, weight="SemiBold", width=320, max_lines=1)

    for oi, (olbl, oval) in enumerate([
        ("Omzet Periode", "Rp 24,5 Jt"),
        ("Honor Siap Kirim", "Rp 11,8 Jt (3 Mentor)"),
        ("Kehadiran Tatap Muka", "98%"),
    ]):
        ox = 308 + oi * 364
        b.rect(fo, ox, cy + 124, 344, 72, fill=SURFACE, radius=12, stroke=HAIRLINE)
        b.text(fo, olbl, ox + 16, cy + 136, size=11.5, color=MUTED, weight="SemiBold", width=312, max_lines=1)
        b.text(fo, oval, ox + 16, cy + 156, size=20, color=INK, weight="Bold", family=FONT_HEAD, width=312, max_lines=1)
    cy += 232
    draw_table_card(
        b, fo, cy,
        "Honor Tentor Siap Diberikan & Jadwal Terkini",
        ["Nama Tentor", "Siswa & Program", "Selesai Periode", "Fee / Sesi", "Total Gaji"],
        [
            ["Kak Sarah", "Naufal, Matematika", "8 / 8 Sesi", "Rp 100.000", "Rp 800.000"],
            ["Kak Dian", "Alisha, Calistung", "8 / 8 Sesi", "Rp 90.000", "Rp 720.000"],
            ["Kak Budi", "Kevin, Fisika SMA", "8 / 8 Sesi", "Rp 110.000", "Rp 880.000"],
            ["Kak Raka", "Dimas, SNBT", "8 / 8 Sesi", "Rp 120.000", "Rp 960.000"],
        ],
        x=284, w=724, h=504
    )
    # Right Health & Audit Rail
    hrail = b.rect(fo, 1028, cy, 376, 504, fill=SURFACE, radius=16, stroke=HAIRLINE, name="Owner Health Rail")
    b.shadow(hrail, blur=18, y=4, opacity=0.035)
    b.text(fo, "Kesehatan Lembaga", 1052, cy + 20, size=15.5, color=INK, weight="Bold", family=FONT_HEAD, width=328, max_lines=1)
    bars = [
        ("Kolektibilitas SPP", "78%", 0.78, PRIMARY),
        ("Kehadiran Tatap Muka", "98%", 0.98, OK_TXT),
        ("Retensi Siswa Aktif", "94%", 0.94, SECONDARY),
    ]
    for bi, (blbl, bval, bratio, bcol) in enumerate(bars):
        by = cy + 62 + bi * 74
        b.rect(fo, 1052, by, 328, 60, fill=ALABASTER, radius=11, stroke=HAIRLINE)
        b.text(fo, blbl, 1068, by + 12, size=12.5, color=INK, weight="SemiBold", width=220, max_lines=1)
        b.text(fo, bval, 1300, by + 12, size=13, color=bcol, weight="Bold", width=64, align="right", max_lines=1)
        b.rect(fo, 1068, by + 38, 296, 8, fill=HAIRLINE, radius=4)
        b.rect(fo, 1068, by + 38, round(296 * bratio), 8, fill=bcol, radius=4)

    b.rect(fo, 1052, cy + 296, 328, 92, fill=SECONDARY_SOFT, radius=12, stroke=SECONDARY_BORDER)
    b.text(fo, "Akses Supervisi Read-Only", 1070, cy + 312, size=13, color=SECONDARY_DARK, weight="Bold", width=292, max_lines=1)
    b.text(fo, "Seluruh transaksi, audit log & pergantian mentor hanya untuk dipantau.", 1070, cy + 334, size=12, color=BODY, width=292, line_h=18)

    owner_specs = [
        ("owner/attendance.html", "Dashboard Absensi", "Dashboard Absensi & Siklus Pertemuan Siswa", "Monitoring progres siklus 8 pertemuan setiap siswa aktif", None,
         [("84", "Siswa Aktif", "Terpantau siklus", PRIMARY_SOFT, PRIMARY_DARK, "graduation"), ("136", "Sesi Terabsen", "Dengan foto bukti", OK_BG, OK_TXT, "camera"), ("4", "Mendekati Periode Baru", "Pertemuan ke-7/8", SECONDARY_SOFT, SECONDARY_DARK, "clock")],
         "Rekap Siklus Pertemuan Siswa",
         ["Nama Siswa", "Wali Murid", "Program & Posisi Siklus", "Status"],
         [["Naufal Pratama", "Ibu Ratna", "Matematika SMP, Pertemuan 6/8", "Aktif"],
          ["Alisha Putri", "Ibu Ratna", "Calistung SD, Pertemuan 8/8", "Siap Perpanjang"]]),

        ("owner/attendance_detail.html", "Dashboard Absensi", "Detail Riwayat Absensi: Naufal Pratama", "Verifikasi bukti foto sesi belajar tatap muka dan catatan mentor", "Kembali ke Dashboard Absensi",
         [("6 / 8", "Pertemuan Periode #3", "Matematika SMP", PRIMARY_SOFT, PRIMARY_DARK, "book"), ("100%", "Hadir Tepat Waktu", "0 Alpa", OK_BG, OK_TXT, "check"), ("6", "Foto Terdokumentasi", "Tersimpan aman", SECONDARY_SOFT, SECONDARY_DARK, "camera")],
         "Riwayat Sesi & Bukti Dokumentasi",
         ["Tanggal & Waktu", "Program Les", "Sesi & Periode", "Mentor", "Status Kehadiran"],
         [["25 Nov 15:30", "Matematika SMP", "Pertemuan 6/8", "Kak Sarah", "Hadir"],
          ["18 Nov 15:30", "Matematika SMP", "Pertemuan 5/8", "Kak Sarah", "Hadir"]]),

        ("owner/students.html", "Data Siswa", "Data Siswa Bimbingan (Pemilik)", "Pengawasan seluruh siswa terdaftar & validasi status pembayaran", None,
         [("84", "Siswa Aktif", "SD, SMP, SMA", PRIMARY_SOFT, PRIMARY_DARK, "graduation"), ("12", "Siswa Baru", "Bulan berjalan", SECONDARY_SOFT, SECONDARY_DARK, "sparkles"), ("84", "Tervalidasi", "Data lengkap", OK_BG, OK_TXT, "check")],
         "Daftar Siswa Bimbingan",
         ["Nama Siswa", "Asal Sekolah & Kelas", "Wali Murid", "Program Les", "Status"],
         [["Naufal Pratama", "SMPN 1, 8B", "Ibu Ratna", "Matematika SMP", "Aktif"],
          ["Kevin Ardiansyah", "SMAN 2, 11 IPA", "Bpk. Hendra", "Fisika SMA", "Aktif"]]),

        ("owner/mentors.html", "Data Mentor", "Data Mentor Pengajar (Pemilik)", "Pengawasan keahlian, tarif fee per sesi, dan beban mengajar mentor", None,
         [("18", "Mentor Aktif", "Semua jenjang", PRIMARY_SOFT, PRIMARY_DARK, "mentor"), ("12.2", "Rata-Rata Sesi/Mg", "Beban seimbang", SECONDARY_SOFT, SECONDARY_DARK, "clock"), ("0", "Keluhan Aktif", "Kualitas terjaga", OK_BG, OK_TXT, "check")],
         "Daftar Mentor & Tarif Fee",
         ["Nama Mentor", "Kontak", "Bidang Keahlian", "Beban Aktif", "Status"],
         [["Kak Sarah", "0812-3400-1122", "Matematika & Inggris", "14 Sesi/mg", "Aktif"],
          ["Kak Budi", "0813-5522-8899", "Fisika & Kimia", "10 Sesi/mg", "Aktif"]]),

        ("owner/parents.html", "Data Orang Tua", "Data Orang Tua & Wali Murid (Pemilik)", "Pengawasan daftar wali murid dan keterhubungan siswa", None,
         [("68", "Wali Murid", "Terhubung aktif", PRIMARY_SOFT, PRIMARY_DARK, "family"), ("14", "Keluarga Multi-Anak", ">= 2 siswa", SECONDARY_SOFT, SECONDARY_DARK, "users"), ("100%", "Kontak Valid", "Terhubung WA", OK_BG, OK_TXT, "phone")],
         "Daftar Orang Tua / Wali Murid",
         ["Nama Wali Murid", "No. Telepon / WA", "Anak Terhubung", "Domisili", "Status"],
         [["Ibu Ratna Sari", "0812-8800-4821", "Naufal, Alisha", "Jl. Merdeka No. 12", "Aktif"],
          ["Bapak Hendra", "0811-7722-9012", "Kevin Ardiansyah", "Jl. Kenanga No. 8", "Aktif"]]),

        ("owner/admins.html", "Data Admin", "Data Administrator Operasional (Pemilik)", "Daftar admin pengelola yang aktif mengoperasikan jadwal & data master", None,
         [("2", "Admin Aktif", "Operasional harian", PRIMARY_SOFT, PRIMARY_DARK, "shield"), ("0", "Akun Terkunci", "Aman", OK_BG, OK_TXT, "lock"), ("100%", "Audit Tercatat", "Terpantau", SECONDARY_SOFT, SECONDARY_DARK, "history")],
         "Daftar Administrator Operasional",
         ["Nama Lengkap", "Username", "Kontak", "Status Akun", "Terdaftar Sejak"],
         [["Desi Pengelola", "admin", "0812-1111-2222", "Aktif", "Jan 2025"],
          ["Rini Administrasi", "admin2", "0813-3333-4444", "Aktif", "Mar 2026"]]),

        ("owner/schedules.html", "Rekap Jadwal", "Rekap Jadwal & Kalender Sesi Les", "Supervisi seluruh jadwal mingguan, konfirmasi siswa & respon mentor", None,
         [("142", "Total Jadwal", "Minggu berjalan", PRIMARY_SOFT, PRIMARY_DARK, "calendar"), ("138", "Dikonfirmasi", "Siap jalan", OK_BG, OK_TXT, "calendar-check"), ("1", "Respon Terlambat", "> 24 jam", DANGER_BG, DANGER_TXT, "alert")],
         "Rekap Jadwal & Status Konfirmasi",
         ["Tanggal Sesi", "Waktu", "Siswa & Program", "Mentor", "Status Jadwal", "Respons Mentor"],
         [["26 Nov 2026", "15:30", "Naufal, Matematika", "Kak Sarah", "Disetujui", "Siap Mengajar"],
          ["26 Nov 2026", "17:00", "Kevin, Fisika SMA", "Kak Budi", "Perlu Pengganti", "Berhalangan"]]),

        ("owner/replacements.html", "Pergantian Mentor", "Riwayat Pergantian Mentor (Pemilik)", "Jejak permanen (immutable history) setiap pergantian mentor pengganti", None,
         [("4", "Total Pergantian", "Bulan November", SECONDARY_SOFT, SECONDARY_DARK, "mentor"), ("100%", "Alasan Tercatat", "Transparan", PRIMARY_SOFT, PRIMARY_DARK, "report"), ("0", "Sesi Terlewat", "Tertangani cepat", OK_BG, OK_TXT, "check")],
         "Riwayat Pergantian Mentor Pengganti",
         ["Waktu Pergantian", "Tanggal Sesi", "Siswa", "Mentor Awal", "Mentor Pengganti", "Alasan"],
         [["25 Nov 09:10", "26 Nov 17:00", "Kevin Ardiansyah", "Kak Budi", "Kak Raka", "Tugas luar kota"],
          ["12 Nov 14:20", "13 Nov 16:00", "Alisha Putri", "Kak Dian", "Kak Sarah", "Sakit"]]),

        ("owner/progress.html", "Perkembangan Siswa", "Supervisi Perkembangan Siswa (Pemilik)", "Pantau mutu pembelajaran dan laporan mentor terbaru ke wali murid", None,
         [("64", "Laporan Bulan Ini", "Terkirim ke wali", PRIMARY_SOFT, PRIMARY_DARK, "report"), ("94%", "Capaian Materi", "Sesuai target silabus", OK_BG, OK_TXT, "trending-up"), ("100%", "Tertaut ke Wali", "Langsung terbaca", SECONDARY_SOFT, SECONDARY_DARK, "family")],
         "Rekap Laporan Perkembangan Terbaru",
         ["Tanggal", "Siswa & Program", "Mentor", "Materi Dipelajari", "Evaluasi"],
         [["25 Nov 2026", "Naufal, Matematika", "Kak Sarah", "Persamaan Linear", "Sangat Baik"],
          ["24 Nov 2026", "Alisha, Calistung", "Kak Dian", "Membaca Suku Kata", "Lancar"]]),

        ("owner/bills.html", "Tagihan & Tunggakan", "Pengawasan Tagihan, Cicilan & Tunggakan Siswa", "Monitoring tagihan periode baru dan siswa yang memerlukan tindak lanjut pembayaran", None,
         [("Rp 24,5 Jt", "Tagihan Periode", "Total aktif", PRIMARY_SOFT, PRIMARY_DARK, "receipt"), ("Rp 5,3 Jt", "Sisa Tunggakan", "Perlu penagihan", DANGER_BG, DANGER_TXT, "alert"), ("Rp 19,2 Jt", "Kas Masuk", "Sudah terbayar", OK_BG, OK_TXT, "check")],
         "Daftar Tagihan & Tunggakan Siswa",
         ["Siswa & Program", "Wali Murid", "Tagihan Periode", "Sisa Tunggakan", "Status"],
         [["Kevin, Fisika SMA", "Bpk. Hendra", "Rp 1.000.000", "Rp 1.000.000", "Tunggakan"],
          ["Alisha, Calistung", "Ibu Ratna", "Rp 650.000", "Rp 325.000", "Cicilan"]]),

        ("owner/finance.html", "Keuangan & Honor", "Laporan Keuangan & Rekap Honor Mentor", "Ringkasan penerimaan kuitansi murid dan pengeluaran honor pengajar", None,
         [("Rp 19,2 Jt", "Pemasukan Kuitansi", "November 2026", OK_BG, OK_TXT, "credit-card"), ("Rp 11,8 Jt", "Honor Tentor", "Periode berjalan", SECONDARY_SOFT, SECONDARY_DARK, "wallet"), ("Rp 7,4 Jt", "Margin Bersih", "Estimasi sementara", PRIMARY_SOFT, PRIMARY_DARK, "trending-up")],
         "Rincian Transaksi & Honor Mentor",
         ["No. Kuitansi", "Tanggal", "Siswa & Program", "Metode", "Nominal"],
         [["KW-2611-019", "25 Nov 2026", "Naufal, Matematika", "Transfer BCA", "Rp 800.000"],
          ["KW-2611-018", "22 Nov 2026", "Alisha, Calistung", "QRIS", "Rp 325.000"]]),

        ("owner/finance_report.html", "Arus Kas Bimbel", "Laporan Keuangan & Arus Kas Bimbel", "Buku kas masuk/keluar operasional lembaga dengan ekspor Excel (.xlsx)", None,
         [("Rp 19,2 Jt", "Uang Masuk", "SPP & pendaftaran", OK_BG, OK_TXT, "trending-up"), ("Rp 12,4 Jt", "Uang Keluar", "Honor & operasional", SECONDARY_SOFT, SECONDARY_DARK, "wallet"), ("Rp 6,8 Jt", "Saldo Bersih", "Periode berjalan", PRIMARY_SOFT, PRIMARY_DARK, "receipt")],
         "Buku Kas Masuk & Keluar",
         ["Tanggal", "Jenis Kas", "Kategori", "Pihak Terkait", "Uang Masuk", "Uang Keluar"],
         [["25 Nov 2026", "Kas Masuk", "SPP Bulanan", "Ibu Ratna", "Rp 800.000", "-"],
          ["24 Nov 2026", "Kas Keluar", "Honor Mentor", "Kak Sarah", "-", "Rp 800.000"]]),

        ("owner/honor.html", "Honor Tentor", "Perhitungan Honor & Fee Mengajar Tentor", "Daftar mentor yang telah menyelesaikan siklus pertemuan & status transfer", None,
         [("3", "Siap Ditransfer", "Periode selesai", SECONDARY_SOFT, SECONDARY_DARK, "clock"), ("Rp 6,9 Jt", "Sudah Ditransfer", "Terbayar bulan ini", OK_BG, OK_TXT, "check"), ("100%", "Tarif Terverifikasi", "Sesuai jenjang", PRIMARY_SOFT, PRIMARY_DARK, "shield")],
         "Rekap Pencairan Honor Tentor",
         ["Nama Tentor", "Siswa & Program", "Siklus Periode", "Total Fee", "Status Transfer"],
         [["Kak Sarah", "Naufal, Matematika", "Periode #2 (8/8)", "Rp 800.000", "Sudah Ditransfer"],
          ["Kak Dian", "Alisha, Calistung", "Periode #3 (8/8)", "Rp 720.000", "Menunggu Transfer"]]),

        ("owner/reports.html", "Laporan Eksekutif", "Laporan & Rekapitulasi Eksekutif", "Ekspor rekap operasional ke CSV dan format cetak untuk rapat evaluasi", None,
         [("148", "Total Pertemuan", "November 2026", PRIMARY_SOFT, PRIMARY_DARK, "calendar"), ("94%", "Tingkat Hadir", "Tinggi", OK_BG, OK_TXT, "check"), ("CSV/PDF", "Siap Ekspor", "Sekali klik", SECONDARY_SOFT, SECONDARY_DARK, "download")],
         "Tabel Rekapitulasi Eksekutif",
         ["ID", "Tanggal", "Jam", "Siswa", "Mentor", "Program", "Status"],
         [["R-01", "25 Nov", "15:30", "Naufal Pratama", "Kak Sarah", "Matematika", "Hadir"],
          ["R-02", "25 Nov", "16:00", "Alisha Putri", "Kak Dian", "Calistung", "Hadir"]]),

        ("owner/audit_logs.html", "Audit Log", "Supervisi Riwayat Aktivitas Sistem", "Pengawasan transparansi seluruh aksi admin dan mentor", None,
         [("1.420", "Catatan Audit", "Immutable log", PRIMARY_SOFT, PRIMARY_DARK, "history"), ("2", "Admin Aktif", "Terpantau", SECONDARY_SOFT, SECONDARY_DARK, "users"), ("Aman", "Status Keamanan", "Tidak ada anomali", OK_BG, OK_TXT, "shield")],
         "Log Pengawasan Aktivitas Sistem",
         ["Waktu", "Pengguna", "Jenis Aksi", "Entitas", "Rincian Aktivitas"],
         [["26 Nov 21:15", "admin", "SETUJUI_JADWAL", "Jadwal #412", "Menyetujui jadwal Naufal"],
          ["26 Nov 19:40", "mentor1", "ABSENSI_SESI", "Sesi #882", "Upload foto & catatan belajar"]]),
    ]

    frames_o = {"owner/dashboard.html": fo}
    navs_o = {"owner/dashboard.html": nav_o}
    secs_o = {}
    row0s_o = {}
    for idx, (fname, anav, ptitle, psub, scta, kpis, ttitle, cols, rows) in enumerate(owner_specs, start=1):
        col = idx % 4
        row = idx // 4
        f, cy, navs, _, sec_b = draw_app_shell(
            b, fname, col * 1540, row * 1060, "owner", anav, ptitle, psub, None, scta,
            readonly_badge=True, secondary_icon="arrow-left" if scta else None
        )
        cy = draw_kpi_strip(b, f, cy, kpis)
        row0 = draw_table_card(b, f, cy, ttitle, cols, rows)
        frames_o[fname] = f
        navs_o[fname] = navs
        secs_o[fname] = sec_b
        row0s_o[fname] = row0

    b.flow(fo, "Owner Eksekutif Flow")

    # Page 04 Post-Click Interactive Layers (y=4280)
    ov_own_photo = b.frame("Overlay: Modal Bukti Foto Sesi (Read-Only)", 0, 4280, 520, 440, fill=SURFACE, stroke=HAIRLINE)
    b.shadow(ov_own_photo, blur=28, y=10, opacity=0.14)
    b.text(ov_own_photo, "Bukti Foto Sesi: Naufal Pratama", 24, 22, size=16.5, color=INK, weight="Bold", family=FONT_HEAD, width=410, max_lines=1)
    ov_own_x = b.pill(ov_own_photo, 460, 18, 34, 34, "×", ALABASTER, INK, size=15, weight="Bold", stroke=HAIRLINE)
    b.close_overlay_link(ov_own_x)
    b.image(ov_own_photo, "galeri_05.webp", 24, 70, 472, 260, mode="fill", name="Owner Verified Session Photo")
    b.text(ov_own_photo, "25 Nov, 15:30 WIB, Kak Sarah, Materi Persamaan Linear", 24, 344, size=12.5, color=BODY, width=472, max_lines=1)
    ov_own_close = b.pill(ov_own_photo, 24, 382, 160, 38, "Tutup Pratinjau", ALABASTER, INK, size=12.5, weight="SemiBold", stroke=HAIRLINE)
    b.close_overlay_link(ov_own_close)

    ov_own_ro, _ = draw_popover_layer(
        b, "Overlay: Popover Info Mode Baca Saja", 560, 4280,
        "Supervisi Read-Only Pemilik",
        [("Hak Akses Terlindung", "Data hanya dibaca; perubahan dilakukan oleh Admin", PRIMARY),
         ("3 Honor Siap Transfer", "Periode 8 pertemuan selesai & siap dicairkan", SECONDARY)],
        footer_lbl=None
    )
    ov_own_logout, ov_own_logout_sub = draw_modal_layer(
        b, "Overlay: Modal Konfirmasi Keluar Pemilik", 960, 4280,
        "Keluar dari Sesi Pemilik?",
        "Akhiri sesi supervisi eksekutif dengan aman",
        [("Akun Aktif", "Pemilik Lembaga (owner)")],
        "Keluar Sekarang", accent=INK, w=440, cancel_lbl="Tetap Memantau"
    )
    b.close_overlay_link(ov_own_logout_sub)

    b.link(own_cash_btn, frames_o["owner/finance_report.html"], trans="push", direction="left", duration=280, easing="easeInOut")
    b.link(own_rep_btn, frames_o["owner/reports.html"], trans="push", direction="left", duration=280, easing="easeInOut")
    if row0s_o.get("owner/attendance.html"):
        b.link(row0s_o["owner/attendance.html"], frames_o["owner/attendance_detail.html"], trans="moveIn", direction="left", duration=320, easing="easeOut")
    if row0s_o.get("owner/attendance_detail.html"):
        b.overlay_link(row0s_o["owner/attendance_detail.html"], ov_own_photo, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    if secs_o.get("owner/attendance_detail.html"):
        b.link(secs_o["owner/attendance_detail.html"], frames_o["owner/attendance.html"], trans="slideIn", direction="right", duration=256, easing="easeOut")
    o_targets = {
        "Dashboard Eksekutif": "owner/dashboard.html",
        "Dashboard Absensi": "owner/attendance.html",
        "Data Siswa": "owner/students.html",
        "Data Mentor": "owner/mentors.html",
        "Data Orang Tua": "owner/parents.html",
        "Data Admin": "owner/admins.html",
        "Rekap Jadwal": "owner/schedules.html",
        "Pergantian Mentor": "owner/replacements.html",
        "Perkembangan Siswa": "owner/progress.html",
        "Tagihan & Tunggakan": "owner/bills.html",
        "Keuangan & Honor": "owner/finance.html",
        "Arus Kas Bimbel": "owner/finance_report.html",
        "Honor Tentor": "owner/honor.html",
        "Laporan Eksekutif": "owner/reports.html",
        "Audit Log": "owner/audit_logs.html",
    }
    for src_name, n_dict in navs_o.items():
        if "__bell__" in n_dict:
            b.overlay_link(n_dict["__bell__"], ov_own_ro, trans="dissolve", duration=180, easing="easeOut", dim="#11182722")
        if "__logout__" in n_dict:
            b.overlay_link(n_dict["__logout__"], ov_own_logout, trans="moveIn", direction="bottom", duration=220, easing="easeOut")
        for lbl, dst_name in o_targets.items():
            if dst_name != src_name and lbl in n_dict:
                b.link(n_dict[lbl], frames_o[dst_name], trans="push", direction="left", duration=280, easing="easeInOut")


# ==============================================================================
# PAGE 6: MENTOR PORTAL (6) + ASYMMETRIC MENTOR WORKSPACE
# ==============================================================================
def build_page_05_mentor(b: FigBuilder):
    b.page_add("05 - Mentor Portal (6)")
    b.page_bg("#EAEAE6")

    f1, cy, nav1, cta1, _ = draw_app_shell(
        b, "mentor/dashboard.html", 0, 0, "mentor", "Beranda Mentor",
        "Beranda Mentor Pengajar",
        "Halo Kak Sarah, lihat jadwal mengajar hari ini dan aksi cepat absensi",
        "Catat Absensi & Materi", None, primary_icon="camera"
    )
    # Mentor Bento Hero (Tanpa 3D)
    mws = b.rect(f1, 284, cy, 1120, 152, fill=SURFACE, radius=12, stroke=HAIRLINE, name="Mentor Workspace")
    b.shadow(mws, blur=8, y=2, opacity=0.03)
    b.text(f1, "Portal Pengajaran DESI PRIVAT", 308, cy + 18, size=11.5, color=MUTED, weight="Bold", width=320, max_lines=1)
    b.text(f1, "Selamat Bertugas, Mentor.", 308, cy + 38, size=22, color=INK, weight="Bold", family=FONT_HEAD, width=480, max_lines=1)
    b.text(f1, "Jadwal tersusun rapi. Setiap 8 kehadiran valid otomatis terhitung 1 periode belajar.", 308, cy + 68, size=12.5, color=BODY, width=680, max_lines=1)
    m_sch_btn = b.pill(f1, 308, cy + 100, 166, 32, "Jadwal Mengajar", ALABASTER, INK, size=11.5, weight="SemiBold", stroke=HAIRLINE)
    m_avl_btn = b.pill(f1, 486, cy + 100, 174, 32, "Ketersediaan Waktu", ALABASTER, INK, size=11.5, weight="SemiBold", stroke=HAIRLINE)
    cy += 168

    cy = draw_kpi_strip(b, f1, cy, [
        ("3", "Sesi Hari Ini", "15:30 - 20:00 WIB", PRIMARY_SOFT, PRIMARY_DARK, "calendar"),
        ("6", "Siswa Bimbingan", "Aktif minggu ini", SECONDARY_SOFT, SECONDARY_DARK, "graduation"),
        ("1", "Perlu Konfirmasi", "Jadwal minggu depan", DANGER_BG, DANGER_TXT, "bell"),
    ])
    draw_table_card(
        b, f1, cy, "Agenda Mengajar Hari Ini",
        ["Waktu", "Siswa & Program", "Fokus Materi", "Status", "Aksi"],
        [
            ["15:30 - 17:00", "Naufal, Matematika", "Persamaan Linear", "Siap Mengajar", "Catat Absen"],
            ["18:30 - 20:00", "Rania, Bahasa Inggris", "Speaking Daily", "Menunggu", "Konfirmasi"],
            ["20:00 - 21:00", "Alisha, Calistung", "Membaca Suku Kata", "Siap Mengajar", "Catat Absen"],
        ],
        x=284, w=724, h=504
    )
    mrail = b.rect(f1, 1028, cy, 376, 504, fill=SURFACE, radius=16, stroke=HAIRLINE, name="Mentor Quick Rail")
    b.shadow(mrail, blur=16, y=4, opacity=0.03)
    b.text(f1, "Aksi Cepat", 1052, cy + 20, size=15.5, color=INK, weight="Bold", family=FONT_HEAD, width=328, max_lines=1)
    m_actions = [
        ("Unggah Foto Absensi", "Dokumentasi sesi tatap muka", PRIMARY),
        ("Tulis Laporan Belajar", "Tampil di portal orang tua", SECONDARY),
        ("Atur Ketersediaan", "Perbarui slot waktu luang", OK_TXT),
    ]
    m_action_hits = []
    for mi, (mt, ms, mcol) in enumerate(m_actions):
        my = cy + 60 + mi * 78
        m_hit = b.rect(f1, 1044, my, 344, 62, fill=SURFACE, radius=10, name=f"Mentor Quick {mt}")
        m_action_hits.append(m_hit)
        b.ellipse(f1, 1056, my + 22, 8, 8, fill=mcol)
        b.text(f1, mt, 1076, my + 12, size=13.5, color=INK, weight="Bold", width=260, max_lines=1)
        b.text(f1, ms, 1076, my + 32, size=12, color=MUTED, width=260, max_lines=1)
        if mi < len(m_actions) - 1:
            b.rect(f1, 1052, my + 66, 328, 1, fill=HAIRLINE, radius=0)

    f2, cy, nav2, cta2, _ = draw_app_shell(b, "mentor/schedules.html", 1540, 0, "mentor", "Jadwal Mengajar", "Jadwal Mengajar Mentor", "Konfirmasi kesediaan mengajar (wajib sertakan alasan jika berhalangan)", "Ajukan Usulan Jadwal", primary_icon="calendar")
    cy = draw_kpi_strip(b, f2, cy, [("14", "Sesi Minggu Ini", "Terkonfirmasi 13", PRIMARY_SOFT, PRIMARY_DARK, "calendar"), ("1", "Menunggu Respon", "Batas 24 jam", SECONDARY_SOFT, SECONDARY_DARK, "clock"), ("0", "Bentrok Jadwal", "Aman", OK_BG, OK_TXT, "calendar-check")])
    draw_table_card(b, f2, cy, "Daftar Jadwal Mengajar", ["Hari & Jam", "Siswa Bimbingan", "Program", "Wali Murid", "Status"],
                    [["Senin 15:30", "Naufal Pratama", "Matematika SMP", "Ibu Ratna", "Siap Mengajar"],
                     ["Kamis 18:30", "Rania Azzahra", "Bahasa Inggris", "Ibu Sinta", "Menunggu"]])

    f3, cy, nav3, cta3, _ = draw_app_shell(b, "mentor/availability.html", 3080, 0, "mentor", "Ketersediaan Waktu", "Pengaturan Ketersediaan Waktu Mengajar", "Atur hari dan rentang jam luang agar penjadwalan admin bebas bentrok", "Simpan Ketersediaan", primary_icon="check")
    draw_table_card(b, f3, cy + 8, "Slot Waktu Mengajar Tersedia", ["Hari", "Rentang Jam", "Catatan Ketersediaan", "Status"],
                    [["Senin", "15:00 - 20:00 WIB", "Area pusat kota & sekitarnya", "Tersedia"],
                     ["Rabu", "15:00 - 20:00 WIB", "Khusus tatap muka SMP/SMA", "Tersedia"],
                     ["Sabtu", "09:00 - 15:00 WIB", "Fleksibel pagi hingga siang", "Tersedia"]])

    f4, cy, nav4, _, _ = draw_app_shell(b, "mentor/students.html", 0, 1060, "mentor", "Siswa Bimbingan", "Daftar Siswa Bimbingan Anda", "Pantau siklus pertemuan dan catatan kebutuhan belajar tiap siswa")
    cy = draw_kpi_strip(b, f4, cy, [("6", "Siswa Aktif", "Diampu saat ini", PRIMARY_SOFT, PRIMARY_DARK, "graduation"), ("95%", "Kehadiran Siswa", "Bulan berjalan", OK_BG, OK_TXT, "check")])
    draw_table_card(b, f4, cy, "Siswa Bimbingan Kak Sarah", ["Nama Siswa", "Sekolah & Jenjang", "Program Les", "Siklus Pertemuan", "Status"],
                    [["Naufal Pratama", "SMPN 1, Kelas 8", "Matematika SMP", "Pertemuan 6/8", "Aktif"],
                     ["Rania Azzahra", "SDN 2, Kelas 6", "Bahasa Inggris", "Pertemuan 4/8", "Aktif"]])

    f5, cy, nav5, cta5, _ = draw_app_shell(b, "mentor/attendance.html", 1540, 1060, "mentor", "Absensi & Foto Sesi", "Absensi Sesi & Dokumentasi Belajar", "Catat kehadiran dan unggah foto dokumentasi sesi belajar tatap muka", "Simpan Dokumentasi Absensi", primary_icon="camera")
    b.rect(f5, 284, cy, 540, 730, fill=SURFACE, radius=16, stroke=HAIRLINE)
    b.text(f5, "Formulir Absensi Sesi", 312, cy + 24, size=16, color=INK, weight="Bold", family=FONT_HEAD)
    for idx, (lbl, val) in enumerate([("Pilih Jadwal Terdaftar", "Naufal Pratama, Matematika, 15:30"), ("Status Kehadiran", "Hadir (Tepat Waktu)"), ("Materi yang Dibahas", "Persamaan Linear Dua Variabel")]):
        fy = cy + 70 + idx * 96
        b.text(f5, lbl, 312, fy, size=13, color=INK, weight="Bold")
        b.rect(f5, 312, fy + 26, 484, 46, fill=ALABASTER, radius=10, stroke=HAIRLINE)
        b.text(f5, val, 328, fy + 40, size=13.5, color=BODY, width=452, max_lines=1)
    b.text(f5, "Foto Dokumentasi Sesi (Wajib)", 312, cy + 362, size=13, color=INK, weight="Bold")
    att_drop = b.rect(f5, 312, cy + 390, 484, 168, fill=PRIMARY_SOFT, radius=14, stroke=PRIMARY_BORDER)
    b.icon_badge(f5, "camera", 530, cy + 422, box_size=48, icon_size=24, bg=SURFACE, fg=PRIMARY_DARK, radius=12)
    b.text(f5, "Klik atau pilih foto kegiatan belajar (.webp/.jpg)", 350, cy + 486, size=13.5, color=PRIMARY_DARK, weight="SemiBold", width=408, align="center")
    draw_table_card(b, f5, cy, "Riwayat Absensi Terakhir", ["Tanggal", "Siswa", "Pertemuan", "Status"],
                    [["25 Nov", "Naufal", "6/8", "Hadir"], ["18 Nov", "Naufal", "5/8", "Hadir"]], x=844, w=560, h=730)

    f6, cy, nav6, cta6, _ = draw_app_shell(b, "mentor/progress.html", 3080, 1060, "mentor", "Laporan Perkembangan", "Laporan Perkembangan Belajar Siswa", "Langsung tampil real-time di dashboard Orang Tua / Wali siswa terkait", "Simpan & Publikasikan Laporan", primary_icon="pencil")
    b.rect(f6, 284, cy, 1120, 720, fill=SURFACE, radius=16, stroke=HAIRLINE)
    b.text(f6, "Tulis Laporan Perkembangan Belajar (Terhubung Langsung ke Wali Murid)", 316, cy + 24, size=16.5, color=INK, weight="Bold", family=FONT_HEAD)
    fields = [
        ("Materi yang Dipelajari (Topics Covered)", "Persamaan Linear Dua Variabel & latihan soal cerita"),
        ("Kemampuan yang Telah Dikuasai (Skills Mastered)", "Siswa mampu mengubah soal cerita menjadi model matematika secara mandiri"),
        ("Kesulitan / Kendala Belajar (Difficulties)", "Perlu ketelitian tambahan saat substitusi bilangan negatif"),
        ("Rekomendasi Pertemuan Berikutnya (Recommendations)", "Latihan 5 soal variasi grafik dan pembahasan ulang pecahan"),
    ]
    for idx, (flbl, fval) in enumerate(fields):
        fy = cy + 74 + idx * 144
        b.text(f6, flbl, 316, fy, size=13.5, color=INK, weight="Bold")
        b.rect(f6, 316, fy + 28, 1056, 88, fill=ALABASTER, radius=10, stroke=HAIRLINE)
        b.text(f6, fval, 336, fy + 44, size=14, color=BODY, width=1016)

    b.flow(f1, "Mentor Portal Flow")

    # Page 05 Post-Click Interactive Layers (y=2160)
    ov_m_reject, ov_m_reject_sub = draw_modal_layer(
        b, "Overlay: Modal Alasan Berhalangan Mengajar", 0, 2160,
        "Ajukan Berhalangan / Usulan Jadwal",
        "Admin akan menerima notifikasi otomatis untuk menyiapkan mentor pengganti",
        [("Sesi Terkait", "Rania Azzahra, Kamis 18:30 WIB"),
         ("Alasan Berhalangan (Wajib)", "Jadwal ujian atau keperluan keluarga mendesak")],
        "Kirim Alasan ke Admin", accent=DANGER_TXT, w=480
    )
    ov_m_photo, ov_m_photo_sub = draw_modal_layer(
        b, "Overlay: Modal Unggah Foto Sesi", 520, 2160,
        "Unggah Foto Dokumentasi Sesi",
        "Foto dikirim ke Admin & Pemilik sebagai bukti sesi ke-7 dari 8",
        [("Berkas Foto Dipilih", "sesi_naufal_26nov.webp (Tervalidasi)"),
         ("Status Kendala (Jika Tertunda)", "Tidak ada kendala unggahan")],
        "Simpan Dokumentasi", accent=PRIMARY, w=480
    )
    ov_m_pub, ov_m_pub_sub = draw_modal_layer(
        b, "Overlay: Modal Konfirmasi Publikasi Rapor", 1040, 2160,
        "Publikasikan Laporan Belajar?",
        "Laporan langsung tampil pada portal Orang Tua / Wali siswa terkait",
        [("Siswa & Program", "Naufal Pratama, Matematika SMP"),
         ("Materi", "Persamaan Linear Dua Variabel")],
        "Publikasikan Sekarang", accent=SECONDARY, w=480
    )
    ov_m_toast = draw_toast_layer(
        b, "Overlay: Toast Tersimpan & Terkirim", 1560, 2160,
        "Tersimpan & Terkirim",
        "Absensi, foto sesi, atau laporan mentor telah diperbarui.",
        accent=OK_TXT
    )

    b.link(m_sch_btn, f2, trans="push", direction="left", duration=280, easing="easeInOut")
    b.link(m_avl_btn, f3, trans="push", direction="left", duration=280, easing="easeInOut")
    if cta1:
        b.link(cta1, f5, trans="moveIn", direction="left", duration=320, easing="easeOut")
    if cta2:
        b.overlay_link(cta2, ov_m_reject, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    if cta3:
        b.overlay_link(cta3, ov_m_toast, trans="dissolve", duration=200, easing="easeOut")
    if cta5:
        b.overlay_link(cta5, ov_m_photo, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    b.overlay_link(att_drop, ov_m_photo, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    if cta6:
        b.overlay_link(cta6, ov_m_pub, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    for sub in [ov_m_reject_sub, ov_m_photo_sub, ov_m_pub_sub]:
        b.swap_overlay_link(sub, ov_m_toast)

    b.link(m_action_hits[0], f5, trans="moveIn", direction="left", duration=320, easing="easeOut")
    b.link(m_action_hits[1], f6, trans="moveIn", direction="left", duration=320, easing="easeOut")
    b.link(m_action_hits[2], f3, trans="moveIn", direction="left", duration=320, easing="easeOut")
    m_map = {
        "Beranda Mentor": f1, "Jadwal Mengajar": f2, "Ketersediaan Waktu": f3,
        "Siswa Bimbingan": f4, "Absensi & Foto Sesi": f5, "Laporan Perkembangan": f6,
    }
    for src_f, n_dict in [(f1, nav1), (f2, nav2), (f3, nav3), (f4, nav4), (f5, nav5), (f6, nav6)]:
        if "__bell__" in n_dict:
            b.overlay_link(n_dict["__bell__"], ov_m_toast, trans="dissolve", duration=180, easing="easeOut")
        for lbl, dst_f in m_map.items():
            if dst_f != src_f and lbl in n_dict:
                b.link(n_dict[lbl], dst_f, trans="slideIn", direction="left", duration=280, easing="easeOut")


# ==============================================================================
# PAGE 7: PARENT & WALI PORTAL (6) + ASYMMETRIC CHILD PROGRESS RAIL
# ==============================================================================
def build_page_06_parent(b: FigBuilder):
    b.page_add("06 - Parent & Wali Portal (6)")
    b.page_bg("#EAEAE6")

    f1, cy, nav1, cta1, _ = draw_app_shell(b, "parent/dashboard.html", 0, 0, "parent", "Ringkasan Belajar", "Portal Belajar Ananda", "", "Tagihan")
    pws = b.rect(f1, 284, cy, 1120, 152, fill=SURFACE, radius=12, stroke=HAIRLINE, name="Parent Workspace")
    b.shadow(pws, blur=8, y=2, opacity=0.03)
    b.text(f1, "Portal Keluarga DESI PRIVAT", 308, cy + 18, size=11.5, color=MUTED, weight="Bold", width=320, max_lines=1)
    b.text(f1, "Portal Belajar Naufal Pratama.", 308, cy + 38, size=22, color=INK, weight="Bold", family=FONT_HEAD, width=580, max_lines=1)
    b.text(f1, "Pantau program les aktif, jadwal tatap muka, absensi, dan laporan mentor.", 308, cy + 68, size=12.5, color=BODY, width=700, max_lines=1)
    child1_pill = b.pill(f1, 308, cy + 98, 218, 38, "Naufal Pratama (8 SMP)", PRIMARY, SURFACE, size=12.5, weight="Bold", elevate=True)
    child2_pill = b.pill(f1, 540, cy + 98, 200, 38, "Alisha Putri (3 SD)", ALABASTER, BODY, size=12.5, weight="SemiBold", stroke=HAIRLINE)

    cy = draw_kpi_strip(b, f1, cy + 168, [
        ("6 / 8", "Sesi Periode #3", "", PRIMARY_SOFT, PRIMARY_DARK),
        ("100%", "Kehadiran Anak", "", OK_BG, OK_TXT),
        ("Lunas", "Status SPP", "", SECONDARY_SOFT, SECONDARY_DARK),
    ])
    draw_table_card(
        b, f1, cy, "Program Les & Jadwal Ananda",
        ["Program Les", "Mentor Pembimbing", "Hari & Jam", "Status"],
        [
            ["Matematika Terpadu SMP", "Kak Sarah Amelia", "Senin & Kamis, 15:30", "Aktif"],
            ["Bahasa Inggris SMP", "Kak Sarah Amelia", "Sabtu, 10:00", "Aktif"],
        ],
        x=284, w=724, h=516
    )
    prail = b.rect(f1, 1028, cy, 376, 516, fill=SURFACE, radius=16, stroke=HAIRLINE, name="Parent Latest Report")
    b.shadow(prail, blur=16, y=4, opacity=0.03)
    b.text(f1, "Laporan Terbaru Mentor", 1052, cy + 20, size=15.5, color=INK, weight="Bold", family=FONT_HEAD, width=328, max_lines=1)
    b.text(f1, "25 Nov, Kak Sarah", 1052, cy + 56, size=12, color=PRIMARY_DARK, weight="Bold", width=296, max_lines=1)
    b.text(f1, "Persamaan Linear Dua Variabel", 1052, cy + 80, size=14.5, color=INK, weight="Bold", width=328, max_lines=1)
    b.text(f1, "Mampu menyusun model matematika dari soal cerita secara mandiri dan rapi.", 1052, cy + 108, size=13, color=BODY, width=328, line_h=20)
    b.rect(f1, 1052, cy + 168, 328, 7, fill=HAIRLINE, radius=3.5)
    b.rect(f1, 1052, cy + 168, 246, 7, fill=PRIMARY, radius=3.5)
    b.text(f1, "Pertemuan 6 dari 8", 1052, cy + 184, size=11.5, color=MUTED, weight="SemiBold", width=296, max_lines=1)

    b.rect(f1, 1052, cy + 226, 328, 96, fill=SECONDARY_SOFT, radius=12, stroke=SECONDARY_BORDER)
    b.text(f1, "Rekomendasi Mentor", 1070, cy + 242, size=13, color=SECONDARY_DARK, weight="Bold", width=292, max_lines=1)
    b.text(f1, "Lanjutkan latihan 5 soal grafik fungsi pekan depan.", 1070, cy + 266, size=12.5, color=BODY, width=292, line_h=18)

    f2, cy, nav2, _, _ = draw_app_shell(b, "parent/schedules.html", 1540, 0, "parent", "Jadwal & Kalender", "Jadwal & Kalender Les Ananda", "Daftar jadwal rutin mingguan dan sesi les yang akan datang")
    draw_table_card(b, f2, cy, "Agenda & Jadwal Rutin Ananda", ["Tanggal Sesi", "Waktu", "Program Les", "Mentor Pengampu", "Status"],
                    [["Senin, 26 Nov", "15:30 - 17:00", "Matematika SMP", "Kak Sarah", "Disetujui"],
                     ["Kamis, 29 Nov", "15:30 - 17:00", "Matematika SMP", "Kak Sarah", "Disetujui"],
                     ["Sabtu, 01 Des", "10:00 - 11:30", "Bahasa Inggris", "Kak Sarah", "Disetujui"]])

    f3, cy, nav3, _, _ = draw_app_shell(b, "parent/attendance.html", 3080, 0, "parent", "Riwayat Kehadiran", "Riwayat Kehadiran Ananda", "Rekap kehadiran tatap muka beserta ringkasan materi tiap pertemuan")
    draw_table_card(b, f3, cy, "Catatan Kehadiran Pertemuan", ["Tanggal & Waktu", "Siklus Periode", "Program & Mentor", "Materi & Catatan", "Status"],
                    [["25 Nov 15:30", "Pertemuan 6/8", "Matematika, Kak Sarah", "Persamaan linear tuntas", "Hadir"],
                     ["18 Nov 15:30", "Pertemuan 5/8", "Matematika, Kak Sarah", "Latihan soal aljabar", "Hadir"],
                     ["11 Nov 15:30", "Pertemuan 4/8", "Matematika, Kak Sarah", "Evaluasi tengah periode", "Hadir"]])

    f4, cy, nav4, _, _ = draw_app_shell(b, "parent/progress.html", 0, 1060, "parent", "Laporan Perkembangan", "Laporan Perkembangan Belajar Ananda", "Laporan evaluasi belajar anak terbaru langsung dari mentor pembimbing")
    for idx, (dt, subj, mat, skill, rec) in enumerate([
        ("25 November 2026", "Matematika SMP, Kak Sarah", "Persamaan Linear Dua Variabel", "Mampu menyusun model matematika dari soal cerita dengan tepat.", "Lanjutkan latihan soal variasi pekan depan."),
        ("18 November 2026", "Matematika SMP, Kak Sarah", "Operasi Aljabar & Substitusi", "Kecepatan berhitung meningkat dan lebih percaya diri.", "Ulangi 3 soal latihan di buku catatan."),
    ]):
        ry = cy + idx * 290
        b.rect(f4, 284, ry, 1120, 266, fill=SURFACE, radius=12, stroke=HAIRLINE)
        b.text(f4, dt, 314, ry + 26, size=13, color=PRIMARY_DARK, weight="Bold", width=180, max_lines=1)
        b.text(f4, subj, 504, ry + 26, size=15.5, color=INK, weight="Bold", family=FONT_HEAD)
        b.text(f4, f"Materi Dipelajari: {mat}\nKemampuan Dikuasai: {skill}", 314, ry + 76, size=14.5, color=BODY, width=1060, line_h=24)
        b.rect(f4, 314, ry + 154, 1060, 78, fill=SECONDARY_SOFT, radius=12, stroke=SECONDARY_BORDER)
        b.icon(f4, "sparkles", 336, ry + 183, size=18, color=SECONDARY_DARK)
        b.text(f4, f"Rekomendasi Mentor: {rec}", 366, ry + 182, size=14, color=SECONDARY_DARK, weight="SemiBold")

    f5, cy, nav5, _, _ = draw_app_shell(b, "parent/bills.html", 1540, 1060, "parent", "Tagihan & Pembayaran", "Informasi Tagihan & Pembayaran Ananda", "Transparansi biaya paket belajar, riwayat cicilan, dan status lunas")
    p_bill_row0 = draw_table_card(b, f5, cy, "Daftar Tagihan Bimbingan Belajar", ["Kode Tagihan", "Program & Periode", "Total Tagihan", "Sudah Dibayar", "Sisa", "Status"],
                                  [["INV-2026-081", "Matematika, Periode #3", "Rp 800.000", "Rp 800.000", "Rp 0", "Lunas"],
                                   ["INV-2026-082", "Calistung, Periode #2", "Rp 650.000", "Rp 325.000", "Rp 325.000", "Cicilan"]])

    f6, cy, nav6, _, _ = draw_app_shell(b, "parent/no_children.html", 3080, 1060, "parent", "Ringkasan Belajar", "Data Siswa Belum Terhubung", "")
    b.rect(f6, 480, cy + 110, 720, 360, fill=SURFACE, radius=20, stroke=HAIRLINE)
    b.text(f6, "Belum Ada Siswa Terhubung", 520, cy + 180, size=22, color=INK, weight="Bold", family=FONT_HEAD, width=640, align="center")
    b.text(f6, "Hubungi Admin DESI PRIVAT untuk menautkan akun dengan data anak Anda.", 540, cy + 224, size=14.5, color=BODY, width=600, align="center", line_h=22)
    contact_admin_pill = b.pill(f6, 706, cy + 304, 268, 46, "Hubungi Admin", SECONDARY, SURFACE, size=13.5, weight="Bold", elevate=True)

    b.flow(f1, "Parent Portal Flow")

    # Page 06 Post-Click Interactive Layers (y=2160)
    ov_p_bill, ov_p_bill_sub = draw_modal_layer(
        b, "Overlay: Modal Rincian Rekening & Tagihan", 0, 2160,
        "Rincian Tagihan INV-2026-081",
        "Informasi pembayaran paket belajar & rekening resmi DESI PRIVAT",
        [("Program & Periode", "Matematika Terpadu SMP, Periode #3 (8 Sesi)"),
         ("Total & Status", "Rp 800.000, Lunas (Transfer BCA)")],
        "Lihat Kuitansi Resmi", accent=PRIMARY, w=480, cancel_lbl="Tutup"
    )
    b.close_overlay_link(ov_p_bill_sub)

    ov_p_contact, ov_p_contact_sub = draw_modal_layer(
        b, "Overlay: Modal Hubungi Admin DESI PRIVAT", 520, 2160,
        "Hubungi Admin DESI PRIVAT",
        "Permintaan penautan akun orang tua dengan data siswa aktif",
        [("Kontak WhatsApp Admin", "0812-1111-2222 (Jam layanan 08:00 - 17:00)"),
         ("ID Akun Wali", "Ibu Ratna Sari (parent1)")],
        "Kirim Permintaan Penautan", accent=SECONDARY, w=480
    )
    ov_p_toast = draw_toast_layer(
        b, "Overlay: Toast Permintaan Wali", 1040, 2160,
        "Pesan Terkirim ke Admin",
        "Admin akan menautkan profil anak Anda secepatnya.",
        accent=OK_TXT
    )
    b.swap_overlay_link(ov_p_contact_sub, ov_p_toast)

    b.overlay_link(prail, ov_p_bill, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    if p_bill_row0:
        b.overlay_link(p_bill_row0, ov_p_bill, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    b.link(child1_pill, f3, trans="dissolve", duration=200, easing="easeOut")
    b.link(child2_pill, f4, trans="dissolve", duration=200, easing="easeOut")
    b.overlay_link(contact_admin_pill, ov_p_contact, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    if cta1:
        b.link(cta1, f5, trans="push", direction="left", duration=300, easing="easeInOut")
    p_map = {
        "Ringkasan Belajar": f1, "Jadwal & Kalender": f2, "Riwayat Kehadiran": f3,
        "Laporan Perkembangan": f4, "Tagihan & Pembayaran": f5,
    }
    for src_f, n_dict in [(f1, nav1), (f2, nav2), (f3, nav3), (f4, nav4), (f5, nav5), (f6, nav6)]:
        if "__bell__" in n_dict:
            b.overlay_link(n_dict["__bell__"], ov_p_toast, trans="dissolve", duration=180, easing="easeOut")
        for lbl, dst_f in p_map.items():
            if dst_f != src_f and lbl in n_dict:
                b.link(n_dict[lbl], dst_f, trans="slideIn", direction="left", duration=280, easing="easeOut")


# ==============================================================================
# PAGE 8: DEVELOPER & ERROR PAGES (6) WITH CRISP ICON MEDALLIONS
# ==============================================================================
def build_page_07_dev_errors(b: FigBuilder):
    b.page_add("07 - Developer & Error Pages (6)")
    b.page_bg("#EAEAE6")

    fd1 = b.frame("developer/login.html: Developer Console Auth", 0, 0, 1440, 900, fill=ALABASTER, stroke=HAIRLINE)
    dcard = b.rect(fd1, 490, 210, 460, 440, fill=SURFACE, radius=20, stroke=HAIRLINE)
    b.shadow(dcard, blur=24, y=8, opacity=0.05)
    b.text(fd1, "Developer Console", 530, 258, size=24, color=INK, weight="Bold", family=FONT_HEAD, width=380, align="center")
    b.rect(fd1, 530, 324, 380, 48, fill=ALABASTER, radius=10, stroke=HAIRLINE)
    b.text(fd1, "ID Developer", 546, 339, size=14, color=MUTED)
    b.rect(fd1, 530, 390, 380, 48, fill=ALABASTER, radius=10, stroke=HAIRLINE)
    b.text(fd1, "Kata Sandi", 546, 405, size=14, color=MUTED)
    dev_btn = b.pill(fd1, 530, 468, 380, 48, "Masuk Monitoring", INK, SURFACE, size=14, weight="Bold")

    fd2, cy, dev_navs, dev_cta, dev_sec = draw_app_shell(b, "developer/dashboard.html", 1540, 0, "developer", "Live Activity Feed", "Developer Activity Monitoring", "", "Unduh CSV", "Unduh JSON")
    cy = draw_kpi_strip(b, fd2, cy, [("LIVE", "Stream Status", "", OK_BG, OK_TXT), ("1.420", "Total Events", "", PRIMARY_SOFT, PRIMARY_DARK)])
    draw_table_card(b, fd2, cy, "Live Activity Feed", ["ID", "Waktu", "Pelaku", "Modul", "Aksi", "IP Address"],
                    [["992", "23:30:12", "admin", "schedule", "CREATE_ROUTINE", "127.0.0.1"],
                     ["991", "23:28:04", "mentor1", "attendance", "UPLOAD_PHOTO", "127.0.0.1"]])

    ov_dev_exp, ov_dev_exp_sub = draw_modal_layer(
        b, "Overlay: Modal Ekspor Audit Log", 0, 2000,
        "Ekspor Audit Log Aktivitas",
        "Berkas terunduh bebas password_hash & token rahasia",
        [("Format Dipilih", "CSV / JSON Terstruktur"),
         ("Jumlah Event", "1.420 Catatan Aktivitas")],
        "Mulai Unduh", accent=PRIMARY, w=480
    )
    ov_dev_toast = draw_toast_layer(
        b, "Overlay: Toast Unduhan Developer Siap", 520, 2000,
        "Berkas Audit Siap",
        "Audit log berhasil diekspor ke folder unduhan.",
        accent=OK_TXT
    )
    b.swap_overlay_link(ov_dev_exp_sub, ov_dev_toast)

    b.flow(fd1, "Developer Flow")
    b.link(dev_btn, fd2, trans="moveIn", direction="left", duration=360)
    if dev_cta:
        b.overlay_link(dev_cta, ov_dev_exp, trans="moveIn", direction="bottom", duration=220, easing="easeOut")
    if dev_sec:
        b.overlay_link(dev_sec, ov_dev_exp, trans="moveIn", direction="bottom", duration=220, easing="easeOut")
    if "__logout__" in dev_navs:
        b.link(dev_navs["__logout__"], fd1, trans="slideIn", direction="right", duration=260, easing="easeOut")

    errs = [
        ("errors/400.html", "400", "Permintaan Tidak Valid", "Parameter atau token keamanan tidak sesuai. Muat ulang halaman.", "Ke Beranda", 3080, 0),
        ("errors/403.html", "403", "Akses Ditolak", "Anda tidak memiliki izin membuka halaman ini.", "Ke Dashboard", 0, 1000),
        ("errors/404.html", "404", "Halaman Tidak Ditemukan", "Alamat halaman tidak tersedia atau telah dipindahkan.", "Ke Beranda", 1540, 1000),
        ("errors/500.html", "500", "Kendala Server", "Terjadi gangguan sementara pada sistem. Silakan coba lagi.", "Ke Beranda", 3080, 1000),
    ]
    for fname, code, title, desc, cta, ex, ey in errs:
        fe = b.frame(fname, ex, ey, 1440, 900, fill=ALABASTER, stroke=HAIRLINE)
        ecard = b.rect(fe, 440, 210, 560, 440, fill=SURFACE, radius=20, stroke=HAIRLINE)
        b.shadow(ecard, blur=24, y=8, opacity=0.05)
        ecol = DANGER_TXT if code == "500" else SECONDARY_DARK
        b.text(fe, code, 480, 268, size=54, color=ecol, weight="Bold", family=FONT_HEAD, width=480, align="center", max_lines=1)
        b.text(fe, title, 480, 356, size=24, color=INK, weight="Bold", family=FONT_HEAD, width=480, align="center")
        b.text(fe, desc, 500, 404, size=15, color=BODY, width=440, align="center", line_h=24)
        err_btn = b.pill(fe, 590, 504, 260, 46, cta, PRIMARY, SURFACE, size=14, weight="Bold", elevate=True)
        b.link(err_btn, fd1, trans="dissolve", duration=240, easing="easeOut")


# ==============================================================================
# PAGE 9: MOBILE RESPONSIVE (390PX), PUBLIC + LOGIN + 4 ROLE DASHBOARDS
# ==============================================================================
def _draw_mobile_chrome(b: FigBuilder, fname, x, y, h, title, _role_lbl, bottom_tabs):
    f = b.frame(fname, x, y, 390, h, fill=ALABASTER, stroke=HAIRLINE)
    # Mobile Topbar (Bebas Badge di Mobile, Radius Ikon Seragam 12px)
    b.rect(f, 0, 0, 390, 62, fill=SURFACE, radius=0, stroke=HAIRLINE, name="Mobile Topbar")
    menu_hit = b.rect(f, 10, 13, 36, 36, fill=ALABASTER, radius=12, stroke=HAIRLINE, name="Mobile Menu Hit")
    b.icon(f, "menu", 19, 22, size=18, color=INK, stroke_w=1.85)
    draw_brand_mark(b, f, 54, 16, size=30, light=False)
    b.text(f, "DESI PRIVAT", 92, 22, size=14, color=INK, weight="Bold", family=FONT_HEAD, width=140, max_lines=1)
    bell = b.rect(f, 342, 13, 36, 36, fill=ALABASTER, radius=12, stroke=HAIRLINE, name="Mobile Bell")
    b.icon(f, "bell", 352, 23, size=16, color=BODY, stroke_w=1.75)

    b.text(f, title, 20, 78, size=18, color=INK, weight="Bold", family=FONT_HEAD, width=350, max_lines=1)

    # Floating Mobile Bottom Nav
    by = h - 70
    b.rect(f, 0, by, 390, 70, fill=SURFACE, radius=0, stroke=HAIRLINE, name="Mobile Bottom Nav")
    tab_hits = {"__menu__": menu_hit}
    tw = 390 / len(bottom_tabs)
    for ti, (ticon, tlbl, t_act) in enumerate(bottom_tabs):
        tx = ti * tw
        hit = b.rect(f, tx + 8, by + 8, tw - 16, 52, fill=PRIMARY_SOFT if t_act else SURFACE, radius=12, name=f"Mobile Tab {tlbl}")
        b.icon(f, ticon, tx + tw / 2 - 9, by + 16, size=18, color=PRIMARY_DARK if t_act else MUTED, stroke_w=1.9 if t_act else 1.65)
        b.text(f, tlbl, tx + 4, by + 40, size=10, color=PRIMARY_DARK if t_act else MUTED, weight="Bold" if t_act else "Medium", width=tw - 8, align="center", max_lines=1)
        tab_hits[tlbl] = hit
    return f, 114, bell, tab_hits


def build_page_08_mobile(b: FigBuilder):
    b.page_add("08 - Mobile Responsive (390px)")
    b.page_bg("#EAEAE6")

    # 1. Mobile Landing (390 x 1980, Framed 4x2 Hero + Concentric Sophie Eye Cards + Zero Solid Footer)
    ml = b.frame("mobile/landing.html (390px)", 0, 0, 390, 1980, fill=ALABASTER, stroke=HAIRLINE)
    b.rect(ml, 10, 10, 370, 510, fill="#085A8C", radius=22, name="Mobile Framed Hero Stage")
    for m_idx, m_file in enumerate(["galeri_01.webp", "galeri_02.webp", "galeri_05.webp", "galeri_06.webp"]):
        mx = 20 + (m_idx % 2) * 180
        my = 22 + (m_idx // 2) * 164 + (m_idx % 2) * -6
        b.rect(ml, mx, my, 170, 152, fill=PRIMARY_DEEP, radius=14)
        b.image(ml, m_file, mx, my, 170, 152, mode="fill", name=f"Mobile Hero Mosaic {m_idx+1}")
    b.gradient_rect(ml, 10, 10, 370, 510, ["#064E77B8", "#0076B2CC", "#075B8EF5", "#075B8EFF"], start=(0.5, 0.0), end=(0.5, 1.0), radius=22, name="Mobile Hero Mosaic Wash")
    draw_brand_mark(b, ml, 24, 24, size=32, light=True)
    b.text(ml, "DESI PRIVAT", 64, 31, size=14.5, color=SURFACE, weight="Bold", family=FONT_HEAD, width=140, max_lines=1)
    ml_login = b.pill(ml, 274, 23, 92, 34, "Masuk", SECONDARY, SURFACE, size=12, weight="Bold", elevate=True, radius=12)
    b.text(ml, "Bimbingan Privat\nyang Tenang &\nTerarah.", 24, 134, size=31, color=SURFACE, weight="Bold", family=FONT_HEAD, width=342, align="center", line_h=38)
    b.text(ml, "Mentor terkurasi datang ke rumah dengan laporan langsung untuk orang tua.", 24, 276, size=14, color="#EBF7FD", width=342, align="center", line_h=22)
    ml_cta = b.pill(ml, 28, 362, 334, 46, "Lihat Program", SECONDARY, SURFACE, size=14, weight="Bold", elevate=True, radius=12)
    ml_prog_btn = b.pill(ml, 28, 420, 334, 42, "Kontak", "#FFFFFF22", SURFACE, size=13, weight="Bold", stroke="#FFFFFF88", radius=12)

    # Mobile Pencapaian Siswa (Concentric 24/16 Sophie Cards + Eye Icon)
    b.text(ml, "Pencapaian Siswa.", 20, 552, size=19, color=INK, weight="Bold", family=FONT_HEAD, width=350, max_lines=1)
    _draw_sophie_achievement_card(b, ml, 20, 588, 350, 326, "pencapaian_01.webp", "M. Ian Ramadhan", "Juara 3 Olimpiade Matematika SD Expo SMAFT 2026.", "Expo SMAFT", outer_r=24, inner_r=16)
    _draw_sophie_achievement_card(b, ml, 20, 930, 350, 326, "pencapaian_04.webp", "M. Izhar Ismed", "Gold Medals Penyisihan Venus Kompetisi Makassar.", "Lolos Nasional", outer_r=24, inner_r=16)

    # Mobile Program Ringkas
    b.text(ml, "Program Bimbingan.", 20, 1288, size=19, color=INK, weight="Bold", family=FONT_HEAD, width=350, max_lines=1)
    ml_prog_cards = []
    for pi, (pno, pttl, pdesc, pcol) in enumerate([("01", "Privat SD", "Tematik & PR harian.", PRIMARY_DARK), ("02", "Privat SMP", "Matematika & IPA terpadu.", SECONDARY_DARK)]):
        py = 1324 + pi * 120
        pc = b.rect(ml, 20, py, 350, 108, fill=SURFACE, radius=16, stroke=HAIRLINE)
        b.text(ml, pno, 36, py + 16, size=11, color=pcol, weight="Bold", width=40, max_lines=1)
        b.text(ml, pttl, 36, py + 36, size=16, color=INK, weight="Bold", family=FONT_HEAD, width=300, max_lines=1)
        b.text(ml, pdesc, 36, py + 64, size=13, color=BODY, width=300, max_lines=1)
        ml_prog_cards.append(pc)

    # Mobile Light Closing Card + Transparent Contact Line (Zero Solid Footer)
    b.rect(ml, 20, 1584, 350, 212, fill=SURFACE, radius=16, stroke=HAIRLINE)
    b.text(ml, "Pantau Jadwal & Progres Anak.", 36, 1608, size=20, color=INK, weight="Bold", family=FONT_HEAD, width=318, line_h=26)
    b.text(ml, "Masuk ke portal untuk jadwal dan laporan belajar.", 36, 1670, size=13, color=BODY, width=318, max_lines=2)
    ml_close = b.pill(ml, 36, 1724, 318, 44, "Masuk Portal", SECONDARY, SURFACE, size=14, weight="Bold", elevate=True, radius=12)
    b.rect(ml, 20, 1838, 350, 1, fill=HAIRLINE, radius=0)
    b.text(ml, "DESI PRIVAT  |  0852-4200-9811  |  @desi_private\nMakassar  © 2026 DESI PRIVAT", 20, 1858, size=12, color=MUTED, width=350, line_h=20)

    # 2. Mobile Login (390 x 844)
    mlog = b.frame("mobile/login.html (390px)", 480, 0, 390, 844, fill=ALABASTER, stroke=HAIRLINE)
    b.image(mlog, "galeri_02.webp", 0, 0, 390, 260, mode="fill", name="Mobile Login Photo")
    b.gradient_rect(mlog, 0, 0, 390, 260, ["#083A54F2", "#0093D6C8"], start=(0.0, 1.0), end=(1.0, 0.0))
    draw_brand_mark(b, mlog, 20, 20, size=30, light=True)
    b.text(mlog, "DESI PRIVAT", 58, 25, size=14.5, color=SURFACE, weight="Bold", family=FONT_HEAD, width=140, max_lines=1)
    mlog_back = b.rect(mlog, 334, 18, 36, 36, fill=SURFACE, radius=12, stroke=HAIRLINE, name="Mobile Login Home Icon")
    b.icon(mlog, "home", 343, 27, size=18, color=INK, stroke_w=1.75)
    b.text(mlog, "Belajar Lebih Teratur.", 24, 172, size=24, color=SURFACE, weight="Bold", family=FONT_HEAD, width=342, max_lines=1)

    mc = b.rect(mlog, 20, 284, 350, 480, fill=SURFACE, radius=16, stroke=HAIRLINE)
    b.shadow(mc, blur=10, y=3, opacity=0.04)
    b.text(mlog, "Masuk", 40, 316, size=22, color=INK, weight="Bold", family=FONT_HEAD, width=310, max_lines=1)
    b.text(mlog, "ID Pengguna", 40, 366, size=13, color=INK, weight="Bold")
    b.rect(mlog, 40, 392, 310, 44, fill=ALABASTER, radius=12, stroke=HAIRLINE)
    b.text(mlog, "Masukkan ID pengguna Anda", 54, 406, size=13, color=MUTED)
    b.text(mlog, "Kata Sandi", 40, 456, size=13, color=INK, weight="Bold")
    b.rect(mlog, 40, 482, 310, 44, fill=ALABASTER, radius=12, stroke=HAIRLINE)
    b.text(mlog, "Masukkan kata sandi", 54, 496, size=13, color=MUTED)
    mlog_submit = b.pill(mlog, 40, 560, 310, 46, "Masuk", SECONDARY, SURFACE, size=14, weight="Bold", elevate=True, radius=12)
    b.text(mlog, "Butuh bantuan? Hubungi Admin", 40, 634, size=12.5, color=MUTED, width=310, align="center")

    # 3. Mobile Admin Dashboard (390 x 960, Tanpa Badge & Tanpa 3D)
    ma, cy, ma_bell, ma_tabs = _draw_mobile_chrome(
        b, "mobile/admin-dashboard.html (390px)", 960, 0, 960,
        "Pusat Operasional", "Admin",
        [("dashboard", "Dashboard", True), ("calendar", "Jadwal", False), ("graduation", "Siswa", False), ("menu", "Menu", False)]
    )
    b.rect(ma, 20, cy, 350, 128, fill=SURFACE, radius=12, stroke=HAIRLINE)
    b.text(ma, "Selamat datang, Admin.", 36, cy + 20, size=17, color=INK, weight="Bold", family=FONT_HEAD, width=318, max_lines=1)
    b.text(ma, "136 sesi terabsen, 6 agenda hari ini.", 36, cy + 46, size=12.5, color=BODY, width=318, max_lines=1)
    ma_btn = b.pill(ma, 36, cy + 74, 136, 36, "+ Jadwal", PRIMARY, SURFACE, size=12.5, weight="Bold")
    cy += 144
    for mi, (mv, mlb) in enumerate([("84", "Siswa Aktif"), ("18", "Mentor Aktif"), ("3", "Perlu Perhatian"), ("142", "Sesi Bulan Ini")]):
        mx = 20 + (mi % 2) * 181
        my = cy + (mi // 2) * 102
        b.rect(ma, mx, my, 169, 90, fill=SURFACE, radius=12, stroke=HAIRLINE)
        b.text(ma, mv, mx + 16, my + 20, size=22, color=INK, weight="Bold", family=FONT_HEAD, width=136, max_lines=1)
        b.text(ma, mlb, mx + 16, my + 52, size=12, color=MUTED, weight="SemiBold", width=136, max_lines=1)
    cy += 218
    b.text(ma, "Agenda Hari Ini (Gulir)", 20, cy, size=14.5, color=INK, weight="Bold", family=FONT_HEAD, width=350, max_lines=1)
    for ti, (tt, tp, ts, tm) in enumerate([("15:30 WIB", "Matematika SMP", "Naufal Pratama", "Kak Sarah"), ("16:00 WIB", "Calistung SD", "Alisha Putri", "Kak Dian")]):
        ty = cy + 28 + ti * 102
        b.rect(ma, 20, ty, 350, 90, fill=SURFACE, radius=12, stroke=HAIRLINE)
        b.text(ma, tt, 36, ty + 14, size=13, color=PRIMARY_DEEP, weight="Bold", family=FONT_HEAD, width=120, max_lines=1)
        b.text(ma, tp, 174, ty + 14, size=11.5, color=PRIMARY_DARK, weight="SemiBold", width=180, align="right", max_lines=1)
        b.rect(ma, 36, ty + 44, 318, 1, fill=HAIRLINE, radius=0)
        b.text(ma, ts, 36, ty + 56, size=12.5, color=INK, weight="Bold", width=180, max_lines=1)
        b.text(ma, tm, 224, ty + 56, size=12, color=MUTED, width=130, align="right", max_lines=1)

    # 4. Mobile Owner Dashboard (390 x 920)
    mo, cy, mo_bell, mo_tabs = _draw_mobile_chrome(
        b, "mobile/owner-dashboard.html (390px)", 1440, 0, 920,
        "Supervisi Pemilik", "Read-Only",
        [("dashboard", "Ringkasan", True), ("camera", "Absensi", False), ("wallet", "Honor", False), ("menu", "Menu", False)]
    )
    b.rect(mo, 20, cy, 350, 100, fill=SURFACE, radius=12, stroke=HAIRLINE)
    b.text(mo, "Pengawasan Eksekutif", 36, cy + 20, size=17, color=INK, weight="Bold", family=FONT_HEAD, width=318, max_lines=1)
    b.text(mo, "Pantau siswa, honor tentor & arus kas real-time.", 36, cy + 48, size=12.5, color=BODY, width=318, max_lines=1)
    cy += 116
    for mi, (mv, mlb) in enumerate([("Rp 24,5 Jt", "Omzet Periode"), ("Rp 11,8 Jt", "Honor Siap Kirim"), ("98%", "Kehadiran Sesi"), ("84", "Siswa Aktif")]):
        mx = 20 + (mi % 2) * 181
        my = cy + (mi // 2) * 102
        b.rect(mo, mx, my, 169, 90, fill=SURFACE, radius=12, stroke=HAIRLINE)
        b.text(mo, mv, mx + 16, my + 20, size=18, color=INK, weight="Bold", family=FONT_HEAD, width=136, max_lines=1)
        b.text(mo, mlb, mx + 16, my + 52, size=12, color=MUTED, weight="SemiBold", width=136, max_lines=1)
    cy += 220
    b.rect(mo, 20, cy, 350, 128, fill=PRIMARY_SOFT, radius=12, stroke=PRIMARY_BORDER)
    b.text(mo, "3 Fee Honor Tentor Siap Kirim", 36, cy + 18, size=14, color=PRIMARY_DEEP, weight="Bold", width=318, max_lines=1)
    b.text(mo, "Periode 8 pertemuan selesai & tervalidasi.", 36, cy + 44, size=12.5, color=BODY, width=318, max_lines=1)
    mo_honor_btn = b.pill(mo, 36, cy + 74, 152, 34, "Honorarium", PRIMARY, SURFACE, size=12, weight="Bold")

    # 5. Mobile Mentor Dashboard (390 x 920)
    mm, cy, mm_bell, mm_tabs = _draw_mobile_chrome(
        b, "mobile/mentor-dashboard.html (390px)", 1920, 0, 920,
        "Beranda Mentor", "Kak Sarah",
        [("dashboard", "Beranda", True), ("calendar", "Jadwal", False), ("camera", "Absensi", False), ("report", "Rapor", False)]
    )
    b.rect(mm, 20, cy, 350, 118, fill=SURFACE, radius=12, stroke=HAIRLINE)
    b.text(mm, "Selamat Bertugas, Mentor.", 36, cy + 20, size=17, color=INK, weight="Bold", family=FONT_HEAD, width=318, max_lines=1)
    mm_btn = b.pill(mm, 36, cy + 62, 150, 36, "Catat Absen", PRIMARY, SURFACE, size=12, weight="Bold")
    cy += 136
    b.rect(mm, 20, cy, 350, 148, fill=SECONDARY_SOFT, radius=12, stroke=SECONDARY_BORDER)
    b.text(mm, "Konfirmasi Mengajar: Naufal", 36, cy + 18, size=14, color=SECONDARY_DARK, weight="Bold", width=318, max_lines=1)
    b.text(mm, "26 Nov, 15:30 - 17:00 WIB (Matematika SMP)", 36, cy + 44, size=12, color=BODY, width=318, max_lines=1)
    mm_ready_btn = b.pill(mm, 36, cy + 84, 150, 38, "Siap Mengajar", OK_TXT, SURFACE, size=12, weight="Bold")
    mm_reject_btn = b.pill(mm, 200, cy + 84, 150, 38, "Berhalangan", DANGER_TXT, SURFACE, size=12, weight="Bold")
    cy += 168
    b.rect(mm, 20, cy, 350, 108, fill=SURFACE, radius=12, stroke=HAIRLINE)
    b.text(mm, "Siswa Bimbingan Aktif: 6 Siswa", 36, cy + 20, size=14, color=INK, weight="Bold", width=318, max_lines=1)
    b.text(mm, "Semua jadwal rutin minggu ini tercatat tanpa bentrok.", 36, cy + 48, size=12.5, color=MUTED, width=318, line_h=19)

    # 6. Mobile Parent Dashboard (390 x 920)
    mp, cy, mp_bell, mp_tabs = _draw_mobile_chrome(
        b, "mobile/parent-dashboard.html (390px)", 2400, 0, 920,
        "Portal Ananda", "Ibu Ratna",
        [("dashboard", "Beranda", True), ("calendar", "Jadwal", False), ("check", "Hadir", False), ("receipt", "SPP", False)]
    )
    b.rect(mp, 20, cy, 350, 118, fill=SURFACE, radius=12, stroke=HAIRLINE)
    b.text(mp, "Portal Belajar Naufal.", 36, cy + 20, size=17, color=INK, weight="Bold", family=FONT_HEAD, width=318, max_lines=1)
    mp_c1 = b.pill(mp, 36, cy + 60, 154, 36, "Naufal (8 SMP)", PRIMARY, SURFACE, size=12, weight="Bold")
    mp_c2 = b.pill(mp, 202, cy + 60, 148, 36, "Alisha (3 SD)", ALABASTER, BODY, size=12, weight="SemiBold", stroke=HAIRLINE)
    cy += 136
    b.rect(mp, 20, cy, 350, 102, fill=SURFACE, radius=12, stroke=HAIRLINE)
    b.text(mp, "Senin & Kamis, 15:30 WIB", 36, cy + 16, size=13.5, color=PRIMARY_DEEP, weight="Bold", family=FONT_HEAD, width=210, max_lines=1)
    b.text(mp, "Aktif", 260, cy + 17, size=12, color=OK_TXT, weight="Bold", width=92, align="right")
    b.rect(mp, 36, cy + 48, 318, 1, fill=HAIRLINE, radius=0)
    b.text(mp, "Matematika SMP, Kak Sarah", 36, cy + 62, size=13, color=INK, weight="SemiBold", width=318, max_lines=1)
    cy += 120
    mp_rep = b.rect(mp, 20, cy, 350, 168, fill=SURFACE, radius=12, stroke=HAIRLINE)
    b.text(mp, "Laporan Terbaru Mentor", 36, cy + 18, size=14.5, color=INK, weight="Bold", family=FONT_HEAD, width=318, max_lines=1)
    b.text(mp, "Persamaan Linear Dua Variabel", 36, cy + 48, size=13.5, color=PRIMARY_DARK, weight="Bold", width=318, max_lines=1)
    b.text(mp, "Mampu menyusun model matematika secara mandiri & rapi.", 36, cy + 74, size=12.5, color=BODY, width=318, line_h=19)
    b.rect(mp, 36, cy + 130, 318, 6, fill=HAIRLINE, radius=3)
    b.rect(mp, 36, cy + 130, 238, 6, fill=PRIMARY, radius=3)

    # Mobile Post-Click Interactive Layers (y=2060)
    mob_drawer = b.frame("Mobile Overlay: Navigasi Drawer (310px)", 0, 2060, 310, 720, fill=SURFACE, stroke=HAIRLINE)
    b.shadow(mob_drawer, blur=24, y=6, opacity=0.14)
    draw_brand_mark(b, mob_drawer, 22, 22, size=30, light=False)
    b.text(mob_drawer, "DESI PRIVAT", 62, 27, size=15, color=INK, weight="Bold", family=FONT_HEAD, width=160, max_lines=1)
    mob_dr_x = b.pill(mob_drawer, 254, 20, 32, 32, "×", ALABASTER, INK, size=15, weight="Bold", stroke=HAIRLINE)
    b.close_overlay_link(mob_dr_x)
    b.rect(mob_drawer, 20, 68, 270, 1, fill=HAIRLINE, radius=0)
    mob_dr_links = []
    for di, dlbl in enumerate(["Dashboard Admin", "Supervisi Pemilik", "Portal Mentor", "Portal Wali Murid", "Beranda Publik"]):
        dy = 86 + di * 52
        dr = b.rect(mob_drawer, 16, dy, 278, 42, fill=PRIMARY_SOFT if di == 0 else ALABASTER, radius=12, stroke=HAIRLINE)
        b.text(mob_drawer, dlbl, 32, dy + 13, size=13, color=PRIMARY_DARK if di == 0 else INK, weight="Bold" if di == 0 else "Medium", width=240, max_lines=1)
        mob_dr_links.append(dr)

    mob_sheet_form, mob_sheet_sub = draw_modal_layer(
        b, "Mobile Overlay: Bottom Sheet Buat Jadwal / Absensi", 360, 2060,
        "Input Jadwal / Absensi Sesi",
        "Formulir cepat 1-tangan bebas bentrok",
        [("Siswa & Program", "Naufal Pratama, Matematika SMP"),
         ("Hari & Waktu", "Senin, 15:30 - 17:00 WIB")],
        "Simpan Data", accent=SECONDARY, w=390
    )
    mob_sheet_rej, mob_sheet_rej_sub = draw_modal_layer(
        b, "Mobile Overlay: Sheet Alasan Berhalangan", 800, 2060,
        "Alasan Berhalangan Mengajar",
        "Admin otomatis menyiapkan mentor pengganti",
        [("Alasan Wajib Diisi", "Sakit / urusan keluarga mendadak")],
        "Kirim Alasan", accent=DANGER_TXT, w=390
    )
    mob_toast = draw_toast_layer(
        b, "Mobile Overlay: Toast Konfirmasi", 1240, 2060,
        "Berhasil Diperbarui",
        "Status sesi & jadwal Anda telah tersimpan.",
        accent=OK_TXT, w=350, h=92
    )

    b.flow(ml, "Mobile Responsive Flow (390px)")
    b.link(ml_login, mlog, trans="moveIn", direction="left", duration=320, easing="easeOut")
    b.link(ml_cta, mlog, trans="moveIn", direction="left", duration=320, easing="easeOut")
    b.link(ml_close, mlog, trans="moveIn", direction="left", duration=320, easing="easeOut")
    b.scroll_link(ml_prog_btn, ml_prog_cards[0])
    for mpc in ml_prog_cards:
        b.overlay_link(mpc, mob_sheet_form, trans="moveIn", direction="bottom", duration=240, easing="easeOut")

    b.link(mlog_back, ml, trans="slideIn", direction="right", duration=260, easing="easeOut")
    b.link(mlog_submit, ma, trans="moveIn", direction="left", duration=320, easing="easeOut")

    b.overlay_link(ma_btn, mob_sheet_form, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    b.overlay_link(mm_btn, mob_sheet_form, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    b.overlay_link(mm_ready_btn, mob_toast, trans="dissolve", duration=200, easing="easeOut")
    b.overlay_link(mm_reject_btn, mob_sheet_rej, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    b.overlay_link(mo_honor_btn, mob_toast, trans="dissolve", duration=200, easing="easeOut")
    b.overlay_link(mp_c1, mob_toast, trans="dissolve", duration=200, easing="easeOut")
    b.overlay_link(mp_c2, mob_toast, trans="dissolve", duration=200, easing="easeOut")
    b.overlay_link(mp_rep, mob_sheet_form, trans="moveIn", direction="bottom", duration=240, easing="easeOut")
    b.swap_overlay_link(mob_sheet_sub, mob_toast)
    b.swap_overlay_link(mob_sheet_rej_sub, mob_toast)

    for mb in [ma_bell, mo_bell, mm_bell, mp_bell]:
        b.overlay_link(mb, mob_toast, trans="dissolve", duration=180, easing="easeOut")
    for mtabs in [ma_tabs, mo_tabs, mm_tabs, mp_tabs]:
        b.overlay_link(mtabs["__menu__"], mob_drawer, trans="moveIn", direction="right", duration=240, easing="easeOut")

    b.link(mob_dr_links[0], ma, trans="dissolve", duration=220, easing="easeOut")
    b.link(mob_dr_links[1], mo, trans="dissolve", duration=220, easing="easeOut")
    b.link(mob_dr_links[2], mm, trans="dissolve", duration=220, easing="easeOut")
    b.link(mob_dr_links[3], mp, trans="dissolve", duration=220, easing="easeOut")
    b.link(mob_dr_links[4], ml, trans="dissolve", duration=220, easing="easeOut")

    b.link(ma_tabs["Menu"], mo, trans="push", direction="left", duration=280, easing="easeInOut")
    b.link(mo_tabs["Menu"], mm, trans="push", direction="left", duration=280, easing="easeInOut")
    b.link(mm_tabs["Rapor"], mp, trans="push", direction="left", duration=280, easing="easeInOut")
    b.link(mp_tabs["Beranda"], ml, trans="dissolve", duration=240, easing="easeOut")


def main():
    b = FigBuilder()
    build_page_00_design_system(b)
    build_page_01_public_auth(b)
    build_page_02_admin_ops(b)
    build_page_03_admin_fin_sys(b)
    build_page_04_owner(b)
    build_page_05_mentor(b)
    build_page_06_parent(b)
    build_page_07_dev_errors(b)
    build_page_08_mobile(b)

    b.steps.append({
        "command": "file.save",
        "params": {"path": r"c:\Users\Coding\04 - Desi Private\design\00 - desi private.figcraft"}
    })
    tmp_json = Path(os.environ.get("TEMP", r"C:\Windows\Temp")) / "00_desi_private_cmds.json"
    payload = json.dumps(b.steps)
    assert "\u2014" not in payload and "\u2013" not in payload, "Em/en dash detected in FigCraft payload!"
    tmp_json.write_text(payload, encoding="utf-8")
    print(f"Generated {len(b.steps)} FigCraft commands -> {tmp_json}")


if __name__ == "__main__":
    main()
