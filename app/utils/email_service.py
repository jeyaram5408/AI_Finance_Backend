# import requests
# import os

# def send_otp_email(to_email, otp):
#     API_KEY = os.getenv("BREVO_API_KEY")
#     SENDER_EMAIL = os.getenv("SENDER_EMAIL")

#     if not API_KEY or not SENDER_EMAIL:
#         raise ValueError("Missing BREVO_API_KEY or SENDER_EMAIL")

#     url = "https://api.brevo.com/v3/smtp/email"

#     payload = {
#         "sender": {
#             "name": "Finance AI App",
#             "email": SENDER_EMAIL
#         },
#         "to": [{"email": to_email}],
#         "subject": "Your OTP Code",
#         "htmlContent": f"""
#             <h2>OTP Verification</h2>
#             <p>Your OTP is:</p>
#             <h1 style="letter-spacing:4px;">{otp}</h1>
#             <p>This OTP is valid for 5 minutes.</p>
#         """,
#         "textContent": f"Your OTP is {otp}. It is valid for 5 minutes."
#     }

#     headers = {
#         "accept": "application/json",
#         "api-key": API_KEY,
#         "content-type": "application/json"
#     }

#     response = requests.post(url, json=payload, headers=headers)

#     if response.status_code == 201:
#         print("Email sent ✅", response.json())
#         return True
#     else:
#         print("FAILED ❌", response.status_code, response.text)
#         return False


        #Local


import os
import aiosmtplib
from email.message import EmailMessage

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT"))
SMTP_USER = os.getenv("Email")
SMTP_PASS = os.getenv("Email_Password")

async def send_otp_email(to_email: str, otp: str):
    message = EmailMessage()
    message["From"] = f"Finance AI <{SMTP_USER}>"
    message["To"] = to_email
    message["Subject"] = "Your OTP Code"

    message.set_content(f"Your OTP is {otp}")

    message.add_alternative(f"""
   <html>
  <body style="margin:0; padding:0; font-family:Arial, sans-serif; background-color:#f4f4f4;">

    <div style="max-width:500px; margin:40px auto; background:#ffffff; padding:30px; border-radius:10px; text-align:center; box-shadow:0 2px 10px rgba(0,0,0,0.1);">

      <h2 style="color:#333;">Finance AI</h2>

      <p style="color:#666; font-size:14px;">
        Use the OTP below to verify your email. This OTP is valid for 5 minutes.
      </p>

      <div style="margin:20px 0;">
        <span style="display:inline-block; padding:12px 25px; font-size:24px; letter-spacing:4px; background:#f1f1f1; border-radius:6px; font-weight:bold;">
          {otp}
        </span>
      </div>

      <p style="color:#999; font-size:12px;">
        If you didn’t request this, ignore this email.
      </p>

    </div>

  </body>
</html>
    """, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASS,
            start_tls=True,
        )
        print("✅ Email sent successfully")
    except Exception as e:
        print("❌ Email failed:", str(e))