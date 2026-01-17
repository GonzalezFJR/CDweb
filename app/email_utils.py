import smtplib
from email.message import EmailMessage
from typing import Iterable

from app.config import settings


def send_email(
    subject: str,
    body: str,
    to_email: str,
    attachments: Iterable[tuple[str, bytes, str]] | None = None,
) -> None:
    if not settings.smtp_host:
        return
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message.set_content(body)

    if attachments:
        for filename, content, content_type in attachments:
            if "/" in content_type:
                maintype, subtype = content_type.split("/", 1)
            else:
                maintype, subtype = "application", "octet-stream"
            message.add_attachment(
                content,
                maintype=maintype,
                subtype=subtype,
                filename=filename,
            )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
