import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def send_email(to_email: str, subject: str, html_content: str, text_content: str = "") -> bool:
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured. Email not sent.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    msg["To"] = to_email

    if text_content:
        msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,   # 587
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=True,            # STARTTLS for port 587
            use_tls=False,             # ensure implicit TLS is off
        )
        logger.info(f"Verification email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


async def send_verification_email(email: str, username: str, verification_token: str) -> bool:
    """Send email verification link to user."""
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"

    subject = f"Verify your {settings.APP_NAME} account"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Verify Your Email</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #4CAF50;">Welcome to {settings.APP_NAME}!</h2>
            <p>Hello {username},</p>
            <p>Thank you for registering. Please verify your email address by clicking the button below:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" 
                   style="background-color: #4CAF50; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Verify Email Address
                </a>
            </div>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #666;">{verification_url}</p>
            <p>This link will expire in {settings.EMAIL_CONFIRM_EXPIRE_HOURS} hours.</p>
            <p>If you didn't create an account, please ignore this email.</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">© {settings.APP_NAME}</p>
        </div>
    </body>
    </html>
    """

    text_content = f"""
    Welcome to {settings.APP_NAME}!

    Hello {username},

    Thank you for registering. Please verify your email address by visiting:
    {verification_url}

    This link will expire in {settings.EMAIL_CONFIRM_EXPIRE_HOURS} hours.

    If you didn't create an account, please ignore this email.

    © {settings.APP_NAME}
    """

    return await send_email(email, subject, html_content, text_content)