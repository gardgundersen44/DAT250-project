import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "secret"  # TODO: Use this with wtforms
    SQLITE3_DATABASE_PATH = "sqlite3.db"  # Path relative to the Flask instance folder
    UPLOADS_FOLDER_PATH = "uploads"  # Path relative to the Flask instance folder
    ALLOWED_EXTENSIONS = {}  # TODO: Might use this at some point, probably don't want people to upload any file type
    WTF_CSRF_ENABLED = False  # TODO: I should probably implement this wtforms feature, but it's not a priority
    RECAPTCHA_PUBLIC_KEY = os.environ.get("RECAPTCHA_PUBLIC_KEY") or "6LdLHpgoAAAAAMxOH6Rs15vN7Y7ppUvar3K0RWwq"
    RECAPTCHA_PRIVATE_KEY = os.environ.get("RECAPTCHA_PRIVATE_KEY")  or "6LdLHpgoAAAAAGIiiXD90LwZCj1dlGn23Gjq7Nk7"