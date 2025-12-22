## Application Deployment with Docker

The application can also be deployed using Docker and Docker Compose. This allows you to run the application in a containerized environment, making it easier to manage dependencies and configurations.

The `docker-compose.yml` file in the root directory of the project defines the services required to run the application, which include:
- `api`: The main FastAPI application.
- `minio`: The MinIO server for file storage.
- `postgres`: The PostgreSQL database for storing data useful for managing users and documents.
- `pgbouncer`: A lightweight connection pooler for PostgreSQL. This helps to manage database connections efficiently, especially under high load.
- `pgbouncer-init`: An initialization service that sets up the necessary pgbouncer configuration before starting the pgbouncer service.

To deploy the application using Docker, follow these steps:

1. Make sure you have Docker and Docker Compose installed on your machine.
2. Create a `.env` file in the root directory of the project and define the necessary environment variables.

    ```
    # ================ Required environment variables ================
    # PID Service
    PID_PRIVATE_KEY_PATH=./keys/user_private.pem  # Path to the PID private key file
    # MinIO
    MINIO_ROOT_USER=<your_minio_root_user>
    MINIO_ROOT_PASSWORD=<your_minio_root_password>
    # PostgreSQL
    POSTGRES_USER=<your_db_user>  # Set your desired Postgres user
    POSTGRES_PASSWORD=<your_db_password>  # Set your desired Postgres password
    POSTGRES_DB=yprovstore

    # ================ Required variables for production deployment (with example values) ================
    # General
    JWT_SECRET_KEY=your_secret_key  # Change this to a secure random value
    APP_HOST=myserver.com  # default: 127.0.0.1
    APP_PORT=80  # default: 8000 (this is the public host port, where the API will be accessible)
    APP_PROTOCOL=https  # default: http
    # PID Service
    PID_PREFIX=21.T11961  # default: 21.T11961
    PID_SERVER_URL=https://pidhs.disi.unitn.it:8000  # default: https://pidhs.disi.unitn.it:8000
    PID_ADMIN_HANDLE_INDEX=301  # default: 301
    ```

    > Additional environment variables can be set as needed. See the file `src/application/settings.py` for more details.
3. Run the following command to start the application:

    ```bash
    docker compose up --build  # Add -d to run in detached mode
    ```

4. Now you can access the API documentation at `/docs` on the host and port you specified in the `.env` file.
