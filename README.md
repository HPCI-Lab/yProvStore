# yProvStore

**yProv** is a provenance service aimed at addressing multi-level provenance as well as reproducibility challenges in climate analytics experiments. It allows scientists to manage provenance information compliant with the [W3C PROV standard](https://www.w3.org/TR/prov-overview/) in a more structured way and navigate and explore the provenance space across multiple dimensions, thus enabling the possibility to get coarse or fine-grained information according to the level of interest.

yProv is a joint project between [University of Trento](https://www.unitn.it) and [CMCC](https://www.cmcc.it).

**yProvStore** is the backend service of yProv, built with FastAPI and designed to handle the storage and retrieval of provenance data. It provides a RESTful API for interacting with provenance information, allowing users to create and read provenance records, manage document metadata, and handle permissions.

## Table of Contents

- [yProvStore](#yprovstore)
  - [Table of Contents](#table-of-contents)
  - [Local Development](#local-development)
    - [Python version](#python-version)
    - [Installing Dependencies](#installing-dependencies)
    - [Database Setup](#database-setup)
    - [Environment Variables (Optional)](#environment-variables-optional)
    - [Running the Application](#running-the-application)
    - [Troubleshooting](#troubleshooting)
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
    - [Managing PIDs](#managing-pids)
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

In general, remember to always run `source prepare_cli.sh` (or `call prepare_cli.bat` on Windows) before using the CLI to ensure that the environment is set up correctly.
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
yprov documents permissions add <document_pid> --user-email <email> --permission-level <level>
yprov documents permissions list <document_pid>
yprov documents permissions delete <document_pid> --user-email <email>
yprov documents metadata get <document_pid>
yprov documents metadata update <document_pid> --key1 <key1> --key2 <value2>
yprov documents metadata schema
yprov pids list [--page <page_number>] [--page-size <page_size>]
yprov pids get <pid>
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
    > Or on Windows:
    > ```cmd
    > set YPROV_API_URL="http://your-api-server.com:8000"
    > ```

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

### Managing Document Permissions

You can grant or view permissions on documents. Internally, all permissions live on the *first version* of a document—adding or listing against any version will target that root document.

* **Add a permission**

  ```bash
  yprov documents permissions add <prefix/id> \
    --user-email user@example.com \
    --permission-level write
  ```

  Notes:

  * PID **must** be in `prefix/id` form.
  * Permissions are always stored on the first version; granting on v2 or v3 still writes to v1.
  * The first version document must already reside on this server instance.
  * Although `read` is supported by the service, setting `read` on already‑public docs may result in an error.

- **List permissions**

  ```bash
  yprov documents permissions list <pid>
  ```

  `<pid>` can be either `prefix/id` or just `id` (default prefix will be used). This shows every user and their permission level on that document’s first version.

- **Delete a permission**

  ```bash
  yprov documents permissions delete <prefix/id> --user-email user@example.com
  ```

  This command deletes the permission for the specified user on the document's first version. The `<prefix/id>` can be provided in the same way as in the list command.

  You must be the owner of the first version of the document to delete permissions. If you are not the owner, you will receive a `403 Forbidden` error.

-----

### Managing Document Metadata


You can manage metadata for documents, including retrieving and updating it.

- **Get metadata for a document**

  ```bash
  yprov documents metadata get <document_pid>
  ```

  This command retrieves the metadata associated with the specified document PID.

- **Update metadata for a document**

  ```bash
  yprov documents metadata update <document_pid> --key <value>
  ```

  This command updates the metadata for the specified document PID.
  You can specify multiple key-value pairs to update multiple metadata fields at once.
  To set a list field, use multiple invocations of the same option, or pass a list as a comma-separated string.
  For example:

  ```bash
  yprov documents metadata update <document_pid> --title "New Title" --keywords keyword1 --keywords keyword2
  # or
  yprov documents metadata update <document_pid> --title "New Title" --keywords "keyword1,keyword2"
  ```
  
  # This command will empty both title and keywords:
  yprov documents metadata update <document_pid> --title "" --keywords ""
  ```
  
  - The PID must be fully qualified (prefix/id).
  - Only passed fields will be updated; existing fields not specified will remain unchanged.
  - Before updating, the command will validate the provided fields against the metadata schema fetched from the server.
  - Fields not defined in the schema will be ignored.
  - To set an empty field, use an empty string
  - To set a list field, use multiple invocations of the same option.
  - To update a list field, you need to pass the entire list each time.
  - If no fields are provided, the command will exit with a warning.
  - To update metadata for a document, you must be the owner of the document or have write permissions on it.

- **Get metadata schema**

  You can retrieve the metadata schema, which defines the structure and fields of the metadata.

  ```bash
  yprov documents metadata schema
  ```

  The schema defines the structure and fields that can be used in document metadata.

  Example output:

  ```
  > yprov documents metadata schema
                              Document Metadata Schema
  ┌─────────────┬──────────────┬──────────┬────────────────────────────────────────┐
  │ Field       │ Type         │ Required │ Example                                │
  ├─────────────┼──────────────┼──────────┼────────────────────────────────────────┤
  │ title       │ string       │ No       │ Sample Document Title                  │
  │ description │ string       │ No       │ This is a sample document description. │
  │ keywords    │ list[string] │ No       │ ['keyword1', 'keyword2']               │
  └─────────────┴──────────────┴──────────┴────────────────────────────────────────┘
  ```

-----

### Graph Operations on Documents

You can explore and analyze the provenance graph structure of documents. Graph operations allow you to list and filter elements within a provenance document's graph representation.

* **List graph elements**

  ```bash
  yprov documents graph list <prefix/id> [OPTIONS]
  ```

  This command lists all elements in a provenance document's graph, including entities, agents, activities, and relationships.

  Options:

  * `--entity-types, -t`   Filter by entity types (can be used multiple times). Examples: `entity`, `agent`, `activity`, `wasDerivedFrom`, `wasGeneratedBy`
  * `--entity-ids, -e`     Filter by specific entity IDs (can be used multiple times)
  * `--is-element, -ie`    Filter by whether the entity is an element (boolean flag)
  * `--is-relation, -ir`   Filter by whether the entity is a relation (boolean flag)
  * `--in-json, -j`        Output results in JSON format with complete data
  * `--display-data, -d`   Include the data field in the console table output
  * `--output, -o`         Save results to a file path (writes complete JSON data)

  Examples:

  * List all graph elements for a document:

    ```bash
    yprov documents graph list myprefix/1234
    ```

  * Filter by specific entity types:

    ```bash
    yprov documents graph list myprefix/1234 --entity-types entity --entity-types agent
    # or, shorter:
    yprov documents graph list myprefix/1234 -t entity -t agent
    ```

  * Filter by entity which are elements:

    ```bash
    yprov documents graph list myprefix/1234 --is-element
    # or, shorter:
    yprov documents graph list myprefix/1234 -ie
    ```

  * Filter by entity which are relations:

    ```bash
    yprov documents graph list myprefix/1234 --is-relation
    # or, shorter:
    yprov documents graph list myprefix/1234 -ir
    ```

  * Filter by entity IDs and display data in the console:

    ```bash
    yprov documents graph list myprefix/1234 --entity-ids "my_entity_1" --display-data
    ```

  * Save results to a JSON file:

    ```bash
    yprov documents graph list myprefix/1234 --output /path/to/graph_elements.json
    ```

  * Get JSON output in the console:

    ```bash
    yprov documents graph list myprefix/1234 --in-json
    ```

  Notes:

  * The PID **must** be in `prefix/id` format.
  * The command displays a table with columns: ID, Type, Group, Is Element, Is Relation.
  * Use `--display-data` to see the actual data content of each element in the console.
  * Multiple filters can be combined (e.g., both entity types and entity IDs).
  * The output includes any warnings from the server and a total count of elements found.

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

