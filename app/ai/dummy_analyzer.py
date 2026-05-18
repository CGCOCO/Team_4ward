
async def dummy_analyze_risk(image_bytes: bytes) -> dict:
    """
    이미지 바이트를 받아 위험요소 분석 결과를 반환한다.
    나중에 이 함수 내부에 Vision AI 모델 호출을 붙인다.
    """

    return {
        "risk_level": "HIGH",
        "summary": "작업자가 안전모를 착용하지 않았고, 바닥에 장애물이 있어 위험합니다.",
        "detected_risks": [
            {
                "type": "NO_HELMET",
                "severity": "HIGH",
                "description": "작업자가 안전모 없이 작업 중입니다.",
                "recommendation": "작업 전 안전모 착용 여부를 확인하세요.",
            },
            {
                "type": "TRIP_HAZARD",
                "severity": "MEDIUM",
                "description": "작업장 바닥에 장애물이 있어 넘어질 위험이 있습니다.",
                "recommendation": "작업장 바닥의 장애물을 제거하세요.",
            },
        ],
    }