import os
import time

from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def save_user_photo(file_storage, user_id):
    if not file_storage or not file_storage.filename:
        return None
    filename = secure_filename(file_storage.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_PHOTO_EXT:
        raise ValueError("Photo must be a JPG, PNG, or WEBP file.")
    name = "user_%s_%s%s" % (user_id, int(time.time()), ext)
    folder = os.path.join(current_app.static_folder, "uploads", "users")
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, name))
    return name
