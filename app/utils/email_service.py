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
        "subject": "OTP Verification",
        "htmlContent": f"""
            <h2>OTP Verification</h2>
            <p>Your OTP is:</p>
            <h1>{otp}</h1>
            <p>This OTP is valid for 5 minutes.</p>
        """
    }

    headers = {
        "accept": "application/json",
        "api-key": API_KEY,
        "content-type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 201:
            return True
        else:
            print("FAILED:", response.text)
            return False

    except Exception as e:
        print("EMAIL ERROR:", e)
        return False