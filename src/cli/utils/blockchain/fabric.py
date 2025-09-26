import os
import json
import logging
import subprocess
from enum import Enum
from shutil import which
from datetime import datetime
from importlib import resources
from urllib.parse import urlparse
from dataclasses import dataclass, asdict

import dotenv

dotenv.load_dotenv(override=True)

logger = logging.getLogger(__name__)


@dataclass
class BlockchainDocument:
    """
    A class to represent a document stored on the blockchain.
    """
    pid: str
    url: str
    hash: str
    timestamp: str
    owners: list[str]

    def validate(self):
        if not isinstance(self.pid, str) or not self.pid.strip():
            raise ValueError("Document pid must be a non-empty string")

        if not isinstance(self.url, str) or not self.url.strip():
            raise ValueError("Document url must be a non-empty string")
        parsed_url = urlparse(self.url)
        if parsed_url.scheme.lower() not in ("http", "https") or not parsed_url.netloc:
            raise ValueError("Document url must be a valid http(s) URL")

        if not isinstance(self.hash, str) or not self.hash.strip():
            raise ValueError("Document hash must be a non-empty string")

        if not isinstance(self.timestamp, str) or not self.timestamp.strip():
            raise ValueError("Document timestamp must be a non-empty ISO-8601 string")
        try:
            datetime.fromisoformat(self.timestamp)
        except Exception:
            raise ValueError("Document timestamp must be a valid ISO-8601 datetime string")

        if not isinstance(self.owners, list) or not self.owners:
            raise ValueError("Document owners must be a non-empty list of owner identifiers")
        for owner in self.owners:
            if not isinstance(owner, str) or not owner.strip():
                raise ValueError("each owner in Document owners must be a non-empty string")

        # normalize owners (remove duplicates while preserving order)
        seen = set()
        normalized = []
        for owner in self.owners:
            if owner not in seen:
                seen.add(owner)
                normalized.append(owner)
        self.owners = normalized

class JSMethods(Enum):
    CREATE_DOCUMENT = "createResource"
    READ_DOCUMENT = "readResource"
    GET_DOCUMENTS_BY_INTERVAL = "getResourcesByInterval"


class FabricConnector:
    """
    A class to manage connections to a Fabric network.
    It proxies calls to a Javascript implementation, due to the lack of a Python SDK.

    Assumes a wrapper.js file exists that can handle the methods defined in JSMethods.
    """

    PACKAGE_NAME = "yprov-cli"
    WRAPPER_PATH = "lib/dist/wrapper.js"

    def create_document(self, document: BlockchainDocument) -> str:
        """
        Create a new document on the blockchain.

        Args:
            document (BlockchainDocument): The document to create.

        Returns:
            str: The result of the creation operation.
        """
        # basic validation of document fields before sending to JS

        if not isinstance(document, BlockchainDocument):
            raise TypeError("document must be a BlockchainDocument instance")

        document.validate()

        return self._call_js(JSMethods.CREATE_DOCUMENT, asdict(document))
    
    def read_document(self, pid: str) -> str:
        """
        Read a document from the blockchain by its PID.

        Args:
            pid (str): The PID of the document to read.

        Returns:
            str: The result of the read operation.
        """
        return self._call_js(JSMethods.READ_DOCUMENT, {"pid": pid})
    
    def get_documents_by_interval(self, start_time: str, end_time: str) -> str:
        """
        Get documents created within a specific time interval.

        Args:
            start_time (str): The start of the time interval.
            end_time (str): The end of the time interval.

        Returns:
            str: The result of the query operation.
        """
        return self._call_js(JSMethods.GET_DOCUMENTS_BY_INTERVAL, {"startTime": start_time, "endTime": end_time})

    def _call_js(self, method: JSMethods, params: dict | None = None, extra_env: dict | None = None, timeout: int = 30) -> str:
        """
        Call the Node.js wrapper script with the specified method and parameters.

        Args:
            method (JSMethods): The method to call.
            params (dict | None): The parameters for the method.
            extra_env (dict | None): Additional environment variables to set.
            timeout (int): Timeout for the subprocess call in seconds.
        Returns:
            dict: The result from the Node.js script.
        """
        env_vars = {
            "CONNECTOR_PEER_TLSCERT_PATH": os.getenv("CONNECTOR_PEER_TLSCERT_PATH"),
            "CONNECTOR_USR_PKEY_PATH": os.getenv("CONNECTOR_USR_PKEY_PATH"),
            "CONNECTOR_PEER_ENDPOINT": os.getenv("CONNECTOR_PEER_ENDPOINT"),
            "CONNECTOR_PEER_HOSTNAME": os.getenv("CONNECTOR_PEER_HOSTNAME") or os.getenv("CONNECTOR_PEER_ENDPOINT"),
            "CONNECTOR_USR_CERT_PATH": os.getenv("CONNECTOR_USR_CERT_PATH"),
            "CONNECTOR_PEER_MSP_ID": os.getenv("CONNECTOR_PEER_MSP_ID"),
        }
        missing = [k for k, v in env_vars.items() if not v]
        if missing:
            raise RuntimeError(f"Missing required env vars for Fabric connection: {', '.join(missing)}")
        if extra_env:
            env_vars.update(extra_env)

        payload = json.dumps({"method": method.value, "params": params or {}}).encode()

        node = self._find_node_executable()
        wrapper = self._get_bundled_wrapper_path()
        proc = subprocess.run(
            [node, wrapper],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env_vars,
            timeout=timeout,
        )

        out = proc.stdout.decode().strip()
        if not out:
            raise RuntimeError("No output from node wrapper. stderr:\n\n" + proc.stderr.decode())

        if proc.stderr:
            # don't treat stderr as fatal, but useful for debugging
            logger.error("node stderr:\n\n" + proc.stderr.decode())

        data = json.loads(out)
        if not data.get("ok"):
            err = data.get("error", {})
            raise RuntimeError(f"JS error: {err.get('message')}")
        return data["result"]

    def _find_node_executable(self):
        # prefer 'node' on PATH
        node = which("node") or which("node.exe")
        if not node:
            raise RuntimeError("Node.js is required but not found on PATH. Please install Node >= 14.")
        return node

    def _get_bundled_wrapper_path(self):
        # returns a pathlib.Path or a file-like object — make sure we have a real FS path
        try:
            with resources.path(self.PACKAGE_NAME, self.WRAPPER_PATH) as p:
                return str(p)
        except Exception:
            # fallback: assume we're running from source checkout
            return os.path.join(os.path.dirname(__file__), self.WRAPPER_PATH)
