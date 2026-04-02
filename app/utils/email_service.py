import requests
import os

def send_otp_email(to_email, otp):
    API_KEY = os.getenv("RESEND_API_KEY")
    FROM_EMAIL = os.getenv("FROM_EMAIL")

    if not API_KEY or not FROM_EMAIL:
        print("Missing API KEY or FROM EMAIL")
        return False

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "from": f"Finance AI <{FROM_EMAIL}>",  # ✅ FIX HERE
        "to": [to_email],
        "subject": "OTP Verification",
        "html": f"""
        <h2>OTP Verification</h2>
        <h1>{otp}</h1>
        <p>Valid for 5 minutes</p>
        """
    }

    res = requests.post(
        "https://api.resend.com/emails",
        json=payload,
        headers=headers
    )

    print("EMAIL STATUS:", res.status_code)
    print("EMAIL RESPONSE:", res.text)

    return res.status_code in [200, 202]