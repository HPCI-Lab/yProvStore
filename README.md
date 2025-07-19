# yProvStore

**yProv** is a provenance service aimed at addressing multi-level provenance as well as reproducibility challenges in climate analytics experiments. It allows scientists to manage provenance information compliant with the [W3C PROV standard](https://www.w3.org/TR/prov-overview/) in a more structured way and navigate and explore the provenance space across multiple dimensions, thus enabling the possibility to get coarse or fine-grained information according to the level of interest.

yProv is a joint project between [University of Trento](https://www.unitn.it) and [CMCC](https://www.cmcc.it).

**yProvStore** is the backend service of yProv, built with FastAPI and designed to handle the storage and retrieval of provenance data. It provides a RESTful API for interacting with provenance information, allowing users to create and read provenance records.

## Table of Contents

- [yProvStore](#yprovstore)
  - [Table of Contents](#table-of-contents)
  - [Local Development](#local-development)
    - [Python version](#python-version)
    - [Installing Dependencies](#installing-dependencies)
    - [Database Setup](#database-setup)
    - [Running the Application](#running-the-application)
    - [Troubleshooting](#troubleshooting)
  - [yProv-CLI](#yprov-cli)
    - [Installation](#installation)
    - [Basic Command Structure](#basic-command-structure)
    - [Available Commands](#available-commands)
    - [Configuration](#configuration)
    - [Authentication](#authentication)
    - [Managing Documents](#managing-documents)
    - [Troubleshooting CLI](#troubleshooting-cli)

## Local Development

This section provides instructions for setting up the yProvStore project for local development. It covers the prerequisites, dependencies installation, database setup, and how to run the application.

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
LOG_LEVEL=DEBUG  # Default: INFO
PID_PRIVATE_KEY_PATH=/path/to/private/key.pem  # Path to the private key for PID service (will throw an error if not set and USE_LOCAL_PID_SERVICE is False)
USE_LOCAL_PID_SERVICE=True  # Set to True to use the local PID service for testing purposes (default is False)
```

The other environment variables can be seen in the `src/application/settings.py` file, where they are defined with default values. You can override these defaults by setting them in your `.env` file.


### Running the Application

To run the application, go to the root directory of the cloned repository and use the following command:

```bash
uv run src/run.py
```

Thanks to `uv`, this command will automatically activate the virtual environment and run the FastAPI application.

You can now go to your web browser and navigate to `http://localhost:8000/docs` to access the interactive API documentation provided by FastAPI. This interface allows you to test the API endpoints and explore the available functionality.

### Troubleshooting

If you encounter this error when running the application:

```
Exception: Database is empty (no tables), verify your configuration and migrations.
```

It means that the database has not been initialized yet. To resolve this, ensure you have run the Alembic migrations as described in the [Database Setup](#database-setup) section above.

-----

If you encounter this error when running the application:

```
FileNotFoundError: PID private key file not found: keys/admpriv.pem. Please provide it or set USE_LOCAL_PID_SERVICE to True if you only need to test locally.
```

It means that the application is trying to use the PID service, but the private key file is missing. To resolve this, you have two options:

1. Provide the missing private key file at the specified path (`keys/admpriv.pem`) - or set the key path `PID_PRIVATE_KEY_PATH` in your `.env` file.
2. Set the `USE_LOCAL_PID_SERVICE` environment variable to `True` in your `.env` file if you only need to test locally.

More details on this can be found in the [Environment Variables](#environment-variables-optional) section above.

## yProv-CLI

This command-line interface (CLI) allows you to interact with the yProv API directly from your terminal.

### Installation

To install the CLI and its dependencies, navigate to the repository root directory and run the following commands.

#### Linux and macOS

```bash
chmod +x prepare_cli.sh
source prepare_cli.sh
```

#### Windows
```bash
call prepare_cli.bat
```

This will set up the CLI environment by initiating the virtual environment and making the `yprov` command available in your terminal.

> **Note**: After you have finished using the CLI, you can deactivate the virtual environment by running `deactivate` in your terminal.


**Prepare the CLI before its usage:**

In general, remember to always run `source prepare_cli.sh` before using the CLI to ensure that the environment is set up correctly.
This should be done not only when you first install the CLI, but also whenever you open a new terminal session where you want to use the CLI.


### Basic Command Structure

The basic structure of the CLI commands is as follows:

```bash
yprov <command> [options]
```

Where `<command>` is the specific action you want to perform, such as `auth`, `documents`, etc., and `[options]` are additional parameters for that command.

### Available Commands

```bash
yprov check
yprov auth signup
yprov auth login
yprov auth verify
yprov auth logout
yprov documents create --json-file <path/to/document.json> [--parent-pid <parent_pid>]
yprov documents list
yprov documents get <document_pid>
yprov documents download <document_pid> [--output-folder <path>] [--output <file_path>]
```

Each of these commands is better explained below.

However, you can also examine the help message for each command by running:

```bash
yprov <command> --help
```

-----

### Configuration

The CLI defaults to connecting to `http://127.0.0.1:8000`. You can specify a different API server URL in two ways:

1.  **Using the `--api-url` option:**

    ```bash
    yprov --api-url http://your-api-server.com:8000 check
    ```

2.  **Setting an environment variable:**

    ```bash
    export YPROV_API_URL="http://your-api-server.com:8000"
    ```

    You can then check the status of the API server with:

    ```bash
    yprov check
    ```

-----

### Authentication

First, you need to register and log in to get an access token. The token is stored locally and used for all authenticated requests.

  * **Sign up** for a new account.
    ```bash
    yprov auth signup
    ```
  * **Log in** to your account to get an access token.
    ```bash
    yprov auth login
    ```
  * **Verify** that your token is valid and see which user you are logged in as.
    ```bash
    yprov auth verify
    ```
  * **Log out** by deleting your local access token.
    ```bash
    yprov auth logout
    ```

-----


### Managing Documents

Once authenticated, you can create, list, and download provenance documents.

  * **Create a new document** from a JSON file or a JSON string (only one of these options is allowed at a time).

    ```bash
    # From a file:
    yprov documents create --json-file examples/doc.json

    # Or from an inline JSON string:
    yprov documents create --value "{\"title\":\"My Doc\",\"owner_email\":\"me@example.com\"}"
    ```

    You can also specify a parent document in either case:

    ```bash
    yprov documents create \
      --json-file examples/doc.json \
      --parent-pid <parent_pid_here>
    ```

  * **List all available documents**.

    ```bash
    yprov documents list
    ```

  * **Get detailed information** for a specific document by its PID.

    ```bash
    yprov documents get <your_document_pid>
    ```

  * **Download a document's file**.

    ```bash
    Usage: yprov documents download [OPTIONS] PID

    Download a document file by its PID.

    Options:
      -o, --output FILE          Full path to save the file (e.g.,
                                'my_dir/my_doc.json'). This overrides --output-folder.
      --output-folder DIRECTORY  Folder to save the file in. The filename will
                                default to the document's PID.
    ```

    * Save to the current directory (e.g., `<pid>.prov`):

      ```bash
      yprov documents download <your_document_pid>
      ```

    * Save to a specific folder:

      ```bash
      yprov documents download <your_document_pid> --output-folder /path/to/downloads
      ```

    * Save with a specific file name and path:

      ```bash
      yprov documents download <your_document_pid> --output /path/to/my_doc.json
      ```


  * **List all available documents**.

    ```bash
    yprov documents list
    ```

  * **Get detailed information** for a specific document by its PID.

    ```bash
    yprov documents get <your_document_pid>
    ```

  * **Download a document's file**.

      ```bash
      Usage: yprov documents download [OPTIONS] PID
      
      Download a document file by its PID.
      
      Options:
        -o, --output FILE          Full path to save the file (e.g.,
                                  'my_dir/my_doc.json'). This overrides --output-
                                  folder.
        --output-folder DIRECTORY  Folder to save the file in. The filename will
                                  default to the document's PID.
      ```
      
      * Save to the current directory (e.g., `<pid>.prov`):
      
        ```bash
        yprov documents download <your_document_pid>
        ```
      * Save to a specific folder:
        ```bash
        yprov documents download <your_document_pid> --output-folder /path/to/downloads
        ```
      * Save with a specific file name and path:
        ```bash
        yprov documents download <your_document_pid> --output /path/to/my_doc.json
        ```

-----

### Managing PIDs

`yProvStore` additionally provides some proxy methods to retrieve PID records directly from the underlying PID service (Handle System).

The `pids` group lets you list and retrieve PID records from your PID service.

* **List PIDs** (with optional pagination)

```bash
  yprov pids list [OPTIONS]
```

Options:

* `--page INTEGER`       Page number (zero‑indexed). Default: `0`
* `--page-size INTEGER`   Number of items per page. Default: `25`

Examples:

* List the first page (25 items):

  ```bash
  yprov pids list
  ```
* List page 2 (zero‑indexed, i.e. the third page) with 50 items per page:

  ```bash
  yprov pids list --page 2 --page-size 50
  ```

- **Get a PID record** (by prefix/id or by id only)

  ```bash
  yprov pids get <PID>
  ```

  The `<PID>` argument can be provided in two ways:

  * **`prefix/id`** — explicitly specify both prefix and identifier
  * **`id`** — omit the prefix, and the service will use your application’s default prefix

  Examples:

  * Retrieve a record with an explicit prefix:

    ```bash
    yprov pids get myprefix/1234
    ```
  * Retrieve a record using the default prefix:

    ```bash
    yprov pids get 1234
    ```


### Troubleshooting CLI

If you encounter this issue when running the CLI:

```
command not found: yprov
```

It means that the `yprov` command is not recognized in your terminal. This can happen if the virtual environment is not activated or if the CLI was not set up correctly.
To resolve this, ensure you have run `source prepare_cli.sh` script as described in the [Installation](#installation) section.

