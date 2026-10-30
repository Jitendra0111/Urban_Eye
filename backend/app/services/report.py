"""PDF report of a saved analysis or comparison (ReportLab).

Built from the saved API response, so a report always matches what the user saw on screen.
"""
import base64
import io
import re
from datetime import datetime

from PIL import Image
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image as RLImage, KeepTogether, ListFlowable, ListItem, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from .segmenter import CLASS_NAMES, PALETTE

INK = colors.HexColor("#0f1e27")
MUTED = colors.HexColor("#5f6f77")
TEAL = colors.HexColor("#0e7c74")
AMBER = colors.HexColor("#c27c00")
LINE = colors.HexColor("#dde4e3")
HEAD_BG = colors.HexColor("#eef2f1")
LEVEL_COLOURS = {"healthy": "#2f7a3e", "balanced": "#2f7a3e", "warning": "#c27c00",
                 "danger": "#b3261e", "critical": "#b3261e", "unknown": "#5f6f77"}
CLASS_COLOURS = {n: colors.Color(*(c / 255 for c in rgb)) for n, rgb in zip(CLASS_NAMES, PALETTE)}

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

styles = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=20,
                    leading=24, textColor=INK, spaceAfter=2)
H2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12.5,
                    leading=16, textColor=INK, spaceBefore=10, spaceAfter=6)
BODY = ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5,
                      leading=13, textColor=INK, alignment=TA_LEFT)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8, leading=10.5, textColor=MUTED)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=9, leading=11.5)


# ---------------------------------------------------------------- helpers

def _text(s: str) -> str:
    """Plain Latin-1 text for the built-in PDF fonts: arrows as words, emoji removed, XML escaped."""
    s = (s or "").replace("→", "to").replace("×", "x").replace("–", "-").replace("—", "-")
    s = s.encode("latin-1", "ignore").decode("latin-1")
    s = re.sub(r"\s+", " ", s).strip()
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _label(name: str) -> str:
    return name[:1].upper() + name[1:]


def _date(d: str | None) -> str:
    if not d or d == "latest":
        return "Latest imagery"
    try:
        return datetime.fromisoformat(d[:10]).strftime("%d %b %Y")
    except ValueError:
        return d


def _ha(v: float) -> str:
    return f"{v / 100:.2f} km²" if v >= 100 else f"{v:.2f} ha"


def _coord(v: float, pos: str, neg: str) -> str:
    return f"{abs(v):.4f}°{pos if v >= 0 else neg}"


def _picture(data_url: str | None, width: float, max_px: int = 900, photo: bool = True):
    """Data-URL image scaled for the PDF. Photos become JPEG; label maps stay PNG (sharp edges)."""
    if not data_url:
        return None
    im = Image.open(io.BytesIO(base64.b64decode(data_url.split(",", 1)[1]))).convert("RGB")
    if max(im.size) > max_px:
        im.thumbnail((max_px, max_px), Image.BILINEAR if photo else Image.NEAREST)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=85) if photo else im.save(buf, format="PNG")
    buf.seek(0)
    return RLImage(buf, width=width, height=width * im.height / im.width)


def _captioned(pairs: list[tuple], width: float) -> Table:
    """Images side by side, each with a caption underneath."""
    col = (width - 6 * mm * (len(pairs) - 1)) / len(pairs)
    pics = [_picture(src, col, photo=photo) for src, _, photo in pairs]
    caps = [Paragraph(_text(cap), SMALL) for _, cap, _ in pairs]
    t = Table([pics, caps], colWidths=[col + (6 * mm if i < len(pairs) - 1 else 0)
                                       for i in range(len(pairs))])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 1), (-1, 1), 3)]))
    return t


def _strip(coverage: dict[str, float], width: float, height: float = 16, label: str | None = None) -> Drawing:
    """The composition strip: the area's land cover as one bar."""
    top = 12 if label else 0
    d = Drawing(width, height + top)
    if label:
        d.add(String(0, height + 3, _text(label), fontName="Helvetica", fontSize=8, fillColor=MUTED))
    total = sum(coverage.get(c, 0) for c in CLASS_NAMES) or 1
    x = 0.0
    for c in CLASS_NAMES:
        w = width * coverage.get(c, 0) / total
        if w <= 0:
            continue
        d.add(Rect(x, 0, w, height, fillColor=CLASS_COLOURS[c], strokeColor=colors.HexColor("#00000033"),
                   strokeWidth=0.3))
        pct = coverage.get(c, 0)
        if pct >= 9:
            dark = c in ("road", "rangeland")
            d.add(String(x + w / 2, height / 2 - 3, f"{pct:.0f}%", fontName="Helvetica-Bold", fontSize=7.5,
                         textAnchor="middle", fillColor=INK if dark else colors.white))
        x += w
    return d


def _legend(width: float) -> Drawing:
    d = Drawing(width, 12)
    x = 0.0
    for c in CLASS_NAMES:
        d.add(Rect(x, 2, 8, 8, fillColor=CLASS_COLOURS[c], strokeColor=colors.HexColor("#8a9599"),
                   strokeWidth=0.4))
        d.add(String(x + 11, 3, _label(c), fontName="Helvetica", fontSize=7.5, fillColor=INK))
        x += 11 + 4.3 * len(c) + 12
    return d


def _table(rows: list[list], widths: list[float], numeric_from: int = 1) -> Table:
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
        ("ALIGN", (numeric_from, 0), (-1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _swatch(c: str) -> Drawing:
    d = Drawing(10, 9)
    d.add(Rect(0, 0, 8, 8, fillColor=CLASS_COLOURS.get(c, colors.grey), strokeColor=colors.HexColor("#8a9599"),
               strokeWidth=0.4))
    return d


def _class_cell(c: str) -> Table:
    t = Table([[_swatch(c), Paragraph(_text(_label(c)), CELL)]], colWidths=[12, None])
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return t


def _facts(rows: list[tuple[str, str]]) -> Table:
    data = [[Paragraph(_text(k).upper(), SMALL), Paragraph(_text(v), CELL)] for k, v in rows]
    t = Table(data, colWidths=[38 * mm, CONTENT_W - 38 * mm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    return t


def _impact(impact: dict, title: str | None = None, recommendations: bool = True) -> list:
    colour = LEVEL_COLOURS.get(impact.get("level"), "#5f6f77")
    out = []
    if title:
        out.append(Paragraph(_text(title), ParagraphStyle("t", parent=BODY, fontName="Helvetica-Bold")))
    out.append(Paragraph(f'<font color="{colour}"><b>{_text(impact["status"])}</b></font>', BODY))
    out.append(Paragraph(f'Green score <b>{impact["green_score"]:.1f}</b> &nbsp;&nbsp; '
                         f'Urban score <b>{impact["urban_score"]:.1f}</b>', BODY))
    if recommendations and impact.get("recommendations"):
        out.append(Spacer(1, 4))
        out.append(ListFlowable([ListItem(Paragraph(_text(r), BODY), leftIndent=10)
                                 for r in impact["recommendations"]],
                                bulletType="bullet", start="•", leftIndent=10, bulletFontSize=8))
    if impact.get("source") == "detection":
        out.append(Paragraph("Estimated from detection boxes because the U-Net++ model was not loaded.", SMALL))
    return out


def _location(item: dict) -> list[tuple[str, str]]:
    w, s, e, n = item["bbox"]
    return [("Centre", f"{_coord((s + n) / 2, 'N', 'S')} {_coord((w + e) / 2, 'E', 'W')}"),
            ("Bounds", f"NW {_coord(n, 'N', 'S')} {_coord(w, 'E', 'W')} · SE {_coord(s, 'N', 'S')} "
                       f"{_coord(e, 'E', 'W')}"),
            ("Area", _ha(item["area_ha"]))]


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 10 * mm, "UrbanEye · U-Net++ land-cover segmentation (OpenEarthMap, 8 classes) · "
                                       "Imagery © Esri, Maxar, Earthstar Geographics")
    canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Page {doc.page}")
    canvas.setFillColor(TEAL)
    canvas.rect(0, PAGE_H - 5, PAGE_W, 5, stroke=0, fill=1)
    canvas.restoreState()


# ---------------------------------------------------------------- report bodies

def _analysis(item: dict, r: dict) -> list:
    scene, seg, impact = r["scene"], r.get("segmentation"), r["impact"]
    cov = impact["coverage"]
    story = [Paragraph("Land-cover report", H1),
             Paragraph(f"Area analysis · {_text(_date(scene['date']))}", SMALL), Spacer(1, 8)]
    story.append(_facts(_location(item) + [
        ("Imagery date", _date(scene["date"])),
        ("Resolution", f"{scene['meters_per_pixel']} m per pixel · {scene['width']} x {scene['height']} px"),
        ("Model", f"{item['model']} · {r.get('quality', 'accurate').capitalize()} mode"),
        ("Analysed", _saved(item)),
    ]))
    story += [Paragraph("Land cover", H2), _strip(cov, CONTENT_W), Spacer(1, 6)]
    pics = [(scene["image"], "Satellite image", True)]
    if seg:
        pics.append((seg["mask_image"], "Land-cover map", False))
    story += [_captioned(pics, CONTENT_W), Spacer(1, 4), _legend(CONTENT_W)]

    rows = [["Class", "Share", "Area"]]
    for c, pct in sorted(cov.items(), key=lambda kv: -kv[1]):
        if pct > 0:
            rows.append([_class_cell(c), f"{pct:.1f}%", _ha(pct * scene["area_ha"] / 100)])
    story += [KeepTogether([Paragraph("Coverage by class", H2), _table(rows, [80 * mm, 40 * mm, 40 * mm])])]

    det = r.get("detection")
    if det:
        counts = ", ".join(f"{k} {v}" for k, v in det["counts"].items()) or "none found"
        story += [Paragraph("Detected objects", H2), Paragraph(_text(counts), BODY)]
    story += [KeepTogether([Paragraph("Environmental assessment", H2), *_impact(impact)])]
    story += [Spacer(1, 10), Paragraph(_text(scene["attribution"]), SMALL)]
    return story


def _comparison(item: dict, r: dict) -> list:
    b, a = r["before"], r["after"]
    db, da = _date(b["scene"]["date"]), _date(a["scene"]["date"])
    story = [Paragraph("Land-cover change report", H1),
             Paragraph(f"Change comparison · {_text(db)} to {_text(da)}", SMALL), Spacer(1, 8)]
    story.append(_facts(_location(item) + [
        ("Dates compared", f"{db} to {da}"),
        ("Area changed", f"{r['changed_percent']:.1f}% · {_ha(r['changed_hectares'])}"),
        ("Model", f"{item['model']} · {r.get('quality', 'accurate').capitalize()} mode"),
        ("Analysed", _saved(item)),
    ]))
    story += [Paragraph("Land cover at each date", H2),
              _strip(b["impact"]["coverage"], CONTENT_W, label=db), Spacer(1, 4),
              _strip(a["impact"]["coverage"], CONTENT_W, label=da), Spacer(1, 8),
              _captioned([(b["scene"]["image"], f"Satellite image, {db}", True),
                          (a["scene"]["image"], f"Satellite image, {da}", True)], CONTENT_W)]
    if b.get("segmentation") and a.get("segmentation"):
        story += [Spacer(1, 6), _captioned([(b["segmentation"]["mask_image"], f"Land cover, {db}", False),
                                            (a["segmentation"]["mask_image"], f"Land cover, {da}", False)],
                                           CONTENT_W),
                  Spacer(1, 4), _legend(CONTENT_W)]

    change = _picture(r["change_map"], CONTENT_W * 0.6, photo=True)
    story += [KeepTogether([Paragraph("Where the land changed", H2), change,
                            Paragraph("Changed pixels in the colour of their new class; unchanged land is grey.",
                                      SMALL)])]

    rows = [["From", "To", "Share", "Area"]]
    for t in r["transitions"]:
        rows.append([_class_cell(t["from_class"]), _class_cell(t["to_class"]), f"{t['percent']:.1f}%",
                     _ha(t["hectares"])])
    if len(rows) == 1:
        rows.append(["No change above 0.05% of the area", "", "", ""])
    story += [KeepTogether([Paragraph("Biggest transitions", H2),
                            _table(rows, [55 * mm, 55 * mm, 30 * mm, 38 * mm], numeric_from=2)])]

    cb, ca = b["impact"]["coverage"], a["impact"]["coverage"]
    rows = [["Class", db, da, "Change"]]
    for c in sorted(CLASS_NAMES, key=lambda c: -ca.get(c, 0)):
        if cb.get(c, 0) or ca.get(c, 0):
            d = ca.get(c, 0) - cb.get(c, 0)
            rows.append([_class_cell(c), f"{cb.get(c, 0):.1f}%", f"{ca.get(c, 0):.1f}%",
                         f"{'+' if d > 0 else ''}{d:.1f}"])
    story += [KeepTogether([Paragraph("Coverage by class", H2),
                            _table(rows, [70 * mm, 36 * mm, 36 * mm, 36 * mm])])]

    pair = Table([[_impact(b["impact"], db, recommendations=False), _impact(a["impact"], da, recommendations=False)]],
                 colWidths=[CONTENT_W / 2] * 2)
    pair.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story += [KeepTogether([Paragraph("Environmental assessment", H2), pair]),
              Paragraph("Recommendations for the later date", H2), *_impact(a["impact"])[2:]]
    story += [Spacer(1, 8),
              Paragraph("Images from different dates can be slightly shifted or taken in different seasons, so "
                        "thin changes along edges and shadows are often not real.", SMALL),
              Paragraph(_text(a["scene"]["attribution"]), SMALL)]
    return story


def _saved(item: dict) -> str:
    try:
        return datetime.fromisoformat(item["created_at"]).strftime("%d %b %Y, %H:%M UTC")
    except ValueError:
        return item["created_at"]


def build_pdf(item: dict, result: dict) -> bytes:
    """item: HistoryItem as a dict; result: the saved /analyze or /compare response."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=16 * mm,
                            bottomMargin=18 * mm, title="UrbanEye land-cover report", author="UrbanEye")
    story = _comparison(item, result) if item["kind"] == "comparison" else _analysis(item, result)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
