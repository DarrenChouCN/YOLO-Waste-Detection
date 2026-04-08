import base64
import cv2

from main import InferenceService

IMAGE_PATH = "Image/image_phone.jpeg"

service = InferenceService(
    model_path="best_model.pt",
    conf=0.25,
    serialize_predict=False,
)

with open(IMAGE_PATH, "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("utf-8")

decoded_image = service._decode_base64_image(image_b64)
print("decode ok:", decoded_image.shape)

result = service._predict(decoded_image)
print("predict ok")
print("boxes count:", 0 if result.boxes is None else len(result.boxes))

annotated = result.plot()
cv2.imwrite("debug_prediction.jpg", annotated)
print("saved debug_prediction.jpg")