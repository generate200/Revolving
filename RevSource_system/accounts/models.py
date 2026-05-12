from django.db import models
from django.contrib.auth.models import AbstractUser
from core.utils import profile_upload_path

# Create your models here.
class User(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    is_active = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)

    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('supplier', 'Supplier'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')

    def __str__(self):
        return self.username
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=['email'], name='user_email_idx'),
            models.Index(fields=['role'], name='user_role_idx'),
            models.Index(fields=['is_active'], name='user_active_idx'),
            models.Index(fields=['is_email_verified'], name='user_email_verified_idx'),
        ]

class profile(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name="profile")
    phone=models.CharField(max_length=20,blank=True,null=True)
    profile_pic = models.ImageField(upload_to=profile_upload_path, blank=True, null=True)
    address=models.CharField(max_length=255,blank=True,null=True)
    city=models.CharField(max_length=100,blank=True,null=True)

    def __str__(self):
        return f"{self.user.username}'s profile"