import os
import uuid
import json
import logging
from datetime import datetime
from urllib.parse import urlencode

from dishka import Provider, provide, Scope

from application.settings import PID_PREFIX, TMP_PATH, PID_PRIVATE_KEY_PATH, USE_LOCAL_PID_SERVICE
from application.exceptions.types import ConflictException, NotFoundException, IntegrityException
from models import PidRecord, PidType, PID_DATE_FORMAT, PID_TIMEZONE
from services.pid.handle.connector import HandleConnector, HandlePaths
from services.pid.handle.record import HandleRecord


logger = logging.getLogger(__name__)


class PidService:

    prefix = PID_PREFIX

    async def new_pid(self, prefix: str | None = None) -> str:
        """
        Generate a new unique PID (Persistent Identifier).
        """
        raise NotImplementedError

    async def save_pid_record(self, pid_record: PidRecord) -> PidRecord:
        """
        Save a PID record to the storage.
        """
        raise NotImplementedError

    async def get_pid_record(self, pid: str, raise_not_found: bool = True) -> PidRecord | None:
        """
        Retrieve a PID record by its unique identifier.
        """
        raise NotImplementedError

    async def update_pid_record(self, pid_record: PidRecord) -> PidRecord:
        """
        Update an existing PID record.
        This method should be used to update the attributes of an existing PID record.

        :param pid_record: The PID record to update.
        """
        raise NotImplementedError

    async def list_document_pids(self, page: int = 0, page_size: int = 10) -> list[str]:
        """
        List all document PIDs stored in the PID service.
        This method returns a list of all PIDs that represent documents.
        
        :param page: The page number for pagination (default is 0).
        :param page_size: The number of items per page (default is 10).
        :return: A list of document PIDs.
        """
        raise NotImplementedError
    
    async def get_document_pid(self, pid: str) -> dict:
        """
        Retrieve a document PID record by its unique identifier.
        This method returns the PID record as a dictionary.
        No conversion to PidRecord is done here, so that even older records can be retrieved.

        :param pid: The PID of the document to retrieve.
        :return: A dictionary representation of the PID record.
        """
        raise NotImplementedError

    async def new_pid_record_from_document(
        self, pid: str, url: str, parent_doc_pid: str | None = None, allow_lineage_branching: bool = False,
    ) -> PidRecord:
        """
        Create a new PID record from a document.
        This method manages the creation of a PID lineage if the parent document PID is provided.

        :param pid: The PID to use for the new document. If None, a new PID will be generated.
        :param url: The storage url of the document.
        :param parent_doc_pid: The PID of the parent document, if any.
        :param allow_lineage_branching: If True, allows creating a new lineage even if the latest version of the parent document is higher than the current document version.
        :return: A PidRecord object of the new created document.
        """
        parent_doc_record = None
        lineage_record = None
        new_version = 1
        if parent_doc_pid:
            parent_doc_record = await self.get_pid_record(parent_doc_pid, raise_not_found=False)
            if not parent_doc_record:
                raise NotFoundException(f"Parent document PID {parent_doc_pid} not found in handle server.")
            if parent_doc_record.lineage_id:
                lineage_record = await self.get_pid_record(parent_doc_record.lineage_id, raise_not_found=False)
                logger.debug(f"Parent document record: {parent_doc_record}")

            if not lineage_record:
                # Valid if parent_doc version is 1
                if str(parent_doc_record.version) != "1":
                    raise IntegrityException(f"PID lineage record for parent document PID {parent_doc_pid} not found.")
                else:
                    # If parent version is 1 then this is the first document update -> create a new lineage PID
                    lineage_id = await self.new_pid()
                    lineage_record = PidRecord(pid=lineage_id, type=PidType.LINEAGE, first_document_pid=parent_doc_pid, latest_document_pid=pid, latest_version=new_version)
                    lineage_record = await self.save_pid_record(lineage_record)

                    # Update the parent document record with the new lineage PID
                    parent_doc_record.lineage_id = lineage_record.pid

            if lineage_record.type != PidType.LINEAGE:
                raise IntegrityException(f"Document with PID {parent_doc_pid} is not a lineage record.")
            
            # It is allowed to create a new document only with version=latest_version + 1 (except with allow_lineage_branching=True)
            if not lineage_record.latest_version or not parent_doc_record.version:
                raise IntegrityException(f"PID lineage record with PID {lineage_record.pid} has no latest version or parent document version.")
            if int(lineage_record.latest_version) > int(parent_doc_record.version) and not allow_lineage_branching:
                raise ValueError(f"Cannot create a new document in the lineage {lineage_record.pid} because the latest version is higher than the parent document version.")

            parent_doc_record.successive_doc_pid = pid
            await self.update_pid_record(parent_doc_record)

            if int(lineage_record.latest_version) > int(parent_doc_record.version):
                # Create a new lineage starting in the middle of the document pid lineage
                new_version = int(parent_doc_record.version) + 1  # TODO: check version of subtree
                lineage_record = PidRecord(
                    pid=await self.new_pid(), type=PidType.LINEAGE, first_document_pid=parent_doc_pid,
                    latest_document_pid=pid, latest_version=new_version
                )
            else:
                # Increment the version of the existing lineage record
                new_version = int(lineage_record.latest_version) + 1
                lineage_record.latest_document_pid = pid
                lineage_record.latest_version = new_version
                await self.update_pid_record(lineage_record)

        new_pid_record = PidRecord(
            pid=pid,
            type=PidType.DOCUMENT,
            version=new_version,
            url=url,
            parent_doc_pid=parent_doc_pid,
            lineage_id=lineage_record.pid if lineage_record else None,
            created_at=datetime.now(PID_TIMEZONE).strftime(PID_DATE_FORMAT)
        )
        return await self.save_pid_record(new_pid_record)


class LocalPidServiceImpl(PidService):
    """
    In-memory implementation of PidService for testing purposes.
    """

    def __init__(self):
        self.documents_path = TMP_PATH / "pid"
        if not self.documents_path.exists():
            self.documents_path.mkdir(parents=True, exist_ok=True)
        self.pids_path = self.documents_path / "pids.json"
        if not self.pids_path.exists():
            with open(self.pids_path, 'w') as f:
                f.write("{}")
            self.pids = {}
        else:
            with open(self.pids_path, 'r') as f:
                self.pids = json.load(f)
                self.pids = {pid: PidRecord(**data) for pid, data in self.pids.items()}

    async def new_pid(self, prefix: str | None = None) -> str:
        """
        Generate a new unique PID (Persistent Identifier).
        This implementation uses UUID v4 generation.
        """
        if prefix is None:
            prefix = self.prefix
        return f"{prefix}/{uuid.uuid4()}"

    async def save_pid_record(self, pid_record: PidRecord) -> PidRecord:
        if pid_record.pid in self.pids:
            raise ConflictException(f"PID record with ID '{pid_record.pid}' already exists")
        self.pids[pid_record.pid] = pid_record
        self._save_pids_to_file()
        return pid_record

    async def get_pid_record(self, pid: str, raise_not_found: bool = True) -> PidRecord | None:
        if pid not in self.pids:
            if raise_not_found:
                raise NotFoundException(f"PID record with ID '{pid}' not found")
            return None
        return self.pids[pid]

    async def update_pid_record(self, pid_record: PidRecord) -> PidRecord:
        if pid_record.pid not in self.pids:
            raise NotFoundException(f"PID record with ID '{pid_record.pid}' not found")
        self.pids[pid_record.pid] = pid_record
        self._save_pids_to_file()
        return pid_record

    async def list_document_pids(self, page: int = 0, page_size: int = 10) -> list[str]:
        document_pids = [pid for pid, record in self.pids.items() if record.type == PidType.DOCUMENT]
        return document_pids[page * page_size:(page + 1) * page_size]
    
    async def get_document_pid(self, pid: str) -> dict:
        pid_record = await self.get_pid_record(pid, raise_not_found=False)
        if not pid_record:
            raise NotFoundException(f"Document PID with ID '{pid}' not found")
        return pid_record.to_dict()

    def _save_pids_to_file(self):
        """
        Save the current state of PIDs to the JSON file.
        This method is called automatically after any modification to the PIDs.
        """
        with open(self.pids_path, 'w') as f:
            json.dump({p.pid: p.to_dict() for p in self.pids.values()}, f, indent=4)


class PidServiceImpl(PidService, HandleConnector):
    """
    Implementation of the PidService that interacts with a real Handle System server.
    This class contains all the logic for HTTP communication and authentication.
    """

    def __init__(self):
        if not os.path.exists(PID_PRIVATE_KEY_PATH):
            raise FileNotFoundError(f"PID private key file not found: {PID_PRIVATE_KEY_PATH}")
        super().__init__()

    async def new_pid(self, prefix: str | None = None) -> str:
        if prefix is None:
            prefix = self.prefix
        new_uuid = str(uuid.uuid4())
        return f"{prefix}/{new_uuid}" if prefix else new_uuid

    async def save_pid_record(self, pid_record: PidRecord) -> PidRecord:
        await self.ensure_authenticated()
        url = HandlePaths.HANDLE.format(pid=pid_record.pid) + "?overwrite=false"
        handle_record_body = HandleRecord.from_pid_record(pid_record).record_values
        await self.send_http_request("PUT", url, data=handle_record_body)
        return pid_record

    async def get_pid_record(self, pid: str, raise_not_found: bool = True) -> PidRecord | None:
        await self.ensure_authenticated()
        url = HandlePaths.HANDLE.format(pid=pid)
        response = await self.send_http_request("GET", url, raise_not_found=raise_not_found)
        logger.debug(f"Retrieved handle record for PID: {pid}: {response}")
        handle_record = HandleRecord.from_record_values(pid, response["values"]) if response else None
        return handle_record.to_pid_record() if handle_record else None

    async def update_pid_record(self, pid_record: PidRecord) -> PidRecord:
        await self.ensure_authenticated()
        url = HandlePaths.HANDLE.format(pid=pid_record.pid)
        handle_record_body = HandleRecord.from_pid_record(pid_record).record_values
        await self.send_http_request("PUT", url, data=handle_record_body)
        return pid_record

    async def list_document_pids(self, page: int = 0, page_size: int = 10) -> list[str]:
        await self.ensure_authenticated()
        query_params = {
            "prefix": PID_PREFIX,
            "page": page,
            "pageSize": page_size
        }
        url = f"{HandlePaths.HANDLES}?{urlencode(query_params)}"
        response = await self.send_http_request("GET", url)
        return response['handles']

    async def get_document_pid(self, pid: str) -> dict:
        await self.ensure_authenticated()
        url = HandlePaths.HANDLE.format(pid=pid)
        response = await self.send_http_request("GET", url, raise_not_found=True)
        logger.debug(f"Retrieved handle record for PID: {pid}: {response}")
        return response


class PidServiceProvider(Provider):

    def __init__(self, *args, **kwargs):
        super().__init__(scope=Scope.APP, *args, **kwargs)
        if not USE_LOCAL_PID_SERVICE:
            if not os.path.exists(PID_PRIVATE_KEY_PATH):
                raise FileNotFoundError(f"PID private key file not found: {PID_PRIVATE_KEY_PATH}. Please provide it or "
                                        f"set USE_LOCAL_PID_SERVICE to True if you only need to test locally.")
        else:
            logger.warning("Using local PID service")

    @provide
    def provide_pid_service(self) -> PidService:
        """
        Provides an instance of the PidService.
        This method is used to inject the PidService into other components.
        """
        return PidServiceImpl() if not USE_LOCAL_PID_SERVICE else LocalPidServiceImpl()
