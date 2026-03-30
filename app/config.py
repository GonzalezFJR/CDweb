import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://mongo:27017")
    mongo_db: str = os.getenv("MONGO_DB", "cielos_despejados")
    secret_key: str = os.getenv("SECRET_KEY", "change-me")
    contact_email: str = os.getenv("CONTACT_EMAIL", "info@cielosdespejados.es")
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "noreply@cielosdespejados.es")
    admin_email: str = os.getenv("ADMIN_EMAIL", "")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")    
    captcha_site_key:   str = os.getenv("CAPTCHA_SITE_KEY", "")
    captcha_secret_key: str = os.getenv("CAPTCHA_SECRET_KEY", "")

settings = Settings()
