# yProvStore

## Version <next>

* Improved pid parameter management in query paths, supporting PID subdomains.
* Added storage of history of metadata changes for provenance documents.
* Added `extra` metadata field to provenance documents for storing additional user-defined information.
* Added storage of artifacts through MinIO presigned URLs.
* Implemented proxying of artifacts downloads/uploads through the API using presigned URLs.
* Moved CLI to a dedicated repository: [yProvStore-cli](https://github.com/HPCI-Lab/yProvStore-cli).
* Added `pgbouncer` service in Docker deployment for efficient database connection pooling.

## Version 1.0.0

* Added MinIO support for file storage, replacing local file system storage.
* Integrated `PostgreSQL` as the primary database for user and provenance document metadata storage.
* Added compression support for provenance documents using `zstd` before storage.
* Added `stream` parameter to the document download endpoint to support streaming large files.

## Version 0.1.0

* Initial release of yProvStore, the backend service for storing and retrieving provenance documents.
* Implemented basic RESTful API endpoints for creating and reading provenance records.
* Implemented basic authentication and authorization using API keys.
* Added temporary storage of documents in local file system.
* Implemented `SQL` storage for users and provenance document records using `SQLite`.
* Added basic error handling and logging.
* Set up `Alembic` for database migrations.
* Added basic CLI for interacting with the API.
