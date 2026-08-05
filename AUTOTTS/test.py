import requests

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3ODM4NDk5MTV9.kVwu0s32HTgv2UmtC025pS284OoDX4Y7Hl87WnccF_I"
APP_ID = "5abdf847-01ac-4fc2-b1ee-12c9891644f1"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "App-Id": APP_ID,
    "Content-Type": "application/json",
}

params = {
    "voiceOwnership": "VBEE",
    "languageCode": "vi-VN",
    "limit": 20,
}

try:
    response = requests.get(
        "https://vbee.vn/api/public/v1/voices",
        headers=headers,
        params=params,
        timeout=30,
    )

    print("URL:", response.url)
    print("HTTP status:", response.status_code)
    print("Response:", response.text)

except requests.exceptions.ConnectionError as error:
    print("Lỗi kết nối:", error)

except requests.exceptions.Timeout:
    print("Kết nối quá thời gian.")

except Exception as error:
    print("Lỗi:", error)