from __future__ import annotations

from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    Image,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.storage_service import download_analysis_image


KOREAN_FONT = "HYSMyeongJo-Medium"


def _register_fonts() -> None:
    if KOREAN_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(KOREAN_FONT))


def _styles() -> dict[str, ParagraphStyle]:
    _register_fonts()
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "KoreanTitle",
            parent=base["Title"],
            fontName=KOREAN_FONT,
            fontSize=20,
            leading=26,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "KoreanSection",
            parent=base["Heading2"],
            fontName=KOREAN_FONT,
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=10,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "KoreanBody",
            parent=base["BodyText"],
            fontName=KOREAN_FONT,
            fontSize=10,
            leading=15,
            wordWrap="CJK",
        ),
        "meta": ParagraphStyle(
            "KoreanMeta",
            parent=base["BodyText"],
            fontName=KOREAN_FONT,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#475569"),
            wordWrap="CJK",
        ),
    }


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def _list_section(title: str, items: list, styles: dict[str, ParagraphStyle]) -> list:
    story = [Paragraph(title, styles["section"])]
    if not items:
        story.append(Paragraph("항목이 없습니다.", styles["meta"]))
        return story

    flowables = []
    for item in items:
        text = item if isinstance(item, str) else str(item)
        flowables.append(
            ListItem(
                Paragraph(escape(text), styles["body"]),
                leftIndent=8,
            )
        )

    story.append(
        ListFlowable(
            flowables,
            bulletType="1",
            start="1",
            leftIndent=16,
            bulletFontName=KOREAN_FONT,
            bulletFontSize=9,
        )
    )
    return story


def _law_section(related_laws: list, styles: dict[str, ParagraphStyle]) -> list:
    story = [Paragraph("관련 법령", styles["section"])]
    if not related_laws:
        story.append(Paragraph("항목이 없습니다.", styles["meta"]))
        return story

    for index, law in enumerate(related_laws, start=1):
        if isinstance(law, str):
            article = law
            content = ""
        else:
            article = law.get("article") or law.get("title") or f"관련 법령 {index}"
            content = law.get("content") or law.get("description") or ""

        story.append(Paragraph(f"{index}. {escape(article)}", styles["body"]))
        if content:
            story.append(Paragraph(escape(content), styles["meta"]))
        story.append(Spacer(1, 4))

    return story


def _image_flowable(image_url: str | None, max_width: float) -> Image | None:
    if not image_url:
        return None

    image_bytes, _ = download_analysis_image(image_url)
    image = Image(BytesIO(image_bytes))
    ratio = image.imageHeight / image.imageWidth
    image.drawWidth = max_width
    image.drawHeight = max_width * ratio
    if image.drawHeight > 90 * mm:
        image.drawHeight = 90 * mm
        image.drawWidth = image.drawHeight / ratio
    return image


def create_analysis_report_pdf(analysis: dict) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="AI 안전 점검 리포트",
    )

    ai_result = analysis["ai_result"]
    hazards = _as_list(ai_result.get("hazards") or ai_result.get("detected_risks"))
    accidents = _as_list(ai_result.get("accidents"))
    preventions = [
        *_as_list(ai_result.get("safety_measures")),
        *_as_list(ai_result.get("preventions")),
    ]
    related_laws = _as_list(ai_result.get("related_laws"))

    story = [
        Paragraph("AI 안전 점검 리포트", styles["title"]),
        Table(
            [
                ["분석 번호", str(analysis["id"])],
                ["분석 일시", analysis.get("created_at") or "-"],
            ],
            colWidths=[32 * mm, 120 * mm],
            style=[
                ("FONTNAME", (0, 0), (-1, -1), KOREAN_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eff6ff")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1d4ed8")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ],
        ),
        Spacer(1, 10),
    ]

    image = _image_flowable(analysis.get("image_url"), doc.width)
    if image is not None:
        story.extend([
            Paragraph("분석 이미지", styles["section"]),
            image,
            Spacer(1, 8),
        ])

    story.extend(_list_section("주요 위험요소", hazards, styles))
    story.extend(_list_section("발생 가능한 아차사고", accidents, styles))
    story.extend(_list_section("예방대책", preventions, styles))
    story.extend(_law_section(related_laws, styles))

    doc.build(story)
    return buffer.getvalue()
