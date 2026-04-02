import requests
import os

def send_otp_email(to_email, otp):
    API_KEY = os.getenv("BREVO_API_KEY")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")

    if not API_KEY or not SENDER_EMAIL:
        raise ValueError("Missing BREVO_API_KEY or SENDER_EMAIL")

    url = "https://api.brevo.com/v3/smtp/email"

    payload = {
        "sender": {
            "name": "Finance AI App",
            "email": SENDER_EMAIL
        },
        "to": [{"email": to_email}],
        "subject": "Your OTP Code",
        "htmlContent": f"""
            <h2>OTP Verification</h2>
            <p>Your OTP is:</p>
            <h1 style="letter-spacing:4px;">{otp}</h1>
            <p>This OTP is valid for 5 minutes.</p>
        """,
        "textContent": f"Your OTP is {otp}. It is valid for 5 minutes."
    }

    headers = {
        "accept": "application/json",
        "api-key": API_KEY,
        "content-type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 201:
        print("Email sent ✅", response.json())
        return True
    else:
        print("FAILED ❌", response.status_code, response.text)
        return False