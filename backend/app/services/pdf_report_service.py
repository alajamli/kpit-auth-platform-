"""
KPIT professional PDF report generator from Robot Framework output.xml.
VEX-oriented layout: indigo header, clear stats, test table.
"""
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)

# VEX palette
INDIGO = colors.HexColor("#3730a3")
SLATE = colors.HexColor("#1e293b")
MUTED = colors.HexColor("#64748b")
BORDER = colors.HexColor("#e2e8f0")
PASS_BG = colors.HexColor("#ecfdf5")
PASS_FG = colors.HexColor("#047857")
FAIL_BG = colors.HexColor("#fef2f2")
FAIL_FG = colors.HexColor("#b91c1c")
HEADER_BG = colors.HexColor("#f8fafc")


class PdfReportService:
    """Builds a clean multi-page PDF from Robot Framework output.xml."""

    def parse_output_xml(self, xml_path: Path) -> Dict[str, Any]:
        if not xml_path.exists():
            raise FileNotFoundError(f"output.xml not found: {xml_path}")

        tree = ET.parse(xml_path)
        root = tree.getroot()

        suite_name = "Robot Framework Suite"
        suite_el = root.find(".//suite")
        if suite_el is not None and suite_el.get("name"):
            suite_name = suite_el.get("name")

        tests: List[Dict[str, str]] = []
        for test_el in root.findall(".//test"):
            name = test_el.get("name") or "Unnamed Test"
            status_el = test_el.find("status")
            status = (status_el.get("status") if status_el is not None else "FAIL") or "FAIL"
            message = ""
            if status_el is not None and status_el.text:
                message = status_el.text.strip()
            # duration if present
            start = status_el.get("starttime") if status_el is not None else ""
            end = status_el.get("endtime") if status_el is not None else ""
            tests.append({
                "name": name,
                "status": status.upper(),
                "message": message[:180],
                "start": start or "",
                "end": end or "",
            })

        passed = sum(1 for t in tests if t["status"] == "PASS")
        failed = sum(1 for t in tests if t["status"] != "PASS")
        total = len(tests)

        # suite-level status
        suite_status = "PASS" if failed == 0 and total > 0 else ("FAIL" if total else "N/A")

        return {
            "suite_name": suite_name,
            "tests": tests,
            "passed": passed,
            "failed": failed,
            "total": total,
            "suite_status": suite_status,
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "source": str(xml_path),
        }

    def build_pdf(self, meta: Dict[str, Any], job_label: str = "latest") -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
            title=f"KPIT Test Report - {job_label}",
            author="KPIT Auth Platform",
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "KpitTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=INDIGO,
            spaceAfter=4,
            alignment=TA_LEFT,
            fontName="Helvetica-Bold",
        )
        subtitle_style = ParagraphStyle(
            "KpitSub",
            parent=styles["Normal"],
            fontSize=10,
            textColor=MUTED,
            spaceAfter=12,
        )
        section_style = ParagraphStyle(
            "KpitSection",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=SLATE,
            spaceBefore=14,
            spaceAfter=8,
            fontName="Helvetica-Bold",
        )
        body_style = ParagraphStyle(
            "KpitBody",
            parent=styles["Normal"],
            fontSize=9,
            textColor=SLATE,
            leading=12,
        )
        small_style = ParagraphStyle(
            "KpitSmall",
            parent=styles["Normal"],
            fontSize=8,
            textColor=MUTED,
        )
        cell_style = ParagraphStyle(
            "KpitCell",
            parent=styles["Normal"],
            fontSize=8,
            textColor=SLATE,
            leading=10,
        )

        story = []

        # Header
        story.append(Paragraph("KPIT Auth Platform", title_style))
        story.append(Paragraph(
            "AI-Enhanced Test Automation Report · Robot Framework",
            subtitle_style
        ))
        story.append(HRFlowable(width="100%", thickness=1.5, color=INDIGO, spaceAfter=12))

        # Meta block
        meta_data = [
            [Paragraph("<b>Suite</b>", body_style), Paragraph(meta["suite_name"], body_style)],
            [Paragraph("<b>Job / Folder</b>", body_style), Paragraph(str(job_label), body_style)],
            [Paragraph("<b>Generated</b>", body_style), Paragraph(meta["generated_at"], body_style)],
            [Paragraph("<b>Overall status</b>", body_style), Paragraph(
                f'<font color="{"#047857" if meta["suite_status"]=="PASS" else "#b91c1c"}"><b>{meta["suite_status"]}</b></font>',
                body_style
            )],
        ]
        meta_table = Table(meta_data, colWidths=[40 * mm, 130 * mm])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HEADER_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 14))

        # KPI cards (as a 3-col table)
        story.append(Paragraph("Execution summary", section_style))
        total, passed, failed = meta["total"], meta["passed"], meta["failed"]
        rate = f"{(passed / total * 100):.1f}%" if total else "n/a"

        kpi = [
            [
                Paragraph(f"<para align='center'><b><font size='16'>{total}</font></b><br/><font color='#64748b' size='8'>TOTAL</font></para>", body_style),
                Paragraph(f"<para align='center'><b><font size='16' color='#047857'>{passed}</font></b><br/><font color='#64748b' size='8'>PASSED</font></para>", body_style),
                Paragraph(f"<para align='center'><b><font size='16' color='#b91c1c'>{failed}</font></b><br/><font color='#64748b' size='8'>FAILED</font></para>", body_style),
                Paragraph(f"<para align='center'><b><font size='16' color='#3730a3'>{rate}</font></b><br/><font color='#64748b' size='8'>PASS RATE</font></para>", body_style),
            ]
        ]
        kpi_table = Table(kpi, colWidths=[42 * mm, 42 * mm, 42 * mm, 42 * mm])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), HEADER_BG),
            ("BACKGROUND", (1, 0), (1, 0), PASS_BG),
            ("BACKGROUND", (2, 0), (2, 0), FAIL_BG),
            ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#eef2ff")),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 16))

        # Tests table
        story.append(Paragraph("Test case results", section_style))

        header = [
            Paragraph("<b>#</b>", cell_style),
            Paragraph("<b>Test case</b>", cell_style),
            Paragraph("<b>Status</b>", cell_style),
            Paragraph("<b>Message</b>", cell_style),
        ]
        rows = [header]
        for idx, t in enumerate(meta["tests"], start=1):
            st = t["status"]
            st_color = "#047857" if st == "PASS" else "#b91c1c"
            rows.append([
                Paragraph(str(idx), cell_style),
                Paragraph(t["name"].replace("&", "&amp;"), cell_style),
                Paragraph(f'<font color="{st_color}"><b>{st}</b></font>', cell_style),
                Paragraph((t["message"] or "—").replace("&", "&amp;"), cell_style),
            ])

        if len(rows) == 1:
            rows.append([
                Paragraph("—", cell_style),
                Paragraph("No test cases found in output.xml", cell_style),
                Paragraph("—", cell_style),
                Paragraph("—", cell_style),
            ])

        col_w = [12 * mm, 70 * mm, 22 * mm, 66 * mm]
        tests_table = Table(rows, colWidths=col_w, repeatRows=1)
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), INDIGO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HEADER_BG]),
        ]
        tests_table.setStyle(TableStyle(style_cmds))
        # fix header text color for Paragraph children: redraw header cells white via background only
        story.append(tests_table)

        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))
        story.append(Paragraph(
            "Generated by KPIT Auth Platform · Confidential · For evaluation / PFA demonstration use",
            small_style
        ))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

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