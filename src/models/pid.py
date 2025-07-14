from enum import Enum
from dataclasses import dataclass

from models import DocumentRecord


# TODO: manage tree pid

class PidType(Enum):
    """
    Enum-like class for PID types.
    """
    DOCUMENT = "document"
    ARTIFACT = "artifact"
    PID_TREE = "pid_tree"


@dataclass
class PidRecord:
    pid: str
    type: PidType

    # Attributes for document
    version: int | None = None
    location: str | None = None
    parent_doc_pid: str | None = None  # previous document pid in the tree
    tree_pid: str | None = None

    # Attributes for PID tree
    first_document_pid: str | None = None
    latest_document_pid: str | None = None
    latest_version: int | None = None

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = PidType(self.type)
        required_fields = {
            PidType.PID_TREE: ["first_document_pid", "latest_document_pid", "latest_version"],
            PidType.DOCUMENT: ["location", "version"],
            PidType.ARTIFACT: ["location"]
        }
        for field in required_fields[self.type]:
            if self.type == PidType.PID_TREE and not getattr(self, field):
                raise AttributeError(f"{field} must be set for {self.type} type.")

    @classmethod
    def from_document_record(cls, document_record: DocumentRecord, tree_pid: str | None = None) -> 'PidRecord':
        """
        Create a PidRecord from a DocumentRecord.
        """
        return cls(
            pid=document_record.pid,
            type=PidType.DOCUMENT,
            version=document_record.version,
            location=document_record.storage_url,
            parent_doc_pid=document_record.parent_doc_pid,
            tree_pid=tree_pid,
        )

    def to_dict(self) -> dict:
        """
        Convert the PidRecord instance to a dictionary for JSON serialization.
        """
        return {
            "pid": self.pid,
            "type": self.type.value,
            "version": self.version,
            "location": self.location,
            "parent_doc_pid": self.parent_doc_pid,
            "tree_pid": self.tree_pid,
            "first_document_pid": self.first_document_pid,
            "latest_document_pid": self.latest_document_pid,
            "latest_version": self.latest_version,
        }
