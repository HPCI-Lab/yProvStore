# yProvStore

**yProv** is a provenance service aimed at addressing multi-level provenance as well as reproducibility challenges in climate analytics experiments. It allows scientists to manage provenance information compliant with the [W3C PROV standard](https://www.w3.org/TR/prov-overview/) in a more structured way and navigate and explore the provenance space across multiple dimensions, thus enabling the possibility to get coarse or fine-grained information according to the level of interest.

yProv is a joint project between [University of Trento](https://www.unitn.it) and [CMCC](https://www.cmcc.it).

**yProvStore** is the backend service of yProv, built with FastAPI and designed to handle the storage and retrieval of provenance data. It provides a RESTful API for interacting with provenance information, allowing users to create and read provenance records.

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