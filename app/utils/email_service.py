import requests
import os

def send_otp_email(to_email, otp):
    API_KEY = os.getenv("BREVO_API_KEY")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")

    url = "https://api.brevo.com/v3/smtp/email"

    payload = {
        "sender": {"email": SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": "OTP Verification",
        "htmlContent": f"<h3>Your OTP is: {otp}</h3>"
    }

    headers = {
        "accept": "application/json",
        "api-key": API_KEY,
        "content-type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        print("STATUS:", response.status_code)
        print("RESPONSE:", response.text)
    except Exception as e:
        print("EMAIL ERROR:", e)