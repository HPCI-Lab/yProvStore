import os
from pathlib import Path


APP_TITLE = os.getenv("APP_TITLE", "yProv")
APP_VERSION = os.getenv("APP_VERSION", "2.0.0")
APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "yProv is a provenance service aimed at addressing multi-level provenance as well as reproducibility challenges in climate analytics experiments.")
APP_URL = os.getenv("APP_URL", "http://127.0.0.1:8000")

ON_WINDOWS = os.name == "nt"
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if not DEBUG else "DEBUG")
print(f"Log level set to: {LOG_LEVEL}")

JWT_ENCODING_ALGORITHM = os.getenv("JWT_ENCODING_ALGORITHM", "HS256")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", 60))

DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING", "sqlite:///yprov.db")

TMP_PATH = Path(os.getenv("TMP_PATH", os.path.join(os.path.dirname(__file__), "..", "..", "tmp")))
if not TMP_PATH.exists():
    TMP_PATH.mkdir(parents=True, exist_ok=True)

# === PID Service Settings === #
PID_PREFIX = os.getenv("PID_PREFIX", "21.T11961")
PID_SERVER_URL = os.getenv("PID_SERVER_URL", "https://pidhs.disi.unitn.it:8000")
PID_ADMIN_VALUE_INDEX = int(os.getenv("PID_ADMIN_VALUE_INDEX", 100))
PID_PRIVATE_KEY_PATH = os.getenv("PID_PRIVATE_KEY_PATH", "keys/admpriv.pem")
PID_ADMIN_HANDLE = os.getenv("PID_ADMIN_HANDLE", "0.NA/21.T11961")
PID_ADMIN_HANDLE_INDEX = int(os.getenv("PID_ADMIN_HANDLE_INDEX", 300))
PID_ADMIN_HANDLE_PERMISSIONS = os.getenv("PID_ADMIN_HANDLE_PERMISSIONS", "011111110011")  # TODO: Verify permissions
