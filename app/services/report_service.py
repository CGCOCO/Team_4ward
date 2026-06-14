from __future__ import annotations

import re
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
)

from app.services.storage_service import download_analysis_image


KOREAN_FONT = "HYGothic-Medium"
PRIMARY = colors.HexColor("#1d4ed8")
DARK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
BORDER = colors.HexColor("#dbe3ef")
SOFT_BLUE = colors.HexColor("#eff6ff")
SOFT_SLATE = colors.HexColor("#f8fafc")


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
            fontSize=22,
            leading=28,
            alignment=TA_LEFT,
            textColor=DARK,
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "KoreanSubtitle",
            parent=base["BodyText"],
            fontName=KOREAN_FONT,
            fontSize=9,
            leading=13,
            textColor=MUTED,
            wordWrap="CJK",
        ),
        "section": ParagraphStyle(
            "KoreanSection",
            parent=base["Heading2"],
            fontName=KOREAN_FONT,
            fontSize=12,
            leading=18,
            textColor=DARK,
            spaceBefore=12,
            spaceAfter=6,
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
        "label": ParagraphStyle(
            "KoreanLabel",
            parent=base["BodyText"],
            fontName=KOREAN_FONT,
            fontSize=8,
            leading=11,
            textColor=PRIMARY,
            wordWrap="CJK",
        ),
        "lawTitle": ParagraphStyle(
            "KoreanLawTitle",
            parent=base["BodyText"],
            fontName=KOREAN_FONT,
            fontSize=10,
            leading=14,
            textColor=DARK,
            wordWrap="CJK",
        ),
        "lawSubtitle": ParagraphStyle(
            "KoreanLawSubtitle",
            parent=base["BodyText"],
            fontName=KOREAN_FONT,
            fontSize=9,
            leading=12,
            textColor=MUTED,
            wordWrap="CJK",
        ),
    }


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def _clean_text(value) -> str:
    return str(value or "").strip()


def _section_title(title: str, styles: dict[str, ParagraphStyle]) -> list:
    return [
        Spacer(1, 4),
        Paragraph(title, styles["section"]),
        HRFlowable(width="100%", thickness=0.7, color=BORDER, spaceAfter=6),
    ]


def _list_section(title: str, items: list, styles: dict[str, ParagraphStyle]) -> list:
    story = _section_title(title, styles)
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
                bulletColor=PRIMARY,
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
            bulletColor=PRIMARY,
        )
    )
    return story


def _format_law(article: str, content: str) -> tuple[str, str]:
    article_text = _clean_text(article)
    content_text = _clean_text(content)
    article_match = re.match(
        r"^(?:산업안전보건(?:기준에 관한 )?규칙\s*)?(제\s*\d+조)(?:\(([^)]+)\))?",
        article_text,
    )
    content_title_match = re.match(r"^제\s*\d+조\(([^)]+)\)", content_text)

    if not article_match:
        return article_text, content_title_match.group(1) if content_title_match else ""

    article_number = article_match.group(1).replace(" ", "")
    subtitle = article_match.group(2) or (content_title_match.group(1) if content_title_match else "")
    return f"산업안전보건규칙 {article_number}", subtitle


def _law_section(related_laws: list, styles: dict[str, ParagraphStyle]) -> list:
    story = _section_title("관련 법규", styles)
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

        title, subtitle = _format_law(article, content)
        law_rows = [[Paragraph(escape(title), styles["lawTitle"])]]
        if subtitle:
            law_rows.append([Paragraph(escape(subtitle), styles["lawSubtitle"])])
        if content:
            law_rows.append([Paragraph(escape(content), styles["meta"])])

        story.append(
            KeepTogether(
                [
                    Table(
                        law_rows,
                        colWidths=[156 * mm],
                        style=[
                            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                            ("LEFTPADDING", (0, 0), (-1, -1), 10),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                            ("TOPPADDING", (0, 0), (-1, -1), 7),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                        ],
                    ),
                    Spacer(1, 6),
                ]
            )
        )

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


def _page_style(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(PRIMARY)
    canvas.rect(0, height - 9 * mm, width, 9 * mm, stroke=0, fill=1)
    canvas.setFillColor(MUTED)
    canvas.setFont(KOREAN_FONT, 8)
    canvas.drawString(18 * mm, 10 * mm, "AI Safety Inspection Report")
    canvas.drawRightString(width - 18 * mm, 10 * mm, f"{doc.page}")
    canvas.restoreState()


def _summary_card(analysis: dict, styles: dict[str, ParagraphStyle], doc_width: float) -> Table:
    rows = [
        [
            Paragraph("분석 번호", styles["label"]),
            Paragraph(str(analysis["id"]), styles["body"]),
            Paragraph("분석 일시", styles["label"]),
            Paragraph(analysis.get("created_at") or "-", styles["body"]),
        ],
        [
            Paragraph("이미지 저장", styles["label"]),
            Paragraph("마스킹 이미지 포함" if analysis.get("image_url") else "-", styles["body"]),
            Paragraph("생성 방식", styles["label"]),
            Paragraph("AI 분석 결과 기반 자동 생성", styles["body"]),
        ],
    ]
    return Table(
        rows,
        colWidths=[25 * mm, 50 * mm, 25 * mm, doc_width - 100 * mm],
        style=[
            ("BACKGROUND", (0, 0), (-1, -1), SOFT_SLATE),
            ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ],
    )


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
        Paragraph(
            "업로드된 현장 이미지와 AI 분석 결과를 기반으로 주요 위험요소, 사고 가능성, 예방대책 및 관련 법규를 정리한 문서입니다.",
            styles["subtitle"],
        ),
        Spacer(1, 10),
        _summary_card(analysis, styles, doc.width),
        Spacer(1, 8),
    ]

    image = _image_flowable(analysis.get("image_url"), doc.width)
    if image is not None:
        story.extend(_section_title("분석 이미지", styles))
        story.append(
            Table(
                [[image]],
                colWidths=[doc.width],
                style=[
                    ("BACKGROUND", (0, 0), (-1, -1), SOFT_BLUE),
                    ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ],
            )
        )
        story.append(Spacer(1, 8))

    story.extend(_list_section("주요 위험요소", hazards, styles))
    story.extend(_list_section("발생 가능한 아차사고", accidents, styles))
    story.extend(_list_section("예방대책", preventions, styles))
    story.extend(_law_section(related_laws, styles))

    doc.build(story, onFirstPage=_page_style, onLaterPages=_page_style)
    return buffer.getvalue()
