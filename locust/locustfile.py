import os
import base64
import uuid
from locust import HttpUser, task, between

IMAGE_PATH = os.path.join(os.path.dirname(__file__), "test.jpg")


def build_payload():
    with open(IMAGE_PATH, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    return {
        "uuid": str(uuid.uuid4()),
        "image": image_b64
    }


class ApiUser(HttpUser):
    wait_time = between(1, 2)

    @task(2)
    def predict(self):
        payload = build_payload()
        with self.client.post(
            "/api/predict",
            json=payload,
            name="POST /api/predict",
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Status code: {response.status_code}, body: {response.text}")
            else:
                response.success()

    @task(1)
    def annotate(self):
        payload = build_payload()
        with self.client.post(
            "/api/annotate",
            json=payload,
            name="POST /api/annotate",
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Status code: {response.status_code}, body: {response.text}")
            else:
                response.success()