import uuid
import json
import logging

from dishka import Provider, provide, Scope

from application.settings import PID_PREFIX, TMP_PATH
from application.exceptions.types import ConflictException, NotFoundException, IntegrityException
from models import PidRecord, PidType
from services.pid.handle.connector import HandleConnector, HandlePaths
from services.pid.handle.record import HandleRecord


logger = logging.getLogger(__name__)


class PidService:

    prefix = PID_PREFIX

    async def new_pid(self, prefix: str = None) -> str:
        """
        Generate a new unique PID (Persistent Identifier).
        """
        raise NotImplementedError

    async def save_pid_record(self, pid_record: PidRecord) -> PidRecord:
        """
        Save a PID record to the storage.
        """
        raise NotImplementedError

    async def get_pid_record(self, pid: str, raise_not_found: bool = True) -> PidRecord:
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

    async def new_pid_record_from_document(
        self, pid: str, location: str, parent_doc_pid: str | None = None, allow_tree_branching: bool = False,
    ) -> PidRecord:
        """
        Create a new PID record from a document.
        This method manages the creation of a PID tree if the parent document PID is provided.

        :param pid: The PID to use for the new document. If None, a new PID will be generated.
        :param location: The storage location of the document.
        :param parent_doc_pid: The PID of the parent document, if any.
        :param allow_tree_branching: If True, allows creating a new subtree even if the latest version of the parent document is higher than the current document version.
        :return: A PidRecord object of the new created document.
        """
        parent_doc_record = None
        pid_tree_record = None
        new_version = 1
        if parent_doc_pid:
            parent_doc_record = await self.get_pid_record(parent_doc_pid, raise_not_found=False)
            if not parent_doc_record:
                raise NotFoundException(f"Parent document PID {parent_doc_pid} not found in handle server.")
            pid_tree_record = await self.get_pid_record(parent_doc_record.tree_pid, raise_not_found=False)
            logger.info(f"Parent document record: {parent_doc_record}")

            if not pid_tree_record:
                # Valid if parent_doc version is 1
                if parent_doc_record.version != 1:
                    raise IntegrityException(f"PID tree record for parent document PID {parent_doc_pid} not found.")
                else:
                    # If parent version is 1 then this is the first document update -> create a new tree PID
                    tree_pid = await self.new_pid()
                    pid_tree_record = PidRecord(pid=tree_pid, type=PidType.PID_TREE, first_document_pid=pid, latest_document_pid=pid, latest_version=new_version)
                    pid_tree_record = await self.save_pid_record(pid_tree_record)

                    # Update the parent document record with the new tree PID
                    parent_doc_record.tree_pid = pid_tree_record.pid
                    await self.update_pid_record(parent_doc_record)

            if pid_tree_record.type != PidType.PID_TREE:
                raise IntegrityException(f"Document with PID {parent_doc_pid} is not a tree record.")

            # It is allowed to create a new document only with version=latest_version + 1 (except with allow_tree_branching=True)
            if pid_tree_record.latest_version > parent_doc_record.version:
                if not allow_tree_branching:
                    raise ValueError(f"Cannot create a new document in the tree {pid_tree_record.pid} because the latest version is higher than the parent document version.")
                # Create a new subtree starting in the middle of the document pid tree
                new_version = parent_doc_record.version + 1  # TODO: check version of subtree
                pid_tree_record = PidRecord(
                    pid=await self.new_pid(), type=PidType.PID_TREE, first_document_pid=parent_doc_pid,
                    latest_document_pid=pid, latest_version=new_version
                )
            else:
                # Increment the version of the existing tree record
                new_version = pid_tree_record.latest_version + 1
                pid_tree_record.latest_document_pid = pid
                pid_tree_record.latest_version = new_version
                await self.update_pid_record(pid_tree_record)

        new_pid_record = PidRecord(
            pid=pid,
            type=PidType.DOCUMENT,
            version=new_version,
            location=location,
            parent_doc_pid=parent_doc_pid,
            tree_pid=pid_tree_record.pid if pid_tree_record else None,
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

    async def new_pid(self, prefix: str = None) -> str:
        """
        Generate a new unique PID (Persistent Identifier).
        This implementation uses UUID v4 generation.
        """
        if prefix is None:
            prefix = self.prefix
        return prefix + str(uuid.uuid4())

    async def save_pid_record(self, pid_record: PidRecord) -> PidRecord:
        if pid_record.pid in self.pids:
            raise ConflictException(f"PID record with ID '{pid_record.pid}' already exists")
        self.pids[pid_record.pid] = pid_record
        self._save_pids_to_file()
        return pid_record

    async def get_pid_record(self, pid: str, raise_not_found: bool = True) -> PidRecord:
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

    async def new_pid(self, prefix: str = None) -> str:
        if prefix is None:
            prefix = self.prefix
        new_uuid = str(uuid.uuid4())
        return f"{prefix}/{new_uuid}" if prefix else new_uuid

    async def save_pid_record(self, pid_record: PidRecord) -> PidRecord:
        await self.ensure_authenticated()
        url = HandlePaths.HANDLE.format(pid=pid_record.pid) + "?overwrite=false"
        handle_record_body = HandleRecord.from_pid_record(pid_record).record_values
        try:
            await self.send_http_request("PUT", url, data=handle_record_body)
            return pid_record
        except IntegrityException as e:
            if "handle already exists" in str(e).lower():
                raise ConflictException(f"PID record with ID '{pid_record.pid}' already exists.")
            raise

    async def get_pid_record(self, pid: str, raise_not_found: bool = True) -> PidRecord:
        await self.ensure_authenticated()
        url = HandlePaths.HANDLE.format(pid=pid)
        response = await self.send_http_request("GET", url, raise_not_found=raise_not_found)
        logger.info(f"Retrieved handle record for PID: {pid}")
        handle_record = HandleRecord.from_record_values(pid, response["values"]) if response else None
        return handle_record.to_pid_record() if handle_record else None

    async def update_pid_record(self, pid_record: PidRecord) -> PidRecord:
        await self.ensure_authenticated()
        url = HandlePaths.HANDLE.format(pid=pid_record.pid)
        handle_record_body = HandleRecord.from_pid_record(pid_record).record_values
        
        # We don't check for existence first to make the update atomic (let the server handle it)
        await self.send_http_request("PUT", url, data=handle_record_body)
        return pid_record


class PidServiceProvider(Provider):

    pid_service = provide(source=PidServiceImpl, scope=Scope.APP, provides=PidService)
