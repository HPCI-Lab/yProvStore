# yProvStore

**yProv** is a provenance service aimed at addressing multi-level provenance as well as reproducibility challenges in climate analytics experiments. It allows scientists to manage provenance information compliant with the [W3C PROV standard](https://www.w3.org/TR/prov-overview/) in a more structured way and navigate and explore the provenance space across multiple dimensions, thus enabling the possibility to get coarse or fine-grained information according to the level of interest.

yProv is a joint project between [University of Trento](https://www.unitn.it) and [CMCC](https://www.cmcc.it).

**yProvStore** is the backend service of yProv, built with FastAPI and designed to handle the storage and retrieval of provenance data. It provides a RESTful API for interacting with provenance information, allowing users to create and read provenance records, manage document metadata, and handle permissions.

## Table of Contents

- [yProvStore](#yprovstore)
  - [Table of Contents](#table-of-contents)
  - [Local Development](#local-development)
    - [TL;DR: Quick Setup & Installation](#tldr-quick-setup--installation)
    - [Python version](#python-version)
    - [Installing Dependencies](#installing-dependencies)
    - [Database Setup](#database-setup)
    - [Environment Variables (Optional)](#environment-variables-optional)
    - [Running the Application](#running-the-application)
    - [Available Endpoints](#available-endpoints)
    - [Troubleshooting](#troubleshooting)
      - [1. Empty database error](#1-empty-database-error)
      - [2. Missing PID private key error](#2-missing-pid-private-key-error)
      - [3. MinIO bucket error](#3-minio-bucket-error)
  - [Application Deployment with Docker](#application-deployment-with-docker)
  - [yProv-CLI](#yprov-cli)
    - [Installation](#installation)
    - [Basic Command Structure](#basic-command-structure)
    - [Available Commands](#available-commands)
    - [Configuration](#configuration)
    - [Authentication](#authentication)
    - [Managing Documents](#managing-documents)
    - [Managing Document Permissions](#managing-document-permissions)
    - [Managing Document Metadata](#managing-document-metadata)
    - [Graph Operations on Documents](#graph-operations-on-documents)
    - [Blockchain Operations](#blockchain-operations)
    - [Managing PIDs](#managing-pids)
    - [Managing Artifacts](#managing-artifacts)
    - [Troubleshooting CLI](#troubleshooting-cli)

## Local Development

This section provides instructions for setting up the yProvStore project for local development. It covers the prerequisites, dependencies installation, database setup, and how to run the application.

For a quick setup, you can follow the [TL;DR: Quick Setup & Installation](#tldr-quick-setup--installation) section below, otherwise, you can read through the detailed steps provided in the following sections.

### TL;DR: Quick Setup & Installation

1. **Clone the repository:**
    ```bash
    git clone https://github.com/HPCI-Lab/yProvStore
    cd yProvStore
    ```

2. **Install `uv` (optional, recommended):**
    ```bash
    pip install uv
    ```

3. **Install Python 3.12** (if not already installed).
    You can use `pyenv` or `uv` to manage Python versions:
    ```bash
    uv install python 3.12
    ```

4. **Install dependencies:**
    ```bash
    uv sync
    ```

5. **Run database migrations:**
    ```bash
    uv run alembic upgrade head
    ```

5. **Create a `.env` file** in the root directory to set necessary environment variables. For local testing, you can use:
    ```env
    USE_LOCAL_PID_SERVICE=True  # Uses a mocked version of the PID service for local testing
    USE_LOCAL_FILE_STORAGE_SERVICE=True  # Uses local file storage instead of MinIO for local testing
    ```

    Or, if you want to connect to the real PID service, provide the path to your private key:
    ```env
    PID_PRIVATE_KEY_PATH=keys/user_private.pem
    USE_LOCAL_PID_SERVICE=False
    USE_LOCAL_FILE_STORAGE_SERVICE=True  # Still using local file storage for testing

    # Other optional variables for PID service if you need to override defaults
    PID_PREFIX=21.T11961  # default value
    PID_SERVER_URL=https://pidhs.disi.unitn.it:8000  # default value
    PID_ADMIN_HANDLE_INDEX=301  # default value
    ```

    > If you want to use MinIO for file storage, set the following variables instead of `USE_LOCAL_FILE_STORAGE_SERVICE=True`:
    > ```env
    > MINIO_ROOT_USER=minioadmin
    > MINIO_ROOT_PASSWORD=minioadmin
    > MINIO_BUCKET_NAME=yprov-documents
    > MINIO_ENDPOINT=localhost:9000  # Change to your MinIO server (for example within docker it whould be `yprovstore-minio:9000`, which is also the default value)
    > MINIO_SECURE=False  # !! IMPORTANT: if testing locally you need to disable HTTPS
    > ```

6. **Start the application:**
    ```bash
    uv run src/run.py
    ```

    > **NOTE**: If you see errors, check the [Troubleshooting](#troubleshooting) and [Environment Variables](#environment-variables-optional) sections for common issues.

7. **Access the API docs:**  
    Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser.

    > For CLI usage, refer to the [yProvStore CLI](#yprovstore-cli) section below.

---

### Python version

Before starting with dependencies installation, make sure you have `Python 3.12` installed on your system, as it is a requirement to run the application. You can check your Python version by running:

```bash
python --version
```

If you don't have Python 3.12, you can install it using your system's package manager or download it from the [official Python website](https://www.python.org/downloads/release/python-3128/).

Alternatively, you can also use tools such as `pyenv` or `uv` to manage multiple Python versions on your system:
```bash
uv install python 3.12
```
> **NOTE**: `uv` is a tool that simplifies Python project management, including virtual environments and dependency management. It is designed to be faster and more efficient than traditional tools like `pip` and `virtualenv`.
> 
> If not already installed, you can install `uv` using:
> ```bash
> pip install uv
> ```

### Installing Dependencies

After cloning the repository, you can create a virtualenv and install the required dependencies by simply running:

```bash
uv sync
```

This command will set up the environment and install all required packages as specified in the `pyproject.toml` file.

> **NOTE**: All commands run with `uv` will automatically activate the virtual environment, so you don't need to manually activate it. This is one of the advantages of using `uv` for managing your Python projects.

### Database Setup

The application uses `Alembic` to manage database migrations. To set up the database, run the following command in the root directory of the cloned repository:

```bash
uv run alembic upgrade head
```

This command will apply all pending migrations to your database, ensuring that it is up-to-date with the latest schema changes.

### Environment Variables (Optional)

If you need to change any environment variables, you can create a `.env` file in the root directory of the project. This file can contain any environment-specific configurations, such as database connection strings or API keys. Some usefule environment variables are:

```env
LOG_LEVEL=INFO  # Change to DEBUG for more verbose logging
PID_PRIVATE_KEY_PATH=/path/to/private/key.pem  # Path to the private key for PID service (will throw an error if not set and USE_LOCAL_PID_SERVICE is False)
USE_LOCAL_PID_SERVICE=True  # Set to True to use the local PID service for testing purposes (default is False)
USE_LOCAL_FILE_STORAGE_SERVICE=True  # Set to True to use local file storage instead of MinIO (default is False)
```

The other environment variables can be seen in the `src/application/settings.py` file, where they are defined with default values. You can override these defaults by setting them in your `.env` file.


### Running the Application

To run the application, go to the root directory of the cloned repository and use the following command:

```bash
uv run src/run.py
```

Thanks to `uv`, this command will automatically activate the virtual environment and run the FastAPI application.

You can now go to your web browser and navigate to `http://localhost:8000/docs` to access the interactive API documentation provided by FastAPI. This interface allows you to test the API endpoints and explore the available functionality.

### Available Endpoints

![OpenAPI Endpoints 1](documentation/images/openapi_1.png)
![OpenAPI Endpoints 2](documentation/images/openapi_2.png)

### Troubleshooting

#### 1. Empty database error

If you encounter this error when running the application:

```
Exception: Database is empty (no tables), verify your configuration and migrations.
```

It means that the database has not been initialized yet. To resolve this, ensure you have run the Alembic migrations as described in the [Database Setup](#database-setup) section above.

-----

#### 2. Missing PID private key error

If you encounter this error when running the application:

```
FileNotFoundError: PID private key file not found: keys/admpriv.pem. Please provide it or set USE_LOCAL_PID_SERVICE to True if you only need to test locally.
```

It means that the application is trying to use the PID service, but the private key file is missing. To resolve this, you have two options:

1. Provide the missing private key file at the specified path (`keys/admpriv.pem`) - or set the key path `PID_PRIVATE_KEY_PATH` in your `.env` file.
2. Set the `USE_LOCAL_PID_SERVICE` environment variable to `True` in your `.env` file if you only need to test locally.

More details on this can be found in the [Environment Variables](#environment-variables-optional) section above.

-----

#### 3. MinIO bucket error

```
Uploading document from JSON file: examples/prov_valid.json
Error 503:
{'description': 'Failed to ensure storage bucket.'}
❌ Error : No response.
```

If you encounter this error when trying to upload a document, it means that the bucket was not created on MinIO or MinIO is not reachable by the application. To resolve this, you need to first check whether the bucket defined in the `MINIO_BUCKET` environment variable has been created. You can do this by accessing the MinIO web interface at `http://localhost:9001` and logging in with the root user and password you defined in the `.env` file (default is `minioadmin` with password `minioadmin`). Once logged in, create a new bucket with the name specified in `MINIO_BUCKET` (default name is `yprov-documents`) if not existing. Alternatively, you need to check if the MinIO server is running and accessible from the application.

You may be missing `MINIO_SECURE=False` in your `.env` file if you are using an insecure connection between the application and the MinIO server (meaning no cls certificates have been configured), which is common in local testing.

## Application Deployment with Docker

The application can also be deployed using Docker and Docker Compose. Check the [DEPLOYMENT.md](DEPLOYMENT.md) file for detailed instructions on how to set up and run the application using Docker.

## yProvStore CLI

This command-line interface (CLI) allows you to interact with the yProv API directly from your terminal.

You can install it and see the available commands in its dedicated repository: [yProvStore-cli](https://github.com/HPCI-Lav/yProvStore-cli)
