import smtplib
from email.mime.text import MIMEText

def send_otp_email(to_email, otp):
    sender = "jeyaram5408@gmail.com"
    app_password = "uvmu utgn szdc wexa"

    msg = MIMEText(f"Your OTP is {otp}")
    msg["Subject"] = "OTP Verification"
    msg["From"] = sender
    msg["To"] = to_email

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender, app_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print("EMAIL ERROR:", e)
        return False