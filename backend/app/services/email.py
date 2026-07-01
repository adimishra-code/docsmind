"""Async email service using aiosmtplib with HTML templates."""
from __future__ import annotations

import ssl
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTML Email Templates
# ---------------------------------------------------------------------------

def _base_html(title: str, body_html: str) -> str:
    """Wrap content in a polished base email template."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #0f0f13; color: #e2e8f0; }}
    .wrapper {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
    .card {{ background: #1a1a2e; border: 1px solid #2d2d44; border-radius: 16px; overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%); padding: 40px 40px 32px; text-align: center; }}
    .logo {{ font-size: 28px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; }}
    .logo span {{ color: #c4b5fd; }}
    .body {{ padding: 40px; }}
    .title {{ font-size: 24px; font-weight: 700; color: #f1f5f9; margin-bottom: 12px; }}
    .text {{ font-size: 16px; color: #94a3b8; line-height: 1.7; margin-bottom: 24px; }}
    .btn {{ display: inline-block; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #ffffff !important; text-decoration: none; padding: 14px 32px; border-radius: 10px; font-size: 16px; font-weight: 600; letter-spacing: 0.2px; }}
    .btn:hover {{ opacity: 0.9; }}
    .divider {{ border: none; border-top: 1px solid #2d2d44; margin: 28px 0; }}
    .small {{ font-size: 13px; color: #64748b; line-height: 1.6; }}
    .footer {{ text-align: center; padding: 24px 40px; color: #475569; font-size: 13px; }}
    .code-box {{ background: #0f0f13; border: 1px solid #3730a3; border-radius: 10px; padding: 20px; text-align: center; margin: 24px 0; }}
    .code {{ font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #818cf8; font-family: monospace; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="card">
      <div class="header">
        <div class="logo">Docs<span>Mind</span></div>
      </div>
      <div class="body">
        {body_html}
      </div>
      <div class="footer">
        &copy; 2026 DocsMind. All rights reserved.<br/>
        This email was sent to you because you have an account with DocsMind.
      </div>
    </div>
  </div>
</body>
</html>"""


def _verification_email_html(verification_url: str, user_email: str) -> str:
    body = f"""
      <h1 class="title">Verify your email address</h1>
      <p class="text">
        Welcome to <strong>DocsMind</strong>! We're excited to have you on board.
        Please verify your email address to activate your account and start exploring
        the power of AI-driven document intelligence.
      </p>
      <div style="text-align: center; margin: 32px 0;">
        <a href="{verification_url}" class="btn">✓ Verify Email Address</a>
      </div>
      <hr class="divider" />
      <p class="small">
        This link expires in <strong>24 hours</strong>. If you didn't create a DocsMind account,
        you can safely ignore this email.<br/><br/>
        Or copy and paste this URL into your browser:<br/>
        <span style="color: #818cf8; word-break: break-all;">{verification_url}</span>
      </p>
    """
    return _base_html("Verify your DocsMind email", body)


def _welcome_email_html(user_name: str) -> str:
    display_name = user_name.split("@")[0].capitalize() if "@" in user_name else user_name
    body = f"""
      <h1 class="title">Welcome to DocsMind, {display_name}! 🎉</h1>
      <p class="text">
        Your email has been verified and your account is now fully active.
        You can now upload documents, ask questions, and leverage the full
        power of DocsMind's AI-driven knowledge engine.
      </p>
      <div style="text-align: center; margin: 32px 0;">
        <a href="{settings.FRONTEND_URL}/login" class="btn">→ Go to Dashboard</a>
      </div>
      <hr class="divider" />
      <p class="small">
        Need help? Check out our documentation or reach out to our support team.
      </p>
    """
    return _base_html("Welcome to DocsMind!", body)


def _password_reset_email_html(reset_url: str) -> str:
    body = f"""
      <h1 class="title">Reset your password</h1>
      <p class="text">
        We received a request to reset the password for your DocsMind account.
        Click the button below to set a new password. This link expires in <strong>1 hour</strong>.
      </p>
      <div style="text-align: center; margin: 32px 0;">
        <a href="{reset_url}" class="btn">🔑 Reset Password</a>
      </div>
      <hr class="divider" />
      <p class="small">
        If you didn't request a password reset, you can safely ignore this email.
        Your password will not change.<br/><br/>
        Or copy and paste this URL:<br/>
        <span style="color: #818cf8; word-break: break-all;">{reset_url}</span>
      </p>
    """
    return _base_html("Reset your DocsMind password", body)


# ---------------------------------------------------------------------------
# Core send function
# ---------------------------------------------------------------------------

async def _send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str | None = None,
) -> bool:
    """Send an email via SMTP. Returns True on success, False on failure."""
    if not settings.EMAILS_ENABLED:
        logger.info("Emails disabled — skipping send to %s", to_email)
        return True

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured — skipping email")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email

    if text_content:
        msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        if settings.SMTP_TLS:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
            )
        else:
            context = ssl.create_default_context()
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                tls_context=context,
            )
        logger.info("Email sent successfully to %s (subject: %s)", to_email, subject)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)
        return False


# ---------------------------------------------------------------------------
# Public send functions
# ---------------------------------------------------------------------------

async def send_verification_email(to_email: str, token: str) -> bool:
    """Send an email verification link to a newly registered user."""
    verification_url = (
        f"{settings.FRONTEND_URL}/verify-email?token={token}"
    )
    html = _verification_email_html(verification_url, to_email)
    text = (
        f"Welcome to DocsMind!\n\n"
        f"Please verify your email address by visiting:\n{verification_url}\n\n"
        f"This link expires in 24 hours."
    )
    return await _send_email(
        to_email=to_email,
        subject="Verify your DocsMind email address",
        html_content=html,
        text_content=text,
    )


async def send_welcome_email(to_email: str, full_name: str | None = None) -> bool:
    """Send a welcome email after successful email verification."""
    html = _welcome_email_html(full_name or to_email)
    text = (
        f"Welcome to DocsMind!\n\n"
        f"Your email has been verified. You can now log in at:\n"
        f"{settings.FRONTEND_URL}/login\n\n"
        f"Enjoy using DocsMind!"
    )
    return await _send_email(
        to_email=to_email,
        subject="Welcome to DocsMind! 🎉",
        html_content=html,
        text_content=text,
    )


async def send_password_reset_email(to_email: str, token: str) -> bool:
    """Send a password reset link."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    html = _password_reset_email_html(reset_url)
    text = (
        f"Password Reset Request\n\n"
        f"Reset your password by visiting:\n{reset_url}\n\n"
        f"This link expires in 1 hour. If you didn't request this, ignore this email."
    )
    return await _send_email(
        to_email=to_email,
        subject="Reset your DocsMind password",
        html_content=html,
        text_content=text,
    )
