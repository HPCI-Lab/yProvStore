# yProvStore

**yProv** is a provenance service aimed at addressing multi-level provenance as well as reproducibility challenges in climate analytics experiments. It allows scientists to manage provenance information compliant with the [W3C PROV standard](https://www.w3.org/TR/prov-overview/) in a more structured way and navigate and explore the provenance space across multiple dimensions, thus enabling the possibility to get coarse or fine-grained information according to the level of interest.

yProv is a joint project between [University of Trento](https://www.unitn.it) and [CMCC](https://www.cmcc.it).

**yProvStore** is the backend service of yProv, built with FastAPI and designed to handle the storage and retrieval of provenance data. It provides a RESTful API for interacting with provenance information, allowing users to create and read provenance records.

## yProv-CLI

This command-line interface (CLI) allows you to interact with the yProv API directly from your terminal.

### Installation

To install the CLI and its dependencies, navigate to the repository root directory and run the following commands.

```bash
chmod +x prepare_cli.sh
source prepare_cli.sh
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
    yprov --api-url http://your-api-server.com documents list
    ```

2.  **Setting an environment variable:**

    ```bash
    export YPROV_API_URL="http://your-api-server.com"
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

  * **Create a new document** from a JSON file.

    ```bash
    yprov documents create --json-file path/to/your/document.json
    ```

    You can also specify a parent document:

    ```bash
    yprov documents create --json-file new_doc.json --parent-pid <parent_pid_here>
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

### Troubleshooting CLI

If you encounter this issue when running the CLI:

```
command not found: yprov
```

It means that the `yprov` command is not recognized in your terminal. This can happen if the virtual environment is not activated or if the CLI was not set up correctly.
To resolve this, ensure you have run `source prepare_cli.sh` script as described in the [Installation](#installation) section.


## Local Development

This section provides instructions for setting up the yProvStore project for local development. It covers the prerequisites, dependencies installation, database setup, and how to run the application.

### Python version

Before starting with dependencies installation, make sure you have `Python 3.12` installed on your system, as it is a requirement to run the application. You can check your Python version by running:

```bash
python --version
```

If you don't have Python 3.12, you can install it using your system's package manager or download it from the [official Python website](https://www.python.org/downloads/release/python-3128/).

Alternatively, you can also use tools such as `pyenv` to manage multiple Python versions on your system:
```bash
pyenv install 3.12.8
```

### Installing Dependencies

After cloning the repository, you can create a virtualenv and install the required dependencies by simply running:

```bash
uv sync
```

This command will set up the environment and install all required packages as specified in the `pyproject.toml` file.

> **NOTE**: `uv` is a tool that simplifies Python project management, including virtual environments and dependency management. It is designed to be faster and more efficient than traditional tools like `pip` and `virtualenv`.
> 
> If not already installed, you can install `uv` using:
> ```bash
> pip install uv
> ```
>
> All commands run with `uv` will automatically activate the virtual environment.

### Database Setup

The application uses `Alembic` to manage database migrations. To set up the database, run the following command in the root directory of the cloned repository:

```bash
uv run alembic upgrade head
```

This command will apply all pending migrations to your database, ensuring that it is up-to-date with the latest schema changes.

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