import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)


APP_TITLE = os.getenv("APP_TITLE", "yProv")
APP_VERSION = os.getenv("APP_VERSION", "2.0.0")
APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "yProv is a provenance service aimed at addressing multi-level provenance as well as reproducibility challenges in climate analytics experiments.")
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", 8000))
APP_PROTOCOL = os.getenv("APP_PROTOCOL", "http")
APP_URL = os.getenv("APP_URL", f"{APP_PROTOCOL}://{APP_HOST}:{APP_PORT}")

ON_WINDOWS = os.name == "nt"
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if not DEBUG else "DEBUG")
print(f"Log level set to: {LOG_LEVEL}")

JWT_ENCODING_ALGORITHM = os.getenv("JWT_ENCODING_ALGORITHM", "HS256")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", 60))

DB_CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING", "sqlite+aiosqlite:///yprov.db")

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
PID_ADMIN_HANDLE = os.getenv("PID_ADMIN_HANDLE", f"{PID_PREFIX}/ADMINLIST")
PID_ADMIN_HANDLE_INDEX = int(os.getenv("PID_ADMIN_HANDLE_INDEX", 301))
PID_ADMIN_HANDLE_PERMISSIONS = os.getenv("PID_ADMIN_HANDLE_PERMISSIONS", "110001110001")
# PID_SERVICE_MAX_CONCURRENT_REQUESTS = int(os.getenv("PID_SERVICE_MAX_CONCURRENT_REQUESTS", 10))  # Remember this applies to each process if using multiple workers

# === MinIO Settings === #
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "yprovstore-minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")  # TODO: is it okay to use root user?
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "yprov-documents")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() in ("true", "1", "yes")
MINIO_REGION = os.getenv("MINIO_REGION", None)

ARTIFACTS_MINIO_ENDPOINT = os.getenv("ARTIFACTS_MINIO_ENDPOINT", MINIO_ENDPOINT)
ARTIFACTS_MINIO_ACCESS_KEY = os.getenv("ARTIFACTS_MINIO_ROOT_USER", MINIO_ACCESS_KEY)  # TODO: is it okay to use root user?
ARTIFACTS_MINIO_SECRET_KEY = os.getenv("ARTIFACTS_MINIO_ROOT_PASSWORD", MINIO_SECRET_KEY)
ARTIFACTS_MINIO_BUCKET = os.getenv("ARTIFACTS_MINIO_BUCKET", "yprov-artifacts")
ARTIFACTS_MINIO_SECURE = os.getenv("ARTIFACTS_MINIO_SECURE", "False").lower() in ("true", "1", "yes")
ARTIFACTS_MINIO_REGION = os.getenv("ARTIFACTS_MINIO_REGION", None)
# URL of MinIO endpoint exposed to clients (used only if PROXY_ARTIFACT_STORAGE is False to generate presigned URLs for artifact upload/download)
ARTIFACTS_PUBLIC_MINIO_ENDPOINT = os.getenv("ARTIFACTS_PUBLIC_MINIO_ENDPOINT", None)  # Set it if different from ARTIFACTS_MINIO_ENDPOINT (which may only be internal)

# If False, yProvStore will proxy artifact storage requests and use the storage (local or MinIO) directly
PROXY_ARTIFACT_STORAGE = os.getenv("PROXY_ARTIFACT_STORAGE", "True").lower() in ("true", "1", "yes")
if USE_LOCAL_FILE_STORAGE_SERVICE and not PROXY_ARTIFACT_STORAGE:
    raise ValueError("Cannot use local file storage service when PROXY_ARTIFACT_STORAGE is False.")
if not PROXY_ARTIFACT_STORAGE and not ARTIFACTS_MINIO_ENDPOINT:
    raise ValueError("ARTIFACTS_MINIO_ENDPOINT must be set if PROXY_ARTIFACT_STORAGE is False.")
if PROXY_ARTIFACT_STORAGE and ARTIFACTS_PUBLIC_MINIO_ENDPOINT:
    # When proxying storage, clients should not access MinIO directly
    raise ValueError("ARTIFACTS_PUBLIC_MINIO_ENDPOINT should not be set if PROXY_ARTIFACT_STORAGE is True.")

# Validate minio endpoint name does not contain underscores
if MINIO_ENDPOINT and '_' in MINIO_ENDPOINT.split(':')[0]:
    raise ValueError("MINIO_ENDPOINT cannot contain underscores in the hostname part.")
