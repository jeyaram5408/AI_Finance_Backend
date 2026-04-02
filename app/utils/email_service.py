import requests
import os

def send_otp_email(to_email, otp):
    API_KEY = os.getenv("RESEND_API_KEY")
    FROM_EMAIL = os.getenv("FROM_EMAIL")

    url = "https://api.resend.com/emails"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "from": FROM_EMAIL,
        "to": [to_email],
        "subject": "OTP Verification",
        "html": f"""
        <h2>OTP Verification</h2>
        <h1>{otp}</h1>
        <p>Valid for 5 minutes</p>
        """
    }

    try:
        res = requests.post(url, json=payload, headers=headers)

        if res.status_code == 200:
            print("EMAIL SENT ✅")
            return True
        else:
            print("FAILED:", res.text)
            return False

    except Exception as e:
        print("ERROR:", e)
        return False