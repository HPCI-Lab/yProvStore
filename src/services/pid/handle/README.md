# Handle System REST API Documentation

This document provides some basic information about the Handle System REST API, which is used for managing handles and their associated values. The API allows for creating, retrieving, updating, and deleting handles, as well as managing sessions for authentication.

## API Response Codes

The Handle System REST API uses specific response codes in the JSON body of its replies, which correspond to standard HTTP status codes.

| Handle Code | HTTP Status | Meaning |
| :--- | :--- | :--- |
| **1** | `200 OK` or `201 Created` | Success |
| **2** | `500 Internal Server Error` | An unexpected error on the server |
| **100** | `404 Not Found` | Handle not found |
| **101** | `409 Conflict` | Handle already exists |
| **102** | `400 Bad Request` | Invalid handle |
| **200** | `200 OK` or `400 Bad Request`| Values not found |
| **201** | `409 Conflict` | Value already exists |
| **202** | `400 Bad Request` | Invalid value |
| **301** | `400 Bad Request` | Server not responsible for handle |
| **402** | `401 Unauthorized` | Authentication needed |
| **40x** | `403 Forbidden` | Other authentication errors |



## Handle API Endpoints

### `GET /api/handles/{handle}`

Resolves the handle record for a given `{handle}`.

* **URI Query Parameters:**
    * `index={index}`: (Repeatable) Resolve only the handle value(s) with the specified index.
    * `type={type}`: (Repeatable) Resolve only handle values with the specified type.
    * `auth=[true|false]`: If `true`, performs an authoritative resolution, bypassing any cache. Default is `false`.
    * `publicOnly=[true|false]`: If `true`, only resolves publicly readable values. Default is `true` for unauthenticated requests and `false` for authenticated ones.

* **Response Entity:** A JSON object containing `responseCode`, `handle`, and an array of `values`.

### `PUT /api/handles/{handle}`

Creates a new handle or completely replaces its record. You can also add or replace specific values by specifying their index in the URL.

* **Request Entity:** An array of handle values, or a single handle value object.

* **URI Query Parameters:**
    * `index={index}`: (Repeatable) Add or replace only the handle value(s) with the specified index.
    * `overwrite=[true|false]`: If `false`, returns a `409 Conflict` if the handle or value already exists. Default is `true`.
    * `mintNewSuffix=[true|false]`: If `true`, a random suffix is generated and appended to the `{handle}` parameter provided. Default is `false`.

* **Response Entity:** A JSON object containing `responseCode` and `handle`.

### `DELETE /api/handles/{handle}`

Deletes an entire handle or specific values within it.

* **URI Query Parameters:**
    * `index={index}`: (Repeatable) Deletes only the handle value(s) with the specified index.

* **Response Entity:** A JSON object containing `responseCode` and `handle`.

### `GET /api/handles?prefix={prefix}`

Lists all handles under a given `{prefix}`.

* **URI Query Parameters:**
    * `prefix={prefix}`: (Required) Specifies the prefix of the handles to list.
    * `page={page}` & `pageSize={pageSize}`: Used for paginated listing.

* **Response Entity:** A JSON object containing `responseCode`, `prefix`, `totalCount`, and an array of `handles`.



## JSON Data Formats

### Handle Value Object

Each handle value is a JSON object with the following attributes:

* `"index"`: (integer) The unique index of the value within the record.
* `"type"`: (string) The type of the data (e.g., `URL`, `HS_ADMIN`).
* `"data"`: (object) The data payload, structured according to its format (see below).
* `"ttl"`: (integer) The time-to-live in seconds.
* `"timestamp"`: (string) An ISO 8601 formatted timestamp of the last modification.
* `"permissions"`: (string, optional) A bitmask string for permissions. Omitted if a common default is used.
* `"references"`: (array, optional) An array of handle references. Omitted if empty.

### Data Field Formats

The `"data"` field within a handle value is an object with `format` and `value` properties.

* If `"format": "string"`, `"value"` is a UTF-8 string.
* If `"format": "base64"`, `"value"` is a Base64 encoded string.
* If `"format": "hex"`, `"value"` is a hex-encoded string.
* If `"format": "admin"`, `"value"` is an object representing an `HS_ADMIN` value with properties:
    * `"handle"` (string)
    * `"index"` (integer)
    * `"permissions"` (string)
* If `"format": "key"`, `"value"` is an object in JSON Web Key (JWK) format.
* If `"format": "vlist"`, `"value"` is a list of objects representing an `HS_VLIST`.
* If `"format": "site"`, `"value"` is a complex object representing an `HS_SITE`.



## Sessions API

The Sessions API allows for proactive session initiation and authentication.

### `POST /api/sessions`

Initiates a new session.

* **Request:** A client can optionally send a `cnonce` (client nonce) in a JSON object to request a server signature.
* **Response:** A JSON object with `sessionId` and `nonce`.

### `GET /api/sessions/this`

Verifies the status of the current session.

* **Request:** The session is identified via the `Authorization: Handle sessionId="..."` header.
* **Response:** A JSON object showing `sessionId`, `nonce`, and if authenticated, `authenticated: true` along with the authenticated `id`.

### `PUT /api/sessions/this`

Authenticates within an existing session.

* **Request:** The client must send a JSON object containing `sessionId`, `id`, `type`, `cnonce`, `alg`, and `signature`.
* **Response:** A JSON object indicating `authenticated: true` if successful.

### `DELETE /api/sessions/this`

Deletes (logs out of) a session.

* **Request:** The session is identified via the `Authorization: Handle sessionId="..."` header.
* **Response:** An empty response with HTTP status `204 No Content`.