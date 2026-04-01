import os
import resend

# Set API key
resend.api_key = os.getenv("RESEND_API_KEY")

def send_otp_email(to_email: str, otp: str):
    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": to_email,
        "subject": "Your Verification Code",
        "html": f"""
        <h2>AI Finance App 🔐</h2>
        <p>Your verification code is:</p>
        <h1>{otp}</h1>
        <p>This code expires in 5 minutes</p>
        """
    })