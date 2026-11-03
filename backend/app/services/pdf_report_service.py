"""
KPIT professional PDF test report, generated from a Robot Framework output.xml.

Layout
  p.1   cover band · verdict · KPI cards · pass/fail donut · run information · suites · tags
  p.2+  failures at a glance · slowest tests · result table · per-test step details
Every page has a running header and a "Page x of y" footer.

Only ReportLab is used (already in requirements.txt) – no extra dependency.
"""
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Circle, Drawing, Rect, String, Wedge
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    CondPageBreak, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

# ------------------------------------------------------------------ palette
BLACK = colors.HexColor("#0a0b09")
INK = colors.HexColor("#14160f")
LIME = colors.HexColor("#b9f53a")
LIME_DEEP = colors.HexColor("#3f6212")
LIME_SOFT = colors.HexColor("#f1fbd8")
MUTED = colors.HexColor("#6b7160")
FAINT = colors.HexColor("#9aa08c")
BORDER = colors.HexColor("#e1e4d8")
PAPER = colors.HexColor("#f6f7f2")
GREEN = colors.HexColor("#15803d")
GREEN_BG = colors.HexColor("#dcfce7")
RED = colors.HexColor("#dc2626")
RED_BG = colors.HexColor("#fee2e2")
AMBER = colors.HexColor("#b45309")
AMBER_BG = colors.HexColor("#fef3c7")
SKY = colors.HexColor("#0369a1")

PAGE_W, PAGE_H = A4
MARGIN_X = 16 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X
BAND_H = 50 * mm          # first-page header band
RUN_H = 14 * mm           # running header on the other pages


# ------------------------------------------------------------------ helpers
def _esc(text: Any) -> str:
    return escape(str(text if text is not None else ""))


def _fmt_dur(seconds: Optional[float]) -> str:
    if seconds is None:
        return "—"
    if seconds < 1:
        return f"{int(round(seconds * 1000))} ms"
    if seconds < 60:
        return f"{seconds:.2f} s"
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}m {s:02d}s"


def _parse_ts(value: str) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y%m%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _status_info(status_el) -> Dict[str, Any]:
    """Works for Robot 7 (start/elapsed) and Robot <= 6 (starttime/endtime)."""
    if status_el is None:
        return {"status": "FAIL", "elapsed": None, "start": None, "text": ""}
    start_raw = status_el.get("start") or status_el.get("starttime") or ""
    start = _parse_ts(start_raw)
    elapsed = None
    if status_el.get("elapsed") is not None:
        try:
            elapsed = float(status_el.get("elapsed"))
        except ValueError:
            elapsed = None
    elif status_el.get("endtime"):
        end = _parse_ts(status_el.get("endtime"))
        if start and end:
            elapsed = (end - start).total_seconds()
    return {
        "status": (status_el.get("status") or "FAIL").upper(),
        "elapsed": elapsed,
        "start": start,
        "text": (status_el.text or "").strip(),
    }


def _draw_logo(c, x: float, y: float, height: float, color) -> float:
    """KPIT wordmark drawn with strokes (same geometry as the web app). Returns its width."""
    s = height / 66.0

    def X(v): return x + v * s
    def Y(v): return y + (66 - v) * s

    c.saveState()
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(9 * s)
    c.setLineCap(0)
    c.setLineJoin(0)

    def line(x1, y1, x2, y2):
        p = c.beginPath(); p.moveTo(X(x1), Y(y1)); p.lineTo(X(x2), Y(y2)); c.drawPath(p, stroke=1, fill=0)

    line(12, 6, 12, 40); line(15, 33, 38, 6); line(17, 29, 41, 58)             # K
    k = 0.5523 * 14
    p = c.beginPath()                                                           # P
    p.moveTo(X(60), Y(60)); p.lineTo(X(60), Y(6)); p.lineTo(X(73), Y(6))
    p.curveTo(X(73 + k), Y(6), X(87), Y(20 - k), X(87), Y(20))
    p.curveTo(X(87), Y(20 + k), X(73 + k), Y(34), X(73), Y(34))
    p.lineTo(X(60), Y(34))
    c.drawPath(p, stroke=1, fill=0)
    line(100, 6, 100, 60)                                                       # I
    line(113, 6, 143, 6); line(128, 6, 128, 60)                                 # T
    c.circle(X(12), Y(58), 5.5 * s, stroke=0, fill=1)                           # dots
    c.circle(X(152), Y(9), 5.5 * s, stroke=0, fill=1)
    c.restoreState()
    return 160 * s


class _NumberedCanvas(rl_canvas.Canvas):
    """Two-pass canvas so the footer can say 'Page x of y'."""

    def __init__(self, *args, **kwargs):
        self._footer_meta = kwargs.pop("footer_meta", {})
        super().__init__(*args, **kwargs)
        self._saved_pages: List[dict] = []

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_pages)
        for state in self._saved_pages:
            self.__dict__.update(state)
            self._draw_chrome(total)
            super().showPage()
        super().save()

    def _draw_chrome(self, total: int):
        page = self._pageNumber
        meta = self._footer_meta
        self.saveState()
        if page == 1:
            self._draw_cover_band(meta)
        else:
            self.setFillColor(BLACK)
            self.rect(0, PAGE_H - RUN_H, PAGE_W, RUN_H, stroke=0, fill=1)
            self.setFillColor(LIME)
            self.rect(0, PAGE_H - RUN_H - 0.8 * mm, PAGE_W, 0.8 * mm, stroke=0, fill=1)
            _draw_logo(self, MARGIN_X, PAGE_H - RUN_H + 3.6 * mm, 6.8 * mm, LIME)
            self.setFillColor(colors.HexColor("#c9cdbd"))
            self.setFont("Helvetica", 8)
            self.drawRightString(PAGE_W - MARGIN_X, PAGE_H - RUN_H + 5 * mm,
                                 f"Test Execution Report  ·  {meta.get('label', '')}")
        # footer
        self.setStrokeColor(BORDER)
        self.setLineWidth(0.5)
        self.line(MARGIN_X, 13 * mm, PAGE_W - MARGIN_X, 13 * mm)
        self.setFillColor(FAINT)
        self.setFont("Helvetica", 7.5)
        self.drawString(MARGIN_X, 8.5 * mm, "KPIT Auth Platform  ·  Confidential")
        self.drawRightString(PAGE_W - MARGIN_X, 8.5 * mm, f"Page {page} of {total}")
        self.restoreState()

    def _draw_cover_band(self, meta: dict):
        self.setFillColor(BLACK)
        self.rect(0, PAGE_H - BAND_H, PAGE_W, BAND_H, stroke=0, fill=1)
        # soft lime glow + grid
        self.setFillColor(colors.Color(0.725, 0.96, 0.227, alpha=0.10))
        self.circle(PAGE_W - 18 * mm, PAGE_H - 6 * mm, 46 * mm, stroke=0, fill=1)
        self.setFillColor(colors.Color(0.725, 0.96, 0.227, alpha=0.10))
        self.circle(PAGE_W - 8 * mm, PAGE_H - 10 * mm, 28 * mm, stroke=0, fill=1)
        self.setStrokeColor(colors.Color(0.725, 0.96, 0.227, alpha=0.07))
        self.setLineWidth(0.4)
        for gx in range(0, int(PAGE_W), 12):
            self.line(gx, PAGE_H - BAND_H, gx, PAGE_H)
        for gy in range(int(PAGE_H - BAND_H), int(PAGE_H), 12):
            self.line(0, gy, PAGE_W, gy)
        self.setFillColor(LIME)
        self.rect(0, PAGE_H - BAND_H - 1.2 * mm, PAGE_W, 1.2 * mm, stroke=0, fill=1)

        _draw_logo(self, MARGIN_X, PAGE_H - 19 * mm, 9 * mm, LIME)
        self.setFillColor(colors.HexColor("#a4a995"))
        self.setFont("Helvetica-Bold", 7.5)
        self.drawString(MARGIN_X + 33 * mm, PAGE_H - 14.2 * mm, "TEST PLATFORM")

        self.setFillColor(colors.white)
        self.setFont("Helvetica-Bold", 25)
        self.drawString(MARGIN_X, PAGE_H - 33 * mm, "Test Execution Report")
        self.setFillColor(colors.HexColor("#c9cdbd"))
        self.setFont("Helvetica", 9.5)
        self.drawString(MARGIN_X, PAGE_H - 40.5 * mm,
                        f"{meta.get('suite', '')}   ·   Job {meta.get('label', '')}")
        self.setFont("Helvetica", 8.5)
        self.setFillColor(colors.HexColor("#8c9280"))
        self.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 40.5 * mm, f"Generated {meta.get('generated', '')}")


# ------------------------------------------------------------------ service
class PdfReportService:
    """Builds the PDF from Robot Framework output.xml."""

    # ---------------------------------------------------------------- parsing
    def parse_output_xml(self, xml_path: Path) -> Dict[str, Any]:
        if not xml_path.exists():
            raise FileNotFoundError(f"output.xml not found: {xml_path}")

        root = ET.parse(xml_path).getroot()
        generator = root.get("generator", "Robot Framework")
        m = re.search(r"Robot ([\d.]+)", generator)
        py = re.search(r"Python ([\d.]+)", generator)
        on = re.search(r" on (\w+)\)", generator)

        root_suite = root.find("suite")
        root_info = _status_info(root_suite.find("status")) if root_suite is not None else {}

        tests: List[Dict[str, Any]] = []
        suites: List[Dict[str, Any]] = []

        def walk(suite_el, path: List[str]):
            name = suite_el.get("name") or "Suite"
            source = suite_el.get("source") or ""
            label = os.path.basename(source) if source and source.endswith(".robot") else name
            direct = suite_el.findall("test")
            if direct:
                sinfo = _status_info(suite_el.find("status"))
                suites.append({"name": label, "elapsed": sinfo["elapsed"], "passed": 0, "failed": 0, "skipped": 0, "total": 0})
            for test_el in direct:
                t = self._parse_test(test_el, label)
                tests.append(t)
                s = suites[-1]
                s["total"] += 1
                s["passed" if t["status"] == "PASS" else "skipped" if t["status"] == "SKIP" else "failed"] += 1
            for child in suite_el.findall("suite"):
                walk(child, path + [name])

        if root_suite is not None:
            walk(root_suite, [])

        passed = sum(1 for t in tests if t["status"] == "PASS")
        skipped = sum(1 for t in tests if t["status"] == "SKIP")
        failed = len(tests) - passed - skipped
        total = len(tests)

        tags = []
        for stat in root.findall("./statistics/tag/stat"):
            tags.append({
                "name": (stat.text or "").strip(),
                "passed": int(stat.get("pass", 0)),
                "failed": int(stat.get("fail", 0)),
            })

        started = root_info.get("start")
        ended = None
        if started and root_info.get("elapsed") is not None:
            from datetime import timedelta
            ended = started + timedelta(seconds=root_info["elapsed"])

        return {
            "suite_name": ", ".join(s["name"] for s in suites[:2]) + ("…" if len(suites) > 2 else "") if suites else "Robot Framework Suite",
            "tests": tests,
            "suites": suites,
            "tags": tags,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total": total,
            "suite_status": "PASS" if failed == 0 and total > 0 else ("FAIL" if total else "N/A"),
            "duration": root_info.get("elapsed"),
            "started": started,
            "ended": ended,
            "robot_version": m.group(1) if m else "",
            "python_version": py.group(1) if py else "",
            "platform": on.group(1).capitalize() if on else "",
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "source": str(xml_path),
        }

    def _parse_test(self, test_el, suite_label: str) -> Dict[str, Any]:
        info = _status_info(test_el.find("status"))
        doc = (test_el.findtext("doc") or "").strip()
        tags = [(t.text or "").strip() for t in test_el.findall("tag")]

        steps = []
        for kw in test_el.findall("kw"):
            kinfo = _status_info(kw.find("status"))
            name = kw.get("name") or "Keyword"
            args = [(a.text or "") for a in kw.findall("arg")]
            if re.search(r"password|passwd|secret|token", name, re.I):
                args = ["••••••" for _ in args]
            error = ""
            if kinfo["status"] == "FAIL":
                for msg in kw.iter("msg"):
                    if msg.get("level") in ("FAIL", "ERROR"):
                        error = (msg.text or "").strip()
                        break
            steps.append({
                "type": (kw.get("type") or "").upper(),
                "name": name,
                "owner": kw.get("owner") or "",
                "args": args,
                "status": kinfo["status"],
                "elapsed": kinfo["elapsed"],
                "error": error[:320],
            })

        return {
            "id": test_el.get("id") or "",
            "name": test_el.get("name") or "Unnamed Test",
            "suite": suite_label,
            "doc": doc,
            "tags": tags,
            "status": info["status"],
            "message": info["text"][:400],
            "elapsed": info["elapsed"],
            "start": info["start"],
            "steps": steps,
        }

    # ---------------------------------------------------------------- layout
    def build_pdf(self, meta: Dict[str, Any], job_label: str = "latest") -> bytes:
        buffer = BytesIO()
        footer_meta = {"label": job_label, "suite": meta["suite_name"], "generated": meta["generated_at"]}

        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=MARGIN_X, rightMargin=MARGIN_X,
            topMargin=RUN_H + 9 * mm, bottomMargin=20 * mm,
            title=f"KPIT Test Report - {job_label}",
            author="KPIT Auth Platform",
            subject="Automated test execution report",
        )

        st = self._styles()
        story: List[Any] = [Spacer(1, BAND_H - RUN_H - 9 * mm + 9 * mm)]

        total, passed, failed, skipped = meta["total"], meta["passed"], meta["failed"], meta["skipped"]
        rate = (passed / total * 100) if total else 0.0

        # ---- verdict banner
        story.append(self._verdict(meta, rate, st))
        story.append(Spacer(1, 5 * mm))

        # ---- KPI cards
        story.append(self._kpi_cards(meta, rate, st))
        story.append(Spacer(1, 6 * mm))

        # ---- donut + run information side by side
        story.append(self._donut_and_info(meta, rate, st))
        story.append(Spacer(1, 4 * mm))

        # ---- suites
        if meta["suites"]:
            story.append(Paragraph("Suites", st["h2"]))
            story.append(self._suite_table(meta, st))

        # ---- tags
        if meta["tags"]:
            story.append(Paragraph("Tags", st["h2"]))
            story.append(self._tag_table(meta, st))

        # ---- failures at a glance
        failures = [t for t in meta["tests"] if t["status"] not in ("PASS", "SKIP")]
        if failures:
            story.append(PageBreak())
            story.append(Paragraph("Failures at a glance", st["h2_first"]))
            for t in failures:
                story.append(self._failure_card(t, st))
                story.append(Spacer(1, 3 * mm))
            story.append(Spacer(1, 2 * mm))

        # ---- results + durations
        story.append(CondPageBreak(70 * mm) if failures else PageBreak())
        story.append(Paragraph("Test case results", st["h2_first"] if not failures else st["h2"]))
        story.append(self._results_table(meta, st))

        timed = [t for t in meta["tests"] if t["elapsed"] is not None]
        if len(timed) > 1:
            story.append(Paragraph("Slowest tests", st["h2"]))
            story.append(self._duration_chart(timed))

        # ---- details
        story.append(PageBreak())
        story.append(Paragraph("Test details", st["h2_first"]))
        for idx, t in enumerate(meta["tests"], start=1):
            story.extend(self._test_detail(idx, t, st))

        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(
            "This report was generated automatically from the Robot Framework execution output. "
            "Passwords and secrets passed to keywords are masked.", st["note"]))

        doc.build(story, canvasmaker=lambda *a, **k: _NumberedCanvas(*a, footer_meta=footer_meta, **k))
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    # ---------------------------------------------------------------- styles
    def _styles(self) -> Dict[str, ParagraphStyle]:
        def ps(name, **kw):
            kw.setdefault("fontName", "Helvetica")
            kw.setdefault("textColor", INK)
            return ParagraphStyle(name, **kw)

        return {
            "body": ps("body", fontSize=9, leading=12.5),
            "small": ps("small", fontSize=8, leading=10.5, textColor=MUTED),
            "cell": ps("cell", fontSize=8.2, leading=10.6),
            "cell_b": ps("cell_b", fontSize=8.2, leading=10.6, fontName="Helvetica-Bold"),
            "cell_mono": ps("cell_mono", fontSize=7.6, leading=10, fontName="Courier", textColor=colors.HexColor("#3b4030")),
            "th": ps("th", fontSize=7.4, leading=9.5, fontName="Helvetica-Bold", textColor=colors.HexColor("#c9cdbd")),
            "h2": ps("h2", fontSize=13, leading=16, fontName="Helvetica-Bold", spaceBefore=10 * mm / 2, spaceAfter=3 * mm),
            "h2_first": ps("h2f", fontSize=13, leading=16, fontName="Helvetica-Bold", spaceBefore=0, spaceAfter=3 * mm),
            "note": ps("note", fontSize=7.8, leading=10.5, textColor=FAINT),
            "kpi_val": ps("kv", fontSize=22, leading=24, fontName="Helvetica-Bold", alignment=TA_LEFT),
            "kpi_lbl": ps("kl", fontSize=7.4, leading=9, fontName="Helvetica-Bold", textColor=MUTED, alignment=TA_LEFT),
        }

    # ---------------------------------------------------------------- blocks
    def _verdict(self, meta, rate, st):
        ok = meta["suite_status"] == "PASS"
        none = meta["suite_status"] == "N/A"
        fg = LIME if ok else (AMBER if none else RED)
        title = "ALL TESTS PASSED" if ok else ("NO TESTS EXECUTED" if none else f"{meta['failed']} TEST{'S' if meta['failed'] != 1 else ''} FAILED")
        sub = (f"{meta['passed']} of {meta['total']} test{'s' if meta['total'] != 1 else ''} passed in {_fmt_dur(meta['duration'])}"
               if not none else "The output file contains no test cases.")
        t = Table([[
            Paragraph(f'<font color="{fg.hexval().replace("0x", "#")}" size="15"><b>{title}</b></font>', st["body"]),
            Paragraph(f'<para align="right"><font color="#c9cdbd" size="9">{_esc(sub)}</font></para>', st["body"]),
        ]], colWidths=[CONTENT_W * 0.5, CONTENT_W * 0.5])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BLACK),
            ("LINEBEFORE", (0, 0), (0, 0), 3, fg),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 11), ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
            ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ]))
        return t

    def _kpi_cards(self, meta, rate, st):
        def card(value, label, color, bg):
            return [
                Paragraph(f'<font color="{color}">{value}</font>', st["kpi_val"]),
                Paragraph(label, st["kpi_lbl"]),
            ], bg

        hexs = lambda c: c.hexval().replace("0x", "#")
        specs = [
            card(meta["total"], "TOTAL TESTS", hexs(INK), PAPER),
            card(meta["passed"], "PASSED", hexs(GREEN), GREEN_BG),
            card(meta["failed"], "FAILED", hexs(RED if meta["failed"] else MUTED), RED_BG if meta["failed"] else PAPER),
            card(meta["skipped"], "SKIPPED", hexs(AMBER if meta["skipped"] else MUTED), AMBER_BG if meta["skipped"] else PAPER),
            card(f"{rate:.0f}%" if meta["total"] else "n/a", "PASS RATE", hexs(LIME_DEEP), LIME_SOFT),
            card(_fmt_dur(meta["duration"]), "DURATION", hexs(INK), PAPER),
        ]
        gap = 2.5 * mm
        w = (CONTENT_W - gap * 5) / 6
        row, widths = [], []
        for i, (cell, _) in enumerate(specs):
            inner = Table([[cell[0]], [cell[1]]], colWidths=[w])
            inner.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (0, 0), 10), ("BOTTOMPADDING", (0, 0), (0, 0), 1),
                ("TOPPADDING", (0, 1), (0, 1), 0), ("BOTTOMPADDING", (0, 1), (0, 1), 9),
            ]))
            row.append(inner)
            widths.append(w)
            if i < len(specs) - 1:
                row.append("")
                widths.append(gap)
        t = Table([row], colWidths=widths)
        cmds = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]
        for i, (_, bg) in enumerate(specs):
            col = i * 2
            cmds += [("BACKGROUND", (col, 0), (col, 0), bg), ("BOX", (col, 0), (col, 0), 0.5, BORDER)]
        t.setStyle(TableStyle(cmds))
        return t

    def _donut(self, meta, rate, size=46 * mm):
        d = Drawing(size, size)
        cx = cy = size / 2
        r_out, r_in = size / 2 - 1, size / 2 - 11
        parts = [(meta["passed"], GREEN), (meta["failed"], RED), (meta["skipped"], AMBER)]
        parts = [(v, c) for v, c in parts if v > 0]
        total = sum(v for v, _ in parts)
        if total == 0:
            d.add(Circle(cx, cy, r_out, fillColor=BORDER, strokeColor=None))
        elif len(parts) == 1:
            d.add(Circle(cx, cy, r_out, fillColor=parts[0][1], strokeColor=None))
        else:
            angle = 90.0
            for v, c in parts:
                sweep = 360.0 * v / total
                d.add(Wedge(cx, cy, r_out, angle - sweep, angle, strokeColor=colors.white, strokeWidth=1.2, fillColor=c))
                angle -= sweep
        d.add(Circle(cx, cy, r_in, fillColor=colors.white, strokeColor=None))
        d.add(String(cx, cy - 2, f"{rate:.0f}%" if meta["total"] else "n/a", textAnchor="middle",
                     fontName="Helvetica-Bold", fontSize=17, fillColor=INK))
        d.add(String(cx, cy - 13, "PASS RATE", textAnchor="middle", fontName="Helvetica-Bold", fontSize=6.5, fillColor=MUTED))
        return d

    def _donut_and_info(self, meta, rate, st):
        def row(label, value):
            return [Paragraph(label, st["small"]), Paragraph(_esc(value) or "—", st["cell_b"])]

        fmt = lambda dt: dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "—"
        env = " · ".join(x for x in [
            f"Robot Framework {meta['robot_version']}" if meta["robot_version"] else "",
            f"Python {meta['python_version']}" if meta["python_version"] else "",
            meta["platform"]] if x) or "—"
        rows = [
            row("Started", fmt(meta["started"])),
            row("Finished", fmt(meta["ended"])),
            row("Duration", _fmt_dur(meta["duration"])),
            row("Suites executed", str(len(meta["suites"]))),
            row("Environment", env),
        ]
        info = Table(rows, colWidths=[28 * mm, CONTENT_W - 46 * mm - 28 * mm - 8 * mm])
        info.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ]))
        outer = Table([[self._donut(meta, rate), info]], colWidths=[52 * mm, CONTENT_W - 52 * mm])
        outer.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        return outer

    def _header_row(self, labels, st):
        return [Paragraph(l, st["th"]) for l in labels]

    def _base_table_style(self, header=True):
        cmds = [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, BORDER),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ]
        if header:
            cmds += [("BACKGROUND", (0, 0), (-1, 0), BLACK), ("LINEBELOW", (0, 0), (-1, 0), 1.2, LIME)]
        return cmds

    def _pill(self, status, st):
        colr, bg = {"PASS": (GREEN, GREEN_BG), "SKIP": (AMBER, AMBER_BG)}.get(status, (RED, RED_BG))
        return Paragraph(f'<font color="{colr.hexval().replace("0x", "#")}"><b>{status}</b></font>', st["cell"]), bg

    def _suite_table(self, meta, st):
        rows = [self._header_row(["SUITE", "TESTS", "PASSED", "FAILED", "DURATION", "PASS RATE"], st)]
        for s in meta["suites"]:
            r = (s["passed"] / s["total"] * 100) if s["total"] else 0
            rows.append([
                Paragraph(_esc(s["name"]), st["cell_b"]), Paragraph(str(s["total"]), st["cell"]),
                Paragraph(f'<font color="#15803d">{s["passed"]}</font>', st["cell"]),
                Paragraph(f'<font color="{"#dc2626" if s["failed"] else "#9aa08c"}">{s["failed"]}</font>', st["cell"]),
                Paragraph(_fmt_dur(s["elapsed"]), st["cell"]),
                self._rate_bar(r),
            ])
        t = Table(rows, colWidths=[CONTENT_W * 0.34, CONTENT_W * 0.1, CONTENT_W * 0.1, CONTENT_W * 0.1, CONTENT_W * 0.14, CONTENT_W * 0.22], repeatRows=1)
        t.setStyle(TableStyle(self._base_table_style() + [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER])]))
        return t

    def _rate_bar(self, pct, w=34 * mm, h=3.2 * mm):
        d = Drawing(w, h + 1)
        bar_w = w - 12 * mm
        d.add(Rect(0, 1, bar_w, h, rx=h / 2, ry=h / 2, fillColor=BORDER, strokeColor=None))
        if pct > 0:
            d.add(Rect(0, 1, max(bar_w * pct / 100, h), h, rx=h / 2, ry=h / 2,
                       fillColor=GREEN if pct >= 100 else (AMBER if pct >= 50 else RED), strokeColor=None))
        d.add(String(bar_w + 3, 1.6, f"{pct:.0f}%", fontName="Helvetica-Bold", fontSize=7.5, fillColor=INK))
        return d

    def _tag_table(self, meta, st):
        rows = [self._header_row(["TAG", "PASSED", "FAILED", "TOTAL"], st)]
        for tg in meta["tags"][:12]:
            rows.append([
                Paragraph(_esc(tg["name"]), st["cell_b"]),
                Paragraph(f'<font color="#15803d">{tg["passed"]}</font>', st["cell"]),
                Paragraph(f'<font color="{"#dc2626" if tg["failed"] else "#9aa08c"}">{tg["failed"]}</font>', st["cell"]),
                Paragraph(str(tg["passed"] + tg["failed"]), st["cell"]),
            ])
        t = Table(rows, colWidths=[CONTENT_W * 0.46, CONTENT_W * 0.18, CONTENT_W * 0.18, CONTENT_W * 0.18], repeatRows=1)
        t.setStyle(TableStyle(self._base_table_style() + [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER])]))
        return t

    def _failure_card(self, t, st):
        failing = next((s for s in t["steps"] if s["status"] == "FAIL"), None)
        body = [
            [Paragraph(f'<b>{_esc(t["name"])}</b>', st["body"]),
             Paragraph(f'<para align="right"><font color="#6b7160" size="8">{_esc(t["suite"])}  ·  {_fmt_dur(t["elapsed"])}</font></para>', st["body"])],
        ]
        msg = t["message"] or (failing["error"] if failing else "")
        if failing:
            body.append([Paragraph(f'<font color="#6b7160" size="8">Failed step</font><br/><b>{_esc(failing["name"])}</b>'
                                   f' <font name="Courier" size="7.6">{_esc(", ".join(failing["args"])[:120])}</font>', st["cell"]), ""])
        if msg:
            body.append([Paragraph(f'<font name="Courier" size="7.8" color="#b91c1c">{_esc(msg)}</font>', st["cell"]), ""])
        tbl = Table(body, colWidths=[CONTENT_W * 0.62, CONTENT_W * 0.38 - 0.1])
        cmds = [("BACKGROUND", (0, 0), (-1, -1), RED_BG), ("LINEBEFORE", (0, 0), (0, -1), 3, RED),
                ("LEFTPADDING", (0, 0), (-1, -1), 11), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, 0), 8), ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP")]
        for i in range(1, len(body)):
            cmds.append(("SPAN", (0, i), (1, i)))
        tbl.setStyle(TableStyle(cmds))
        return KeepTogether([tbl])

    def _results_table(self, meta, st):
        rows = [self._header_row(["#", "TEST CASE", "SUITE", "TAGS", "DURATION", "STATUS"], st)]
        bgs = []
        for i, t in enumerate(meta["tests"], start=1):
            pill, bg = self._pill(t["status"], st)
            rows.append([
                Paragraph(str(i), st["cell"]),
                Paragraph(_esc(t["name"]), st["cell_b"]),
                Paragraph(_esc(t["suite"]), st["cell"]),
                Paragraph(_esc(", ".join(t["tags"]) or "—"), st["cell"]),
                Paragraph(_fmt_dur(t["elapsed"]), st["cell"]),
                pill,
            ])
            bgs.append(("BACKGROUND", (5, i), (5, i), bg))
        if len(rows) == 1:
            rows.append([Paragraph("—", st["cell"]), Paragraph("No test cases found in output.xml", st["cell"]),
                         "", "", "", ""])
        cw = [CONTENT_W * x for x in (0.06, 0.34, 0.2, 0.18, 0.11, 0.11)]
        t = Table(rows, colWidths=cw, repeatRows=1)
        t.setStyle(TableStyle(self._base_table_style() + [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PAPER])] + bgs))
        return t

    def _duration_chart(self, timed):
        top = sorted(timed, key=lambda t: t["elapsed"], reverse=True)[:8]
        row_h, label_w = 7 * mm, 62 * mm
        d = Drawing(CONTENT_W, row_h * len(top) + 2 * mm)
        longest = max(t["elapsed"] for t in top) or 1
        bar_max = CONTENT_W - label_w - 22 * mm
        for i, t in enumerate(top):
            y = (len(top) - 1 - i) * row_h + 2 * mm
            name = t["name"] if len(t["name"]) <= 34 else t["name"][:33] + "…"
            d.add(String(0, y + 2.2 * mm, name, fontName="Helvetica", fontSize=8, fillColor=INK))
            d.add(Rect(label_w, y + 1.4 * mm, bar_max, 3.4 * mm, rx=1.7 * mm, ry=1.7 * mm, fillColor=PAPER, strokeColor=None))
            w = max(bar_max * t["elapsed"] / longest, 2 * mm)
            d.add(Rect(label_w, y + 1.4 * mm, w, 3.4 * mm, rx=1.7 * mm, ry=1.7 * mm,
                       fillColor=GREEN if t["status"] == "PASS" else RED, strokeColor=None))
            d.add(String(label_w + bar_max + 3 * mm, y + 2.2 * mm, _fmt_dur(t["elapsed"]),
                         fontName="Helvetica-Bold", fontSize=8, fillColor=MUTED))
        return d

    def _test_detail(self, idx, t, st):
        pill, bg = self._pill(t["status"], st)
        status_col = {"PASS": GREEN, "SKIP": AMBER}.get(t["status"], RED)
        head = Table([[
            Paragraph(f'<font color="#9aa08c">{idx:02d}</font>', st["cell_b"]),
            Paragraph(f'<b>{_esc(t["name"])}</b><br/><font color="#6b7160" size="7.6">{_esc(t["suite"])}'
                      f'{"  ·  " + _esc(", ".join(t["tags"])) if t["tags"] else ""}</font>', st["body"]),
            Paragraph(f'<para align="right"><font color="#6b7160" size="8">{_fmt_dur(t["elapsed"])}</font></para>', st["cell"]),
            pill,
        ]], colWidths=[10 * mm, CONTENT_W - 10 * mm - 24 * mm - 20 * mm, 24 * mm, 20 * mm])
        head.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PAPER), ("BACKGROUND", (3, 0), (3, 0), bg),
            ("LINEBEFORE", (0, 0), (0, 0), 3, status_col),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))

        out: List[Any] = [CondPageBreak(55 * mm), head]
        if t["doc"]:
            out.append(Spacer(1, 1.5 * mm))
            out.append(Paragraph(_esc(t["doc"]), st["small"]))
        if t["status"] not in ("PASS", "SKIP") and t["message"]:
            out.append(Spacer(1, 1.5 * mm))
            out.append(Paragraph(f'<font name="Courier" size="7.8" color="#b91c1c">{_esc(t["message"])}</font>', st["cell"]))

        if t["steps"]:
            rows = [self._header_row(["", "KEYWORD", "ARGUMENTS", "TIME", "RESULT"], st)]
            bgs = []
            for i, s in enumerate(t["steps"], start=1):
                tag = {"SETUP": "setup", "TEARDOWN": "teardown"}.get(s["type"], "")
                label = f'<b>{_esc(s["name"])}</b>'
                if s["owner"]:
                    label += f'<br/><font color="#9aa08c" size="7">{_esc(s["owner"])}{"  ·  " + tag if tag else ""}</font>'
                elif tag:
                    label += f'<br/><font color="#9aa08c" size="7">{tag}</font>'
                args = _esc(" | ".join(s["args"]))[:150] or "—"
                step_pill, step_bg = self._pill(s["status"], st)
                rows.append([
                    Paragraph(f'<font color="#9aa08c">{i}</font>', st["cell"]),
                    Paragraph(label, st["cell"]),
                    Paragraph(args, st["cell_mono"]),
                    Paragraph(_fmt_dur(s["elapsed"]), st["cell"]),
                    step_pill,
                ])
                if s["error"]:
                    rows.append(["", Paragraph(f'<font name="Courier" size="7.4" color="#b91c1c">{_esc(s["error"])}</font>', st["cell"]), "", "", ""])
                    r = len(rows) - 1
                    bgs += [("SPAN", (1, r), (4, r)), ("BACKGROUND", (0, r), (-1, r), RED_BG)]
            cw = [CONTENT_W * x for x in (0.05, 0.31, 0.38, 0.11, 0.15)]
            tbl = Table(rows, colWidths=cw, repeatRows=1)
            tbl.setStyle(TableStyle(self._base_table_style() + bgs + [
                ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5)]))
            out.append(Spacer(1, 2 * mm))
            out.append(tbl)
        out.append(Spacer(1, 7 * mm))
        return out

    # ---------------------------------------------------------------- entry
    def generate_from_folder(self, results_root: Path, folder: str) -> bytes:
        if folder == "latest":
            xml_path = results_root / "output.xml"
            label = "latest"
        else:
            xml_path = results_root / folder / "output.xml"
            label = folder
            if not xml_path.exists():
                # fallback: root output if subfolder has only report.html
                alt = results_root / "output.xml"
                if alt.exists():
                    xml_path = alt
                    label = f"{folder} (root output.xml)"
        meta = self.parse_output_xml(xml_path)
        return self.build_pdf(meta, job_label=label)


pdf_report_service = PdfReportService()
