def send_otp_email(to_email, otp):
    EMAIL = os.getenv("EMAIL")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")

    print("EMAIL:", EMAIL)
    print("SENDER:", SENDER_EMAIL)

    msg = MIMEText(f"Your OTP is {otp}")
    msg["Subject"] = "OTP Verification"
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp-relay.brevo.com", 587)
        server.starttls()
        server.login(EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        print("✅ Email Sent Successfully")

    except Exception as e:
        print("❌ Email Error:", e)