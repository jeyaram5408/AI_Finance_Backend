import os
import smtplib
from email.mime.text import MIMEText

def send_otp_email(to_email, otp):
    # SMTP credentials (Brevo)
    EMAIL = os.getenv("EMAIL")  # a6dea6001@smtp-brevo.com
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # SMTP Key

    # Verified sender email (important)
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")  # jeyaram5408@gmail.com

    msg = MIMEText(f"Your OTP is {otp}")
    msg["Subject"] = "OTP Verification"
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp-relay.brevo.com", 587)  # ✅ correct server
        server.starttls()
        server.login(EMAIL, EMAIL_PASSWORD)  # ✅ login with SMTP login
        server.send_message(msg)
        server.quit()

        print("✅ Email Sent Successfully")

    except Exception as e:
        print("❌ Email Error:", e)