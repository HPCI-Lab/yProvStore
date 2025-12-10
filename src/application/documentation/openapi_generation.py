from fastapi.openapi.utils import get_openapi

from application.settings import APP_TITLE, APP_VERSION, APP_DESCRIPTION, APP_URL, PID_PREFIX


def custom_openapi(app) -> dict:
    """
    Custom OpenAPI schema generator for FastAPI application.
    This function modifies the OpenAPI schema to include a bearer token authentication scheme.
    If the schema is already generated, it returns the existing schema.

    :param app: FastAPI application instance
    :return: OpenAPI schema dictionary with bearer token authentication.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=APP_TITLE,
        version=APP_VERSION,
        description=APP_DESCRIPTION,
        routes=app.routes,
    )

    # === Update the OpenAPI schema below as needed === #

    return openapi_schema


EXAMPLE_UUID = f"{PID_PREFIX}/123e4567-e89b-12d3-a456-426614174000"
EXAMPLE_UUID_2 = f"{PID_PREFIX}/123e4567-e89b-12d3-a456-426614174001"
EXAMPLE_HASH = "3a7bd3e2360a3d4858f6f2d4b3b5c6e0f1a2b3c4d5e6f708192a3b4c5d6e7f80"
EXAMPLE_EMAIL = "user@example.com"
EXAMPLE_DOCUMENT_VERSION = 1
EXAMPLE_DOCUMENT_STORAGE = f"{APP_URL}/docs/{EXAMPLE_UUID}"
EXAMPLE_ARTIFACT_STORAGE = f"{APP_URL}/artifacts/{EXAMPLE_UUID}"
EXAMPLE_ARTIFACT_FILENAME = "example_artifact.txt"
# TODO: make this a valid PROV JSON graph
EXAMPLE_DOCUMENT_DATA = {
    "activity": {
        "activity1": {
            "prov:startedAtTime": "2023-10-01T12:00:00Z",
            "prov:endedAtTime": "2023-10-01T12:05:00Z",
        },
    },
    "entity": {
        "entity1": {
            "prov:location": "https://example.com/entity1",
            "yprov:pid": "entity1_pid",
        },
        "entity2": {
            "prov:location": "https://example.com/entity2",
            "yprov:pid": "entity2_pid",
        }
    },
    "experiment": {
        "title": "Sample Experiment",
        "description": "This is a sample experiment.",
    },
    "used": {
        "_:id1": {
            "prov:entity": "entity1",
            "prov:activity": "activity1",
        }
    },
    "wasGeneratedBy": {
        "_:id2": {
            "prov:entity": "entity2",
            "prov:activity": "activity1",
        }
    }
}
EXAMPLE_METADATA_TITLE = "Sample Document Title"
EXAMPLE_METADATA_DESCRIPTION = "This is a sample document description."
EXAMPLE_METADATA_KEYWORDS = ["keyword1", "keyword2"]
EXAMPLE_METADATA_AUTHOR = "Sample Author"
EXAMPLE_METADATA_EXTRA = {"custom_field": "custom_value"}
EXAMPLE_METADATA_SCHEMA = {
  "properties": {
    "title": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "example": "Sample Document Title"
    },
    "description": {
      "anyOf": [
        {
          "type": "string"
        },
        {
          "type": "null"
        }
      ],
      "example": "This is a sample document description."
    },
    "keywords": {
      "anyOf": [
        {
          "items": {
            "type": "string"
          },
          "type": "array"
        },
        {
          "type": "null"
        }
      ],
      "example": [
        "keyword1",
        "keyword2"
      ]
    }
  }
}
