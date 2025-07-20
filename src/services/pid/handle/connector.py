import os
import json
import httpx
import base64
import asyncio
import logging

from Cryptodome.Signature import pkcs1_15
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import RSA

from application.settings import PID_SERVER_URL, PID_ADMIN_HANDLE, PID_PRIVATE_KEY_PATH, PID_ADMIN_HANDLE_INDEX
from application.exceptions.types import IntegrityException, ConflictException


logger = logging.getLogger(__name__)


# Disable UnsecureRequestWarning prints for self-signed https requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HandlePaths:
    SESSIONS = PID_SERVER_URL + "/api/sessions"
    SESSION_THIS = PID_SERVER_URL + "/api/sessions/this"
    HANDLES = PID_SERVER_URL + "/api/handles"
    HANDLE = PID_SERVER_URL + "/api/handles/{pid}"


class HandleConnector:

    def __init__(self):
        self.http_client = httpx.AsyncClient(verify=False) # `verify=False` to allow self-signed certs
        self.private_key = self._load_private_key_file(PID_PRIVATE_KEY_PATH)
        self.session_id = None
        self._auth_lock = asyncio.Lock() # Prevents race conditions during authentication

    def _load_private_key_file(self, path):
        with open(path, "r") as key_file:
            return RSA.import_key(key_file.read())

    async def send_http_request(self, method: str, url: str, data: dict | None = None, headers: dict | None = None, raise_not_found: bool = True) -> dict | None:
        if method not in ["GET", "POST", "PUT", "DELETE"]:
            raise Exception(f"Unsupported HTTP method: {method}")
        try:
            if headers is None:
                headers = self._get_session_auth_header()
            logger.debug(f"Sending {method} request to {url} with headers: {headers} and data: {data}")
            response = await self.http_client.request(method, url, json=data, headers=headers, timeout=10.0)
            # In case of error the response has the following properties:
            # - "responseCode": Handle protocol response code for the message. (handle coders are described in README.md inside this file folder)
            # - "message": For error responses, an error message.
            if response.status_code == 404 and not raise_not_found:
                return None
            response.raise_for_status() # Raise an exception for 4xx/5xx responses
            return response.json()
        except httpx.HTTPStatusError as e:
            # Re-raise with more context from the server's response if available
            error_details = e.response.json()
            logger.debug(f"Handle Server response details: {error_details}")
            response_code = error_details.get("responseCode", "Unknown")
            message = error_details.get("message", "No message provided")
            logger.error(f"Handle Server Error: {e.response.status_code} - {response_code}: {message}")
            if str(response_code) == "101":
                raise ConflictException("Handle already exists")
            raise IntegrityException("Failed to communicate with Handle Server")
        except httpx.RequestError as e:
            logger.error(f"HTTP Request Error: {e}")
            raise IntegrityException("Failed to communicate with Handle Server")
        except json.JSONDecodeError as e:
            logger.error(f"JSON Decode Error decoding handle server response: {e}")
            raise IntegrityException("Failed to decode response from Handle Server")
        except Exception as e:
            logger.error(f"Unexpected error during HTTP request to handle server: {e}")
            raise IntegrityException("Failed to communicate with Handle Server")

    async def _authenticate(self):
        # 1. Generate client nonce
        client_nonce_bytes = os.urandom(16)
        client_nonce_string = base64.b64encode(client_nonce_bytes).decode()

        # 2. Start session to get server nonce
        session_url = HandlePaths.SESSIONS
        init_response = await self.send_http_request("POST", session_url, headers={})
        server_nonce_string = init_response["nonce"]
        self.session_id = init_response["sessionId"]
        server_nonce_bytes = base64.b64decode(server_nonce_string)

        # 3. Sign the combined nonces
        combined_nonce_bytes = server_nonce_bytes + client_nonce_bytes
        digest = SHA256.new(combined_nonce_bytes)
        signer = pkcs1_15.new(self.private_key)
        signature_bytes = signer.sign(digest)
        signature_string = base64.b64encode(signature_bytes).decode()

        # 4. Complete authentication
        auth_url = HandlePaths.SESSION_THIS
        id_str = f'{PID_ADMIN_HANDLE_INDEX}:{PID_ADMIN_HANDLE}'
        auth_header_str = (
            f'Handle version="0", sessionId="{self.session_id}", cnonce="{client_nonce_string}", '
            f'id="{id_str}", type="HS_PUBKEY", alg="SHA256", signature="{signature_string}"'
        )
        auth_response = await self.send_http_request("POST", auth_url, headers={'Authorization': auth_header_str})

        if not auth_response.get("authenticated"):
            raise IntegrityException(f"Handle Server authentication failed: {auth_response}")

    async def ensure_authenticated(self):
        """A thread-safe method to ensure the service is authenticated before making a call."""
        if self.session_id:
            return
        async with self._auth_lock:
            # Check again after acquiring the lock in case another coroutine finished auth
            if self.session_id:
                return
            await self._authenticate()

    def _get_session_auth_header(self) -> dict:
        """Returns the authorization header for an existing authenticated session."""
        return {'Authorization': f'Handle version="0", sessionId="{self.session_id}"'}
