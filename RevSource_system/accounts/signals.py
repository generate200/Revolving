from django.dispatch import Signal
from django.dispatch import receiver
from django.contrib.auth import get_user_model


email_verified = Signal()
User = get_user_model()

@receiver(email_verified)
def activate_user(sender, user, **kwargs):
    user.is_active = True
    user.save()