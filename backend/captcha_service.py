"""
CAPTCHA Service for high-risk vote verification

This module provides CAPTCHA verification using Google reCAPTCHA v2.
"""

from typing import Optional
import requests
from config import settings


class CaptchaService:
    """Handles CAPTCHA verification using Google reCAPTCHA v2"""

    RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"

    def get_site_key(self) -> str:
        """
        Get the reCAPTCHA site key for frontend rendering.
        """
        if not settings.RECAPTCHA_SITE_KEY:
            raise ValueError("RECAPTCHA_SITE_KEY is not configured")
        return settings.RECAPTCHA_SITE_KEY

    def verify_response(self, recaptcha_token: str, remote_ip: Optional[str] = None) -> bool:
        """
        Verify reCAPTCHA token with Google's API.

        Args:
            recaptcha_token: The reCAPTCHA response token from the frontend
            remote_ip: Optional client IP address for additional verification

        Returns:
            True if verification successful, False otherwise
        """
        if not settings.RECAPTCHA_SECRET_KEY:
            raise ValueError("RECAPTCHA_SECRET_KEY is not configured")

        try:
            data = {
                "secret": settings.RECAPTCHA_SECRET_KEY,
                "response": recaptcha_token
            }
            
            if remote_ip:
                data["remoteip"] = remote_ip

            response = requests.post(
                self.RECAPTCHA_VERIFY_URL,
                data=data,
                timeout=5
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Check if verification was successful
            return result.get("success", False) is True
            
        except (requests.RequestException, ValueError, KeyError) as e:
            # Log error in production
            print(f"reCAPTCHA verification error: {e}")
            return False


# Singleton instance
captcha_service = CaptchaService()
