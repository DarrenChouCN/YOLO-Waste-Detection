import base64
import uuid
import requests

IMAGE_PATH = "Image/image_phone.jpeg"
OUTPUT_PATH = "service_debug_prediction.jpg"

SERVICE_URL = "http://4.193.105.141:30080/api/annotate"
# SERVICE_URL = "http://104.215.144.255:30080/api/annotate"



def main():
    with open(IMAGE_PATH, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "uuid": str(uuid.uuid4()),
        "image": image_b64
    }

    response = requests.post(SERVICE_URL, json=payload, timeout=120)

    print("status code:", response.status_code)
    response.raise_for_status()

    data = response.json()
    print("response keys:", list(data.keys()))
    print("uuid:", data.get("uuid"))
    print("count:", data.get("count"))
    print("detections:", data.get("detections"))
    print("boxes:", len(data.get("boxes", [])))

    result_b64 = data["image"]

    with open(OUTPUT_PATH, "wb") as f:
        f.write(base64.b64decode(result_b64))

    print(f"saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()