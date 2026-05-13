# create_superuser.py
# IMPORTANT: add project root to Python path
import os
import sys
import django

sys.path.append("/app")

# Set correct settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "RevSource_system.settings")

django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser(
        username="admin",
        email="revolvingsourcesmail@gmail.com",
        password="Cordex@974#254"
    )
    print("Superuser created")
else:
    print("Superuser already exists")