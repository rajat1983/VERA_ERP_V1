import os
import time

from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_BYTES = 2 * 1024 * 1024


def _ext_ok(filename, allowed):
    filename = secure_filename(filename or "")
    return os.path.splitext(filename)[1].lower() in allowed


def _read_size(file_storage):
    stream = file_storage.stream
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)
    head = stream.read(12)
    stream.seek(0)
    return size, head


def _magic_ok(head, ext):
    if ext in (".jpg", ".jpeg") and head.startswith(b"\xff\xd8\xff"):
        return True
    if ext == ".png" and head.startswith(b"\x89PNG"):
        return True
    if ext == ".webp" and head.startswith(b"RIFF") and b"WEBP" in head[:12]:
        return True
    return False


def save_user_photo(file_storage, user_id):
    return save_image(file_storage, ("uploads", "users"), "user_%s" % user_id)


def save_product_image(file_storage, tenant_id):
    return save_image(file_storage, ("uploads", "products"), "t%s" % int(tenant_id))


def save_image(file_storage, folder_parts, stem, allowed=None):
    if not file_storage or not file_storage.filename:
        return None
    allowed = allowed or ALLOWED_PHOTO_EXT
    if not _ext_ok(file_storage.filename, allowed):
        raise ValueError("Image must be a JPG, PNG, or WEBP file.")
    ext = os.path.splitext(secure_filename(file_storage.filename))[1].lower()
    size, head = _read_size(file_storage)
    if size > MAX_IMAGE_BYTES:
        raise ValueError("Image must be 2 MB or smaller.")
    if size and not _magic_ok(head, ext):
        raise ValueError("Image file does not match its extension.")
    name = "%s_%s%s" % (stem, int(time.time()), ext)
    folder = os.path.join(current_app.static_folder, *folder_parts)
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, name))
    return name
