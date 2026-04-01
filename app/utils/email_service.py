import os
import resend

def send_otp_email(to_email: str, otp: str):
    try:
        # ✅ Always set API key inside function
        resend.api_key = os.getenv("RESEND_API_KEY")

        print("API KEY:", resend.api_key)  # debug

        response = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": [to_email],   # ⚠️ IMPORTANT: list format
            "subject": "Your Verification Code",
            "html": f"""
            <h2>AI Finance App 🔐</h2>
            <p>Your verification code is:</p>
            <h1>{otp}</h1>
            <p>This code expires in 5 minutes</p>
            """
        })

        print("EMAIL SUCCESS:", response)

    except Exception as e:
        print("EMAIL ERROR:", str(e))