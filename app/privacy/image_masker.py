import os
from pathlib import Path

YOLO_CONFIG_DIR = Path("/private/tmp/team4ward-ultralytics")
MPL_CONFIG_DIR = Path("/private/tmp/team4ward-matplotlib")
YOLO_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
MPL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("YOLO_CONFIG_DIR", str(YOLO_CONFIG_DIR))
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG_DIR))

import cv2
import numpy as np
from ultralytics import YOLO


APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FACE_MODEL_PATH = APP_ROOT / "models" / "face_yolo.pt"
DEFAULT_PLATE_MODEL_PATH = APP_ROOT / "models" / "license_plate_yolo.pt"


def _resolve_model_path(env_name: str, default_path: Path) -> Path:
    configured_path = os.getenv(env_name)
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return default_path


_models: tuple[YOLO, YOLO] | None = None


def load_yolo_models(
    face_model_path: Path,
    plate_model_path: Path,
) -> tuple[YOLO, YOLO]:
    """YOLO 얼굴/번호판 모델을 메모리에 올림"""
    if not face_model_path.exists():
        raise FileNotFoundError(f"얼굴 YOLO 모델을 찾을 수 없습니다: {face_model_path}")
    if not plate_model_path.exists():
        raise FileNotFoundError(f"번호판 YOLO 모델을 찾을 수 없습니다: {plate_model_path}")

    return YOLO(str(face_model_path)), YOLO(str(plate_model_path))


def initialize_yolo_models() -> None:
    """서버 시작 시 YOLO 모델을 로드함"""
    global _models

    if _models is not None:
        return

    face_model_path = _resolve_model_path("FACE_YOLO_MODEL_PATH", DEFAULT_FACE_MODEL_PATH)
    plate_model_path = _resolve_model_path("PLATE_YOLO_MODEL_PATH", DEFAULT_PLATE_MODEL_PATH)

    try:
        _models = load_yolo_models(face_model_path, plate_model_path)
    except FileNotFoundError as exc:
        raise RuntimeError(str(exc)) from exc


def get_yolo_models() -> tuple[YOLO, YOLO]:
    """서버 시작 시 로드된 YOLO 모델을 반환함"""
    if _models is None:
        raise RuntimeError("YOLO 모델이 로드되지 않았습니다. 서버 시작 설정을 확인하세요.")

    return _models


def blur_boxes(image: np.ndarray, boxes: np.ndarray, min_kernel: int = 31, kernel_ratio: int = 5) -> np.ndarray:
    """YOLO가 찾은 xyxy 박스 영역을 블러함"""
    result = image.copy()
    height, width = result.shape[:2]

    for box in boxes:
        x1, y1, x2, y2 = map(int, box)
        x1 = max(0, min(x1, width - 1))
        y1 = max(0, min(y1, height - 1))
        x2 = max(0, min(x2, width))
        y2 = max(0, min(y2, height))

        if x2 <= x1 or y2 <= y1:
            continue

        roi = result[y1:y2, x1:x2]
        box_w = x2 - x1
        box_h = y2 - y1
        kernel = max(min_kernel, (max(box_w, box_h) // kernel_ratio) | 1)
        if kernel % 2 == 0:
            kernel += 1

        result[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (kernel, kernel), 0)

    return result


def detect_yolo_boxes(model: YOLO, image: np.ndarray, conf: float = 0.25, imgsz: int = 640) -> tuple[np.ndarray, np.ndarray]:
    """YOLO 모델 결과에서 confidence 기준을 통과한 xyxy 박스와 점수를 반환함"""
    prediction = model(image, conf=conf, imgsz=imgsz, verbose=False)[0]
    if prediction.boxes is None or len(prediction.boxes) == 0:
        return np.empty((0, 4), dtype=int), np.empty((0,), dtype=float)

    boxes = prediction.boxes.xyxy.cpu().numpy().astype(int)
    scores = prediction.boxes.conf.cpu().numpy()
    return boxes, scores


def blur_faces_and_plates_yolo(
    image: np.ndarray,
    face_model: YOLO,
    plate_model: YOLO,
    face_conf: float = 0.25,
    plate_conf: float = 0.10,
    face_imgsz: int = 640,
    plate_imgsz: int = 1280,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """디코딩된 이미지 배열에서 YOLO로 얼굴/번호판을 찾아 블러함"""
    if image is None:
        raise ValueError("image는 None일 수 없습니다.")

    face_boxes, face_scores = detect_yolo_boxes(
        face_model,
        image,
        conf=face_conf,
        imgsz=face_imgsz,
    )
    plate_boxes, plate_scores = detect_yolo_boxes(
        plate_model,
        image,
        conf=plate_conf,
        imgsz=plate_imgsz,
    )

    result = blur_boxes(image, face_boxes, min_kernel=31, kernel_ratio=5)
    result = blur_boxes(result, plate_boxes, min_kernel=41, kernel_ratio=2)

    detections = {
        "faces": face_boxes,
        "plates": plate_boxes,
        "face_scores": face_scores,
        "plate_scores": plate_scores,
    }
    return result, detections


async def blur_sensitive_regions(image_bytes: bytes) -> bytes:
    """업로드 이미지 bytes에서 얼굴/번호판을 블러 처리한 bytes를 반환함"""
    np_image = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(np_image, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("이미지를 디코딩할 수 없습니다.")

    face_model, plate_model = get_yolo_models()
    blurred_image, _ = blur_faces_and_plates_yolo(image, face_model, plate_model)

    success, encoded_image = cv2.imencode(".jpg", blurred_image)
    if not success:
        raise ValueError("이미지를 인코딩할 수 없습니다.")

    return encoded_image.tobytes()
