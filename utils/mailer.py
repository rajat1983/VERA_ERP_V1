import os
import smtplib
import socket
from email.message import EmailMessage

MAIL_PORT = int(os.environ.get("MAIL_PORT", "1025"))
FROM_EMAIL = os.environ.get("MAIL_FROM", "noreply@vera-erp.local")
ADMIN_EMAIL = os.environ.get("MAIL_ADMIN", "parida2008@gmail.com")


def _smtp_hosts():
    env_host = (os.environ.get("MAIL_SERVER") or "").strip()
    hosts = []
    if env_host:
        hosts.append(env_host)
    # DDEV Mailpit listens on IPv4 inside the web container. Avoid localhost (::1).
    for host in ("127.0.0.1", "localhost", "mailpit"):
        if host not in hosts:
            hosts.append(host)
    return hosts


def send_email(to_email, subject, html_content):
    if not to_email:
        print("EMAIL ERROR: missing recipient")
        return False
    msg = EmailMessage()
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content("This email requires HTML support.")
    msg.add_alternative(html_content, subtype="html")

    last_error = None
    for host in _smtp_hosts():
        try:
            with smtplib.SMTP(host, MAIL_PORT, timeout=8) as server:
                server.send_message(msg)
            print("EMAIL SENT via %s:%s to %s" % (host, MAIL_PORT, to_email))
            return True
        except (OSError, smtplib.SMTPException, socket.error) as e:
            last_error = e
            print("EMAIL TRY FAIL %s:%s: %s" % (host, MAIL_PORT, e))
            continue
    print("EMAIL ERROR: could not reach Mailpit on port %s (%s)" % (MAIL_PORT, last_error))
    return False
