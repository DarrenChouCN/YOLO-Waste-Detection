import asyncio
import base64
import logging
import os
import threading
from contextlib import asynccontextmanager
from typing import List, Union

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from ultralytics import YOLO

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("cloudeco")

MODEL_PATH = os.getenv("MODEL_PATH", "best_model.pt")
MODEL_CONFIDENCE = float(os.getenv("MODEL_CONFIDENCE", "0.25"))
DEFAULT_MAX_CONCURRENCY = max(1, min(4, os.cpu_count() or 1))
MAX_INFERENCE_CONCURRENCY = max(
    1, int(os.getenv("MAX_INFERENCE_CONCURRENCY", str(DEFAULT_MAX_CONCURRENCY)))
)
SERIALIZE_MODEL_PREDICT = os.getenv("SERIALIZE_MODEL_PREDICT", "false").lower() == "true"
WARMUP_ON_STARTUP = os.getenv("WARMUP_ON_STARTUP", "true").lower() == "true"
ANNOTATION_JPEG_QUALITY = int(os.getenv("ANNOTATION_JPEG_QUALITY", "90"))


class PredictRequest(BaseModel):
    uuid: str = Field(..., description="Client-generated request ID")
    image: str = Field(..., description="Base64-encoded image")


class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int
    probability: float


class PredictResponse(BaseModel):
    uuid: str
    count: int
    detections: List[str]
    boxes: List[BoundingBox]
    speed_preprocess_ms: float
    speed_inference_ms: float
    speed_postprocess_ms: float


class AnnotateResponse(PredictResponse):
    image: str


class InferenceService:
    def __init__(self, model_path: str, conf: float, serialize_predict: bool = False) -> None:
        self.model = YOLO(model_path)
        self.conf = conf
        self.serialize_predict = serialize_predict
        self._predict_lock = threading.Lock()

    def warmup(self) -> None:
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        self._predict(dummy)
        logger.info("Model warm-up completed")

    def predict(self, payload: PredictRequest) -> PredictResponse:
        image_bgr = self._decode_base64_image(payload.image)
        result = self._predict(image_bgr)
        return self._build_predict_response(payload.uuid, result)

    def annotate(self, payload: PredictRequest) -> AnnotateResponse:
        image_bgr = self._decode_base64_image(payload.image)
        result = self._predict(image_bgr)
        predict_response = self._build_predict_response(payload.uuid, result)
        annotated_image = self._draw_annotations(image_bgr.copy(), predict_response)
        encoded_image = self._encode_image_to_base64(annotated_image)

        response_data = (
            predict_response.model_dump()
            if hasattr(predict_response, "model_dump")
            else predict_response.dict()
        )
        response_data["image"] = encoded_image
        return AnnotateResponse(**response_data)

    def _predict(self, image_bgr: np.ndarray):
        if self.serialize_predict:
            with self._predict_lock:
                results = self.model.predict(source=image_bgr, conf=self.conf, verbose=False)
        else:
            results = self.model.predict(source=image_bgr, conf=self.conf, verbose=False)

        if not results:
            raise RuntimeError("Model returned no prediction result")
        return results[0]

    def _build_predict_response(self, uuid: str, result) -> PredictResponse:
        boxes_out: List[BoundingBox] = []
        detections: List[str] = []

        names_map = result.names if isinstance(result.names, dict) else {}
        has_boxes = result.boxes is not None and len(result.boxes) > 0

        if has_boxes:
            xyxy_list = result.boxes.xyxy.cpu().tolist()
            cls_list = result.boxes.cls.cpu().tolist()
            conf_list = result.boxes.conf.cpu().tolist()

            for xyxy, cls_id, conf in zip(xyxy_list, cls_list, conf_list):
                x1, y1, x2, y2 = xyxy

                x = max(0, int(round(x1)))
                y = max(0, int(round(y1)))
                x2_i = max(x, int(round(x2)))
                y2_i = max(y, int(round(y2)))

                width = max(0, x2_i - x)
                height = max(0, y2_i - y)
                probability = round(float(conf), 6)

                label = names_map.get(int(cls_id), str(int(cls_id)))
                detections.append(label)
                boxes_out.append(
                    BoundingBox(
                        x=x,
                        y=y,
                        width=width,
                        height=height,
                        probability=probability,
                    )
                )

        speed = getattr(result, "speed", {}) or {}

        return PredictResponse(
            uuid=uuid,
            count=len(boxes_out),
            detections=detections,
            boxes=boxes_out,
            speed_preprocess_ms=round(float(speed.get("preprocess", 0.0)), 6),
            speed_inference_ms=round(float(speed.get("inference", 0.0)), 6),
            speed_postprocess_ms=round(float(speed.get("postprocess", 0.0)), 6),
        )

    @staticmethod
    def _normalize_base64_image(raw: str) -> str:
        data = raw.strip()

        if data.startswith("data:image"):
            _, data = data.split(",", 1)

        data = "".join(data.split())

        padding = len(data) % 4
        if padding:
            data += "=" * (4 - padding)

        return data

    def _decode_base64_image(self, raw: str) -> np.ndarray:
        normalized = self._normalize_base64_image(raw)

        try:
            image_bytes = base64.b64decode(normalized, validate=True)
        except Exception as exc:
            raise ValueError("Invalid base64 image payload") from exc

        np_buffer = np.frombuffer(image_bytes, dtype=np.uint8)
        image_bgr = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)

        if image_bgr is None:
            raise ValueError("Decoded payload is not a valid image")

        return image_bgr

    @staticmethod
    def _draw_annotations(image_bgr: np.ndarray, prediction: PredictResponse) -> np.ndarray:
        for label, box in zip(prediction.detections, prediction.boxes):
            x1, y1 = box.x, box.y
            x2, y2 = box.x + box.width, box.y + box.height

            cv2.rectangle(image_bgr, (x1, y1), (x2, y2), (255, 0, 0), 2)

            text = f"{label} {box.probability:.2f}"
            text_y = y1 - 8 if y1 > 20 else y1 + 20
            cv2.putText(
                image_bgr,
                text,
                (x1, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 0, 0),
                2,
                cv2.LINE_AA,
            )

        return image_bgr

    @staticmethod
    def _encode_image_to_base64(image_bgr: np.ndarray) -> str:
        success, encoded = cv2.imencode(
            ".jpg",
            image_bgr,
            [int(cv2.IMWRITE_JPEG_QUALITY), ANNOTATION_JPEG_QUALITY],
        )
        if not success:
            raise RuntimeError("Failed to encode annotated image")
        return base64.b64encode(encoded.tobytes()).decode("utf-8")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading YOLO model from %s", MODEL_PATH)

    service = InferenceService(
        model_path=MODEL_PATH,
        conf=MODEL_CONFIDENCE,
        serialize_predict=SERIALIZE_MODEL_PREDICT,
    )

    if WARMUP_ON_STARTUP:
        try:
            await run_in_threadpool(service.warmup)
        except Exception:
            logger.exception("Model warm-up failed")

    app.state.inference_service = service
    app.state.inference_semaphore = asyncio.Semaphore(MAX_INFERENCE_CONCURRENCY)

    logger.info(
        "Application started | model=%s | conf=%.2f | max_inference_concurrency=%d | serialize_predict=%s",
        MODEL_PATH,
        MODEL_CONFIDENCE,
        MAX_INFERENCE_CONCURRENCY,
        SERIALIZE_MODEL_PREDICT,
    )
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title="CloudEco Inference API",
    version="1.0.0",
    lifespan=lifespan,
)


def get_service_and_semaphore(request: Request):
    service = getattr(request.app.state, "inference_service", None)
    semaphore = getattr(request.app.state, "inference_semaphore", None)

    if service is None or semaphore is None:
        raise HTTPException(status_code=503, detail="Model service is not ready")

    return service, semaphore


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/api/predict", response_model=PredictResponse)
async def predict(payload: PredictRequest, request: Request):
    service, semaphore = get_service_and_semaphore(request)

    try:
        async with semaphore:
            return await run_in_threadpool(service.predict, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail="Prediction failed") from exc


@app.post("/api/annotate", response_model=AnnotateResponse)
async def annotate(payload: PredictRequest, request: Request):
    service, semaphore = get_service_and_semaphore(request)

    try:
        async with semaphore:
            return await run_in_threadpool(service.annotate, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Annotation failed")
        raise HTTPException(status_code=500, detail="Annotation failed") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        workers=int(os.getenv("UVICORN_WORKERS", "1")),
    )