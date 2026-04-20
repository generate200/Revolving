import os
import uuid
from django.utils.text import slugify


def generate_upload_path(instance, filename, folder='uploads'):
    ext = filename.split('.')[-1].lower()
    name = slugify(getattr(instance, 'name', 'item'))
    unique_id = uuid.uuid4().hex[:8]

    filename = f"{name}-{unique_id}.{ext}"
    return os.path.join(folder, filename)


# ✅ IMPORTANT: NO INNER FUNCTION
def product_upload_path(instance, filename):
    return generate_upload_path(instance, filename, 'products/images')

def profile_upload_path(instance, filename):
    return generate_upload_path(instance, filename, 'accounts/profile_pics')