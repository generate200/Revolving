# tokens.py
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import timezone

class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def check_token(self, user, token):
        if not super().check_token(user, token):
            return False
        try:
            ts_b36 = token.split("-")[1]
            ts = int(ts_b36, 36)
        except Exception:
            return False
        # Token is valid for 5 minutes
        now_ts = int(timezone.now().timestamp())
        token_age_seconds = now_ts - (ts * 86400 // (24 * 60 * 60))

        return token_age_seconds <= 300
    
email_verification_token = EmailVerificationTokenGenerator()
    
