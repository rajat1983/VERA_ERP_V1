import smtplib
from email.message import EmailMessage

MAIL_SERVER = "mailpit"
MAIL_PORT = 1025

FROM_EMAIL = "noreply@localhost"
ADMIN_EMAIL = "parida2008@gmail.com"


def send_email(to_email, subject, html_content):
    try:
        msg = EmailMessage()
        msg["From"] = FROM_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.set_content("This email requires HTML support.")
        msg.add_alternative(html_content, subtype="html")

        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.send_message(msg)

        return True

    except Exception as e:
        print("EMAIL ERROR:", e)
        return False
