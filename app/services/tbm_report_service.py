"""TBM(Tool Box Meeting) 회의록 PDF 생성.

1페이지: 고용노동부·안전보건공단「작업 전 안전점검회의(TBM) 가이드」(2023.2.)
         <서식 2> Tool Box Meeting 회의록 양식을 그대로 재현하고,
         AI 분석 결과로 채울 수 있는 칸만 미리 채운다.
         (일시·장소·리더·참석자 등 현장 정보는 출력 후 수기 작성)
2페이지~: AI 위험성 분석 참고자료 (중점위험, 아차사고, 예방대책, 관련 법규, SLAM 행동요령)

AI 결과에 TBM 전용 필드(tbm_risks, key_risk 등)가 있으면 그것을 쓰고,
없는 기존 결과(hazards/preventions만 있는 경우)는 후처리로 짝을 맞춘다.
"""

from __future__ import annotations

import re
from html import escape
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepInFrame,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.storage_service import download_analysis_image


# =====================================================
# 폰트 (PDF에 임베드 → 뷰어와 무관하게 한글 표시)
# =====================================================

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT = "NanumGothic"
FONT_BOLD = "NanumGothicBold"


def _register_fonts() -> None:
    registered = pdfmetrics.getRegisteredFontNames()
    if FONT not in registered:
        pdfmetrics.registerFont(TTFont(FONT, str(FONT_DIR / "NanumGothic.ttf")))
    if FONT_BOLD not in registered:
        pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONT_DIR / "NanumGothicBold.ttf")))
    pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT_BOLD)


# =====================================================
# 공통 상수
# =====================================================

PAGE_W, PAGE_H = A4
MARGIN_X = 16 * mm
MARGIN_TOP = 14 * mm
MARGIN_BOTTOM = 14 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X

CIRCLED = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨"]
TBM_RISK_COUNT = 3

SOURCE_TEXT = "출처: 고용노동부·안전보건공단「작업 전 안전점검회의(TBM) 가이드」(2023.2.) &lt;서식 2&gt; 기반"

# 1페이지(공식 양식) 색
FORM_LINE = colors.HexColor("#222222")
FORM_INNER = colors.HexColor("#9a9a9a")
FORM_LABEL_BG = colors.HexColor("#f3f3f3")
FORM_NOTE = colors.HexColor("#7a7a7a")
FORM_FILL = colors.HexColor("#1f3a8a")  # AI가 미리 채운 값

# 2페이지(참고자료) 색 — 메인 네이비 1색 + 중점위험 강조용 레드 1색, 나머지는 무채색
INK = colors.HexColor("#0f172a")
SUB = colors.HexColor("#475569")
FAINT = colors.HexColor("#94a3b8")
LINE = colors.HexColor("#d5dbe3")
PRIMARY = colors.HexColor("#1e3a8a")
PRIMARY_LINE = colors.HexColor("#93a5cf")
ACCENT = colors.HexColor("#dc2626")
ACCENT_LINE = colors.HexColor("#f0a3a3")


def _style(name: str, size: float, *, bold: bool = False, color=INK,
           leading: float | None = None, align=TA_LEFT) -> ParagraphStyle:
    return ParagraphStyle(
        name,
        fontName=FONT_BOLD if bold else FONT,
        fontSize=size,
        leading=leading or size * 1.42,
        textColor=color,
        alignment=align,
        wordWrap="CJK",
    )


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    """사용자/AI 텍스트를 escape해서 Paragraph로 만든다."""
    return Paragraph(escape(text), style)


def _pm(markup: str, style: ParagraphStyle) -> Paragraph:
    """이미 안전한 markup(<b>, <font> 등)을 그대로 쓴다."""
    return Paragraph(markup, style)


# =====================================================
# AI 결과 정규화
# =====================================================

def _text(item) -> str:
    if item is None:
        return ""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in ("description", "content", "text", "title", "hazard", "measure", "name"):
            if item.get(key):
                return str(item[key]).strip()
        return ""
    return str(item).strip()


def _texts(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [t for t in (_text(v) for v in value) if t]


def _bigrams(text: str) -> set[str]:
    compact = re.sub(r"[^0-9A-Za-z가-힣]", "", text)
    return {compact[i:i + 2] for i in range(len(compact) - 1)}


def _similarity(a: str, b: str) -> float:
    ga, gb = _bigrams(a), _bigrams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def _pair_measures(hazards: list[str], measures: list[str]) -> list[str]:
    """위험요인마다 가장 겹치는 대책을 하나씩 배정한다 (탐욕적, 중복 없이).

    겹치는 글자가 전혀 없으면 같은 순번의 대책으로 대체한다.
    """
    remaining = list(range(len(measures)))
    paired: list[str] = []
    for index, hazard in enumerate(hazards):
        if not remaining:
            paired.append("")
            continue
        best = max(remaining, key=lambda m: _similarity(hazard, measures[m]))
        if _similarity(hazard, measures[best]) == 0.0:
            best = index if index in remaining else remaining[0]
        remaining.remove(best)
        paired.append(measures[best])
    return paired


def _form_numbers(listed: list[str], pool: list[str]) -> dict[int, int]:
    """회의록에 기재된 항목(listed ①~③)이 pool의 몇 번째 항목에 해당하는지 1:1로 찾는다.

    반환값: {pool 인덱스: 회의록 번호(0부터)}.
    AI가 tbm_risks를 원문과 다른 표현으로 써도 가장 비슷한 원문 항목에 연결된다.
    """
    remaining = list(range(len(pool)))
    mapping: dict[int, int] = {}
    for number, text in enumerate(listed):
        if not remaining or not text:
            continue
        exact = [i for i in remaining if pool[i] == text]
        best = exact[0] if exact else max(remaining, key=lambda i: _similarity(text, pool[i]))
        if exact or _similarity(text, pool[best]) > 0.0:
            mapping[best] = number
            remaining.remove(best)
    return mapping


def build_tbm_data(ai_result: dict) -> dict:
    """AI 결과(dict)를 TBM 회의록에 들어갈 형태로 정리한다."""
    hazards = _texts(ai_result.get("hazards") or ai_result.get("detected_risks"))
    measures = _texts(ai_result.get("preventions")) + _texts(ai_result.get("safety_measures"))
    accidents = _texts(ai_result.get("accidents"))
    laws = ai_result.get("related_laws") if isinstance(ai_result.get("related_laws"), list) else []

    # 1) 프롬프트가 TBM 전용 필드를 준 경우
    risks: list[dict] = []
    for item in ai_result.get("tbm_risks") or []:
        if isinstance(item, dict) and _text(item.get("hazard")):
            risks.append({
                "hazard": _text(item.get("hazard")),
                "measure": _text(item.get("measure")),
            })
    paired_by_ai = bool(risks)

    # 2) 기존 결과: hazards ↔ preventions 후처리 매칭
    if not risks:
        top = hazards[:TBM_RISK_COUNT]
        risks = [
            {"hazard": h, "measure": m}
            for h, m in zip(top, _pair_measures(top, measures))
        ]
    risks = risks[:TBM_RISK_COUNT]

    key_index = 0
    key_measure = ""
    key_reason = ""
    key_risk = ai_result.get("key_risk")
    if isinstance(key_risk, dict):
        try:
            key_index = int(key_risk.get("index", 1)) - 1
        except (TypeError, ValueError):
            key_index = 0
        key_measure = _text(key_risk.get("measure"))
        key_reason = _text(key_risk.get("reason"))
    if not 0 <= key_index < len(risks):
        key_index = 0

    if risks and not key_measure:
        key_measure = risks[key_index]["measure"]

    hazard_form_no = _form_numbers([r["hazard"] for r in risks], hazards)
    measure_form_no = _form_numbers([r["measure"] for r in risks], measures)

    return {
        "work_name": _text(ai_result.get("work_name")),
        "work_content": _text(ai_result.get("work_content")),
        "risks": risks,
        "key_index": key_index if risks else None,
        "key_measure": key_measure,
        "key_reason": key_reason,
        "paired_by_ai": paired_by_ai,
        "hazards": hazards,
        "accidents": accidents,
        "measures": measures,
        "hazard_form_no": hazard_form_no,
        "measure_form_no": measure_form_no,
        "laws": laws,
    }


# =====================================================
# 1페이지: TBM 회의록 (공식 양식 재현)
# =====================================================

class _FormStyles:
    def __init__(self) -> None:
        self.title = _style("f_title", 17, bold=True, align=TA_CENTER, leading=22)
        self.label = _style("f_label", 9, bold=True, align=TA_CENTER, leading=12)
        self.label_left = _style("f_label_l", 9, bold=True, leading=12)
        self.cell = _style("f_cell", 8.6, leading=11.6)
        self.fill = _style("f_fill", 8.6, color=FORM_FILL, leading=11.6)
        self.center = _style("f_center", 8.6, align=TA_CENTER, leading=11.6)
        self.note = _style("f_note", 7.4, color=FORM_NOTE, leading=10)
        self.section = _style("f_section", 9.4, bold=True, leading=12.5)
        self.foot = _style("f_foot", 6.8, color=FORM_NOTE, leading=9)


def _form_table(rows, col_widths, extra=None, row_heights=None) -> Table:
    style = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("BOX", (0, 0), (-1, -1), 0.9, FORM_LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, FORM_INNER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
    ]
    if extra:
        style.extend(extra)
    return Table(rows, colWidths=col_widths, rowHeights=row_heights, style=TableStyle(style))


def _fill_or_blank(value: str, s: _FormStyles) -> Paragraph:
    return _p(value, s.fill) if value else Paragraph("", s.cell)


def _build_form_page(data: dict) -> list:
    s = _FormStyles()
    W = CONTENT_W
    risks = data["risks"]
    story: list = [
        _pm("Tool Box Meeting 회의록", s.title),
        Spacer(1, 5 * mm),
    ]

    # ── 기본 정보 ────────────────────────────────
    label_w = 24 * mm
    story.append(_form_table(
        [
            [
                _p("TBM 일시", s.label),
                _pm(
                    "20&nbsp;&nbsp;&nbsp;&nbsp;년&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;월&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;일"
                    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;~&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;:"
                    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;작업날짜와 동일함 (□예, □아니오)",
                    s.cell,
                ),
                "", "",
            ],
            [_p("작 업 명", s.label), _fill_or_blank(data["work_name"], s), "", ""],
            [_p("작업내용", s.label), _fill_or_blank(data["work_content"], s), "", ""],
            [
                _p("TBM 장소", s.label),
                Paragraph("", s.cell),
                _pm("위험성평가<br/>실시여부", s.label),
                _p("예 □    아니오 □", s.center),
            ],
        ],
        [label_w, W - label_w - 26 * mm - 44 * mm, 26 * mm, 44 * mm],
        extra=[
            ("SPAN", (1, 0), (3, 0)),
            ("SPAN", (1, 1), (3, 1)),
            ("SPAN", (1, 2), (3, 2)),
            ("BACKGROUND", (0, 0), (0, -1), FORM_LABEL_BG),
            ("BACKGROUND", (2, 3), (2, 3), FORM_LABEL_BG),
        ],
        row_heights=[8 * mm, 8 * mm, 11 * mm, 10 * mm],
    ))

    # ── 잠재위험요인 / 대책 ──────────────────────
    half = W / 2
    rows = [[
        _p("잠재위험요인", s.label),
        _pm('대책 <font size="7.4" color="#7a7a7a">(※ 제거 → 대체 → 통제 순서 고려)</font>', s.label),
    ]]
    for i in range(TBM_RISK_COUNT):
        risk = risks[i] if i < len(risks) else {"hazard": "", "measure": ""}
        rows.append([
            _pm(f"{CIRCLED[i]} " + (f'<font color="#1f3a8a">{escape(risk["hazard"])}</font>' if risk["hazard"] else ""), s.cell),
            _pm(f"{CIRCLED[i]} " + (f'<font color="#1f3a8a">{escape(risk["measure"])}</font>' if risk["measure"] else ""), s.cell),
        ])
    story.append(_form_table(
        rows,
        [half, half],
        extra=[
            ("BACKGROUND", (0, 0), (-1, 0), FORM_LABEL_BG),
            ("LINEBELOW", (0, 0), (-1, 0), 0.9, FORM_LINE),
            ("VALIGN", (0, 1), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ],
        row_heights=[7.5 * mm, None, None, None],
    ))

    # ── 중점위험요인 ─────────────────────────────
    key_index = data["key_index"]
    if key_index is not None:
        key_text = f'{CIRCLED[key_index]} <font color="#1f3a8a">{escape(risks[key_index]["hazard"])}</font>'
    else:
        key_text = ""
    story.append(_form_table(
        [
            [
                _pm("중점위험<br/>요인", s.label),
                _p("선정", s.label),
                _pm(
                    '<font size="7.4" color="#7a7a7a">※ 잠재위험요인 ① ~ ③ 중 중요위험 1개를 선정하여 기재함</font>'
                    + (f"<br/>{key_text}" if key_text else ""),
                    s.cell,
                ),
            ],
            [
                "",
                _p("대책", s.label),
                _fill_or_blank(data["key_measure"], s),
            ],
        ],
        [label_w, 18 * mm, W - label_w - 18 * mm],
        extra=[
            ("SPAN", (0, 0), (0, 1)),
            ("BACKGROUND", (0, 0), (1, -1), FORM_LABEL_BG),
        ],
        row_heights=[13 * mm, 11 * mm],
    ))

    # ── TBM 리더 확인 ───────────────────────────
    gap = "&nbsp;" * 22
    story.append(_form_table(
        [[
            _p("TBM 리더 확인", s.label),
            _pm(f"• 소속 :{gap}• 직책 :{gap}• 성명{gap}&nbsp;&nbsp;&nbsp;&nbsp;(서명)", s.cell),
        ]],
        [label_w + 18 * mm, W - label_w - 18 * mm],
        extra=[("BACKGROUND", (0, 0), (0, 0), FORM_LABEL_BG)],
        row_heights=[8.5 * mm],
    ))

    # ── 작업 전 안전조치 확인 ───────────────────
    c1, c2 = 92 * mm, 30 * mm
    rows = [
        [_pm('■ 작업 전 안전조치 확인 <font name="NanumGothic" size="7.4" color="#7a7a7a">'
             '※ 위 잠재위험요인(중점위험 포함) 안전조치 여부 재확인</font>', s.section), "", ""],
        [_p("잠재위험요소(중점위험 포함)", s.label), _p("조 치 여 부", s.label), _p("'아니오'인 경우 조치 내용", s.label)],
    ]
    for i in range(TBM_RISK_COUNT):
        hazard = risks[i]["hazard"] if i < len(risks) else ""
        rows.append([
            _pm(f"{CIRCLED[i]} " + (f'<font color="#1f3a8a">{escape(hazard)}</font>' if hazard else ""), s.cell),
            _p("예□, 아니오□", s.center),
            Paragraph("", s.cell),
        ])
    story.append(_form_table(
        rows,
        [c1, c2, W - c1 - c2],
        extra=[
            ("SPAN", (0, 0), (-1, 0)),
            ("BACKGROUND", (0, 1), (-1, 1), FORM_LABEL_BG),
            ("LINEBELOW", (0, 0), (-1, 0), 0.9, FORM_LINE),
        ],
    ))

    # ── 일일 안전점검 / 종료 미팅 ───────────────
    story.append(_form_table(
        [
            [_p("■ 작업 전 일일 안전점검 시행 결과", s.section)],
            [_p("※ 위험요인 중 조치가 되지 않은 사항, 작업자의 TBM내용 숙지 여부 중점체크", s.note)],
            [_p("■ 작업 후 종료 미팅(중점대책의 실효성)", s.section)],
            [Paragraph("", s.cell)],
        ],
        [W],
        extra=[
            ("VALIGN", (0, 1), (0, 1), "TOP"),
            ("LINEBELOW", (0, 1), (0, 1), 0.9, FORM_LINE),
            ("LINEBELOW", (0, 0), (0, 0), 0.45, FORM_INNER),
            ("LINEBELOW", (0, 2), (0, 2), 0.45, FORM_INNER),
        ],
        row_heights=[7.5 * mm, 15 * mm, 7.5 * mm, 17 * mm],
    ))

    # ── 참석자 확인 ─────────────────────────────
    name_w, sign_w = 26 * mm, W / 3 - 26 * mm
    header = [_p("이 름", s.label), _p("서 명", s.label)] * 3
    rows = [
        [_pm('■ 참석자 확인 <font name="NanumGothic" size="7.4" color="#7a7a7a">'
             '※ TBM에 참여하지 않은 작업자를 확인하여 미팅 참석 유도</font>', s.section), "", "", "", "", ""],
        header,
        *[["", "", "", "", "", ""] for _ in range(4)],
    ]
    story.append(_form_table(
        rows,
        [name_w, sign_w] * 3,
        extra=[
            ("SPAN", (0, 0), (-1, 0)),
            ("BACKGROUND", (0, 1), (-1, 1), FORM_LABEL_BG),
            ("LINEBELOW", (0, 0), (-1, 0), 0.9, FORM_LINE),
            ("LINEAFTER", (1, 1), (1, -1), 0.9, FORM_LINE),
            ("LINEAFTER", (3, 1), (3, -1), 0.9, FORM_LINE),
        ],
        row_heights=[7.5 * mm, 6.5 * mm] + [7.2 * mm] * 4,
    ))

    # AI 결과가 길어도 회의록은 항상 1장에 들어가도록 필요 시 축소한다.
    frame_h = PAGE_H - MARGIN_TOP - MARGIN_BOTTOM - 4  # 프레임 내부 패딩 여유
    return [KeepInFrame(W, frame_h, story, mode="shrink")]


# =====================================================
# 2페이지~: AI 위험성 분석 참고자료
#   - 색: PRIMARY(네이비) 1색 + ACCENT(레드)는 중점위험에만
#   - 박스: 배경 채움 없이 윤곽선만
# =====================================================

_NO_PAD = [
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ("TOPPADDING", (0, 0), (-1, -1), 0),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
]


class _RefStyles:
    def __init__(self) -> None:
        self.eyebrow = _style("r_eyebrow", 7.4, bold=True, color=PRIMARY, leading=10)
        self.hero = _style("r_hero", 18, bold=True, color=INK, leading=23)
        self.hero_sub = _style("r_hero_sub", 8.4, color=SUB, leading=12)
        self.meta = _style("r_meta", 7.6, color=SUB, align=TA_CENTER, leading=10)
        self.stat_num = _style("r_stat_num", 17, bold=True, color=PRIMARY, leading=20)
        self.stat_label = _style("r_stat_label", 7.6, color=SUB, leading=10)
        self.h2 = _style("r_h2", 10.6, bold=True, color=INK, leading=14)
        self.h2_sub = _style("r_h2_sub", 7.6, color=FAINT, leading=10.5)
        self.body = _style("r_body", 8.8, color=INK, leading=13)
        self.body_sub = _style("r_body_sub", 8, color=SUB, leading=12)
        self.small = _style("r_small", 7.4, color=SUB, leading=10.5)
        self.badge = _style("r_badge", 7.8, bold=True, color=PRIMARY, align=TA_CENTER, leading=10)
        self.tag = _style("r_tag", 7, bold=True, color=PRIMARY, align=TA_CENTER, leading=9)
        self.key_label = _style("r_key_label", 7.6, bold=True, color=ACCENT, leading=10)
        self.key_title = _style("r_key_title", 11, bold=True, color=INK, leading=15.5)
        self.law_title = _style("r_law_title", 9.2, bold=True, color=INK, leading=13)
        self.slam_en = _style("r_slam_en", 8.6, bold=True, color=PRIMARY, align=TA_CENTER, leading=11)
        self.slam_ko = _style("r_slam_ko", 7.4, color=SUB, align=TA_CENTER, leading=10)
        self.slam_desc = _style("r_slam_desc", 7.2, color=SUB, align=TA_CENTER, leading=10)


def _card(content, *, border=LINE, accent=None, pad=9, width=CONTENT_W, radius=6) -> Table:
    """윤곽선만 있는 둥근 카드. accent가 있으면 왼쪽에 얇은 색 띠를 붙인다."""
    style = [
        ("BOX", (0, 0), (-1, -1), 0.6, border),
        ("TOPPADDING", (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROUNDEDCORNERS", [radius] * 4),
    ]
    if accent is None:
        style += [
            ("LEFTPADDING", (0, 0), (-1, -1), pad + 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), pad),
        ]
        return Table([[content]], colWidths=[width], style=TableStyle(style))
    style += [
        ("BACKGROUND", (0, 0), (0, 0), accent),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 0),
        ("LEFTPADDING", (1, 0), (1, 0), pad + 2),
        ("RIGHTPADDING", (1, 0), (1, 0), pad),
    ]
    return Table([["", content]], colWidths=[2.6, width - 2.6], style=TableStyle(style))


def _outline_pill(text: str, style: ParagraphStyle, border, width: float,
                  height: float = 5.2 * mm) -> Table:
    return Table(
        [[_p(text, style)]],
        colWidths=[width],
        rowHeights=[height],
        style=TableStyle(_NO_PAD + [
            ("BOX", (0, 0), (-1, -1), 0.6, border),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ROUNDEDCORNERS", [height / 2] * 4),
        ]),
    )


def _section_head(title: str, sub: str, s: _RefStyles) -> Table:
    """소제목 바로 옆에 보조설명을 붙이고, 둘을 합친 길이만큼 네이비 밑줄을 긋는다.

    나머지 폭은 옅은 회색 구분선으로 채운다.
    """
    gap = "&nbsp;&nbsp;&nbsp;"
    markup = (
        f'{escape(title)}{gap}'
        f'<font name="{FONT}" size="{s.h2_sub.fontSize}" color="{FAINT.hexval().replace("0x", "#")}">'
        f'{escape(sub)}</font>'
    )
    text_w = (
        pdfmetrics.stringWidth(title, FONT_BOLD, s.h2.fontSize)
        + pdfmetrics.stringWidth("   ", FONT_BOLD, s.h2.fontSize)
        + pdfmetrics.stringWidth(sub, FONT, s.h2_sub.fontSize)
        + 4
    )
    text_w = min(text_w, CONTENT_W)
    rest_w = CONTENT_W - text_w
    row = [_pm(markup, s.h2)] + ([""] if rest_w > 0 else [])
    widths = [text_w] + ([rest_w] if rest_w > 0 else [])
    return Table(
        [row],
        colWidths=widths,
        style=TableStyle(_NO_PAD + [
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEBELOW", (0, 0), (0, 0), 1.2, PRIMARY),
            ("LINEBELOW", (1, 0), (-1, 0), 0.5, LINE),
        ]),
    )


def _hero(analysis: dict, s: _RefStyles) -> Table:
    created = str(analysis.get("created_at") or "-")
    chips = Table(
        [[
            _outline_pill(f"분석 #{analysis.get('id', '-')}", s.meta, LINE, 24 * mm),
            _outline_pill(created, s.meta, LINE, 36 * mm),
            _outline_pill("Multimodal RAG · Gemini", s.meta, LINE, 38 * mm),
            "",
        ]],
        colWidths=[26 * mm, 38 * mm, 40 * mm, CONTENT_W - 104 * mm],
        style=TableStyle(_NO_PAD),
    )
    content = [
        _p("SAFE-GUARD AI  ·  TBM REFERENCE", s.eyebrow),
        Spacer(1, 3),
        _p("TBM 참고자료", s.hero),
        _p("현장 사진 AI 분석 결과 — TBM 리더가 회의 전 숙지할 위험요인·사고사례·법규 요약", s.hero_sub),
        Spacer(1, 6),
        chips,
    ]
    return Table(
        [[content]],
        colWidths=[CONTENT_W],
        style=TableStyle(_NO_PAD + [
            ("LINEABOVE", (0, 0), (-1, 0), 2.2, PRIMARY),
            ("TOPPADDING", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
        ]),
    )


def _stats(data: dict, s: _RefStyles) -> Table:
    items = [
        ("잠재위험요인", len(data["hazards"])),
        ("아차사고 시나리오", len(data["accidents"])),
        ("예방대책", len(data["measures"])),
        ("관련 법규", len(data["laws"])),
    ]
    gap = 3 * mm
    tile_w = (CONTENT_W - gap * 3) / 4
    row, widths = [], []
    for i, (label, count) in enumerate(items):
        row.append(_card([_p(str(count), s.stat_num), _p(label, s.stat_label)], pad=7, width=tile_w))
        widths.append(tile_w)
        if i < len(items) - 1:
            row.append("")
            widths.append(gap)
    return Table([row], colWidths=widths, style=TableStyle(_NO_PAD))


def _key_risk_card(data: dict, s: _RefStyles) -> Table | None:
    if data["key_index"] is None:
        return None
    risk = data["risks"][data["key_index"]]
    content = [
        _p(f"중점위험요인  {CIRCLED[data['key_index']]}", s.key_label),
        Spacer(1, 2),
        _p(risk["hazard"], s.key_title),
    ]
    if data["key_reason"]:
        content += [Spacer(1, 2), _p(data["key_reason"], s.body_sub)]
    if data["key_measure"]:
        content += [
            Spacer(1, 5),
            _pm(f'<font name="{FONT_BOLD}" color="#1e3a8a">대책 →</font>&nbsp; {escape(data["key_measure"])}', s.body),
        ]
    return _card(content, border=ACCENT_LINE, accent=ACCENT, pad=10)


def _numbered_list(items: list[str], s: _RefStyles, form_no: dict[int, int] | None = None) -> list:
    """윤곽선 번호 배지 + 본문, 항목 사이 얇은 구분선 (하나의 외곽 박스).

    form_no가 주어지면 회의록(1p)에 기재된 항목 오른쪽에 '회의록 ①' 태그를 붙인다.
    """
    if not items:
        return []
    badge = 5.6 * mm
    tag_w = 17 * mm if form_no else 0
    rows = []
    for i, text in enumerate(items):
        row = [_outline_pill(str(i + 1), s.badge, PRIMARY_LINE, badge, badge), _p(text, s.body)]
        if form_no:
            number = form_no.get(i)
            row.append(
                _outline_pill(f"회의록 {CIRCLED[number]}", s.tag, PRIMARY_LINE, tag_w - 2 * mm, 4.6 * mm)
                if number is not None else ""
            )
        rows.append(row)
    widths = [badge + 9, CONTENT_W - badge - 9 - tag_w] + ([tag_w] if form_no else [])
    style = [
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("ROUNDEDCORNERS", [6] * 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, -1), 9),
        ("RIGHTPADDING", (0, 0), (0, -1), 0),
        ("LEFTPADDING", (1, 0), (1, -1), 8),
        ("RIGHTPADDING", (1, 0), (1, -1), 10),
        ("LEFTPADDING", (2, 0), (2, -1), 0),
        ("RIGHTPADDING", (2, 0), (2, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for r in range(len(rows) - 1):
        style.append(("LINEBELOW", (0, r), (-1, r), 0.4, LINE))
    return [Table(rows, colWidths=widths, style=TableStyle(style))]


def _format_law(article: str, content: str) -> tuple[str, str]:
    article_text = article.strip()
    content_text = content.strip()
    m = re.match(
        r"^(?:산업안전보건(?:기준에 관한 )?규칙\s*)?(제\s*\d+조(?:의\d+)?)(?:\s*\(([^)]+)\))?",
        article_text,
    )
    title_in_content = re.match(r"^제\s*\d+조(?:의\d+)?\s*\(([^)]+)\)", content_text)
    if not m:
        return article_text, title_in_content.group(1) if title_in_content else ""
    number = m.group(1).replace(" ", "")
    subtitle = m.group(2) or (title_in_content.group(1) if title_in_content else "")
    return number, subtitle


def _law_cards(laws: list, s: _RefStyles) -> list:
    flow = []
    for index, law in enumerate(laws, start=1):
        if isinstance(law, str):
            article, content = law, ""
        elif isinstance(law, dict):
            article = _text(law.get("article") or law.get("title")) or f"관련 법령 {index}"
            content = _text(law.get("content") or law.get("description"))
        else:
            continue
        number, subtitle = _format_law(article, content)
        head = Table(
            [[_outline_pill(number, s.tag, PRIMARY_LINE, 22 * mm),
              _p(subtitle or "산업안전보건기준에 관한 규칙", s.law_title)]],
            colWidths=[25 * mm, CONTENT_W - 25 * mm - 22],
            style=TableStyle(_NO_PAD + [("VALIGN", (0, 0), (-1, -1), "MIDDLE")]),
        )
        content_flow = [head]
        if content:
            content_flow += [Spacer(1, 4), _p(content, s.small)]
        # 한 행짜리 Table이라 페이지 중간에서 잘리지 않는다.
        # (KeepTogether로 감싸면 바깥 KeepTogether와 중첩될 때 높이가 무한대로 계산됨)
        flow.append(_card(content_flow, pad=8))
        flow.append(Spacer(1, 2.2 * mm))
    return flow


def _slam_strip(s: _RefStyles) -> list:
    steps = [
        # 칸이 좁아 의미 단위로 직접 줄을 나눈다.
        ("STOP", "멈추기", "위험·불안전 상태 발견 시<br/>작업 중지"),
        ("LOOK", "확인하기", "미처 파악하지 못한<br/>위험요인 확인"),
        ("ASSESS", "평가하기", "지식·기술·훈련·보호구<br/>준비 상태 평가"),
        ("MANAGE", "관리하기", "위험 제거·최소화,<br/>불가 시 관리자에게 보고"),
    ]
    arrow_w = 4 * mm
    w = (CONTENT_W - arrow_w * 3) / 4
    arrow_style = _style("r_arrow", 9, bold=True, color=PRIMARY_LINE, align=TA_CENTER)
    row, widths = [], []
    for i, (en, ko, desc) in enumerate(steps):
        block = Table(
            [[[_p(en, s.slam_en), _p(ko, s.slam_ko)]], [_pm(desc, s.slam_desc)]],
            colWidths=[w],
            rowHeights=[None, 11 * mm],
            style=TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("LINEBELOW", (0, 0), (-1, 0), 0.4, LINE),
                ("ROUNDEDCORNERS", [5] * 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 1), (-1, 1), "MIDDLE"),
            ]),
        )
        row.append(block)
        widths.append(w)
        if i < len(steps) - 1:
            row.append(_p("›", arrow_style))
            widths.append(arrow_w)
    strip = Table([row], colWidths=widths, style=TableStyle(_NO_PAD + [("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return [
        _section_head("위험 발견 시 행동요령", "SLAM technique · TBM 가이드 Ⅱ-2", s),
        Spacer(1, 3 * mm),
        strip,
    ]


IMAGE_BOX_H = 72 * mm


def _load_image(image_url: str | None) -> Image | None:
    if not image_url:
        return None
    try:
        image_bytes, _ = download_analysis_image(image_url)
        image = Image(BytesIO(image_bytes))
    except Exception:
        # 이미지 저장소에 접근할 수 없어도 회의록은 생성한다.
        return None
    ratio = image.imageHeight / image.imageWidth
    max_w, max_h = CONTENT_W - 20, IMAGE_BOX_H - 16
    image.drawWidth = max_w
    image.drawHeight = max_w * ratio
    if image.drawHeight > max_h:
        image.drawHeight = max_h
        image.drawWidth = max_h / ratio
    return image


def _image_card(image_url: str | None) -> Table:
    """현장 사진 영역. 사진을 불러오지 못하면 같은 크기의 점선 자리표시를 그린다."""
    image = _load_image(image_url)
    if image is not None:
        return Table(
            [[image]],
            colWidths=[CONTENT_W],
            rowHeights=[IMAGE_BOX_H],
            style=TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROUNDEDCORNERS", [6] * 4),
            ]),
        )
    placeholder_title = _style("r_ph_title", 9.4, bold=True, color=FAINT, align=TA_CENTER, leading=13)
    placeholder_sub = _style("r_ph_sub", 7.6, color=FAINT, align=TA_CENTER, leading=11)
    return Table(
        [[[
            _p("현장 사진", placeholder_title),
            _p("분석에 사용된 현장 사진(얼굴·번호판 마스킹)이 이 위치에 표시됩니다", placeholder_sub),
        ]]],
        colWidths=[CONTENT_W],
        rowHeights=[IMAGE_BOX_H],
        style=TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.8, PRIMARY_LINE, None, (3, 3)),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROUNDEDCORNERS", [6] * 4),
        ]),
    )


def _build_reference_pages(analysis: dict, data: dict) -> list:
    s = _RefStyles()
    gap_l, gap_m = 6.5 * mm, 3 * mm
    story: list = [
        _hero(analysis, s),
        Spacer(1, gap_m + 1 * mm),
        _section_head("현장 사진", "AI 분석에 사용된 이미지 · 개인정보(얼굴·번호판) 마스킹", s),
        Spacer(1, gap_m),
        _image_card(analysis.get("image_url")),
        Spacer(1, gap_m + 1 * mm),
        _stats(data, s),
        Spacer(1, gap_l),
    ]

    key_card = _key_risk_card(data, s)
    if key_card is not None:
        story += [key_card, Spacer(1, gap_l)]

    sections = [
        ("잠재위험요인", "AI 분석 전체 항목 · 태그는 회의록(1p) 기재 번호",
         data["hazards"], data["hazard_form_no"]),
        ("발생 가능한 아차사고", "Near Miss · 유사 사고사례 RAG 기반", data["accidents"], None),
        ("예방대책", "AI 분석 전체 항목 · 태그는 회의록(1p) 기재 번호",
         data["measures"], data["measure_form_no"]),
    ]
    for title, sub, items, form_no in sections:
        if not items:
            continue
        head = [_section_head(title, sub, s), Spacer(1, gap_m)]
        story.append(KeepTogether(head + _numbered_list(items, s, form_no)))
        story.append(Spacer(1, gap_l))

    story.append(KeepTogether(_slam_strip(s)))
    story.append(Spacer(1, gap_l))

    law_cards = _law_cards(data["laws"], s)
    if law_cards:
        # 제목만 페이지 끝에 홀로 남지 않도록 첫 카드와 묶는다.
        head = [_section_head("관련 법규", "산업안전보건기준에 관한 규칙", s), Spacer(1, gap_m)]
        story.append(KeepTogether(head + law_cards[:1]))
        story += law_cards[1:]
    return story


# =====================================================
# 페이지 장식 & 진입점
# =====================================================

def _draw_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FONT, 6.8)
    canvas.setFillColor(FORM_NOTE)
    y = 8 * mm
    if doc.page == 1:
        canvas.drawString(
            MARGIN_X, y + 3.6 * mm,
            "파란색 글씨는 AI 현장 사진 분석으로 미리 채운 내용입니다. 현장 확인 후 수정·보완하고, "
            "상세 근거는 「TBM 참고자료」(2p~)를 참고하십시오.",
        )
        canvas.drawString(MARGIN_X, y, SOURCE_TEXT.replace("&lt;", "<").replace("&gt;", ">"))
    else:
        canvas.setFillColor(FAINT)
        canvas.drawString(
            MARGIN_X, y,
            "Safe-Guard AI · 본 참고자료는 AI 분석 결과로 위험성평가를 대체하지 않으며, 현장 확인 후 보완하여 활용하십시오.",
        )
    canvas.drawRightString(PAGE_W - MARGIN_X, y, f"{doc.page}")
    canvas.restoreState()


def create_tbm_report_pdf(analysis: dict) -> bytes:
    """분석 결과 1건으로 TBM 회의록(1p) + 참고자료(2p~) PDF를 만든다."""
    _register_fonts()
    ai_result = analysis.get("ai_result") or {}
    data = build_tbm_data(ai_result)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title="Tool Box Meeting 회의록",
        author="Safe-Guard AI",
    )
    story = _build_form_page(data)
    story.append(PageBreak())
    story.extend(_build_reference_pages(analysis, data))
    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return buffer.getvalue()
