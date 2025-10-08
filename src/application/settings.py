import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)


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
DB_MAX_POOL_SIZE = int(os.getenv("DB_MAX_POOL_SIZE", 20))  # Remember this applies to each process if using multiple workers
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", -1))
DB_TIMEOUT = int(os.getenv("DB_TIMEOUT", 5))

TMP_PATH = Path(os.getenv("TMP_PATH", os.path.join(os.path.dirname(__file__), "..", "..", "tmp")))
if not TMP_PATH.exists():
    TMP_PATH.mkdir(parents=True, exist_ok=True)

USE_LOCAL_PID_SERVICE = os.getenv("USE_LOCAL_PID_SERVICE", "False").lower() in ("true", "1", "yes")
USE_LOCAL_FILE_STORAGE_SERVICE = os.getenv("USE_LOCAL_FILE_STORAGE_SERVICE", "False").lower() in ("true", "1", "yes")

# === PID Service Settings === #
PID_PREFIX = os.getenv("PID_PREFIX", "21.T11961")
PID_SERVER_URL = os.getenv("PID_SERVER_URL", "https://pidhs.disi.unitn.it:8000")
PID_ADMIN_VALUE_INDEX = int(os.getenv("PID_ADMIN_VALUE_INDEX", 100))
PID_PRIVATE_KEY_PATH = os.getenv("PID_PRIVATE_KEY_PATH", "keys/privkey.pem")
PID_ADMIN_HANDLE = os.getenv("PID_ADMIN_HANDLE", "21.T11961/ADMINLIST")
PID_ADMIN_HANDLE_INDEX = int(os.getenv("PID_ADMIN_HANDLE_INDEX", 301))
PID_ADMIN_HANDLE_PERMISSIONS = os.getenv("PID_ADMIN_HANDLE_PERMISSIONS", "110001110001")
# PID_SERVICE_MAX_CONCURRENT_REQUESTS = int(os.getenv("PID_SERVICE_MAX_CONCURRENT_REQUESTS", 10))  # Remember this applies to each process if using multiple workers

# === MinIO Settings === #
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "yprovstore-minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")  # TODO: is it okay to use root user?
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "yprov-documents")
MINIO_SECURE = os.getenv("MINIO_SECURE", "True").lower() in ("true", "1", "yes")
MINIO_REGION = os.getenv("MINIO_REGION", None)

# Validate minio endpoint name does not contain underscores
if MINIO_ENDPOINT and '_' in MINIO_ENDPOINT.split(':')[0]:
    raise ValueError("MINIO_ENDPOINT cannot contain underscores in the hostname part.")
