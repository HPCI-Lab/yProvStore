from enum import Enum
from dataclasses import dataclass
from typing import Any

from models import DocumentRecord
from datetime import timezone


PID_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
PID_TIMEZONE = timezone.utc


class PidType(Enum):
    """
    Enum-like class for PID types.
    """
    DOCUMENT = "document"
    ARTIFACT = "artifact"
    LINEAGE = "lineage"

    def __str__(self):
        return self.value


@dataclass
class PidRecord:
    # !! NOTE: when adding new attributes, update `to_dict` method and `HandleValueType` in `services/pid/handle/base.py`
    pid: str
    type: PidType

    # Attributes for document
    version: int | None = None
    url: str | None = None
    created_at: str | None = None
    parent_doc_pid: str | None = None  # previous document pid in the lineage
    successive_doc_pid: str | None = None  # next document pid in the lineage
    lineage_id: str | None = None
    hash: str | None = None
    hash_algorithm: str | None = None

    # Attributes for PID lineage
    first_document_pid: str | None = None
    latest_document_pid: str | None = None
    latest_version: int | None = None

    __other: dict[str, Any] | None = None
    
    def __init__(self, pid: str, type: PidType | str, **kwargs):
        self.pid = pid
        if not isinstance(type, PidType):
            type = PidType(type)
        self.type = type
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                if self.__other is None:
                    self.__other = {}
                self.__other[key] = value

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = PidType(self.type)
        if isinstance(self.version, str):
            self.version = int(self.version)
        if isinstance(self.latest_version, str):
            self.latest_version = int(self.latest_version)
        required_fields = {
            PidType.LINEAGE: ["first_document_pid", "latest_document_pid", "latest_version"],
            PidType.DOCUMENT: ["url", "version"],
            PidType.ARTIFACT: ["url"]
        }
        for field in required_fields[self.type]:
            if not getattr(self, field):
                raise AttributeError(f"{field} must be set for {self.type} type.")

    @property
    def other(self) -> dict[str, Any] | None:
        """
        Returns other attributes not defined in the class.
        """
        return self.__other
    
    @other.setter
    def other(self, value: dict[str, Any]):
        """
        Sets other attributes not defined in the class.
        """
        self.__other = value

    @classmethod
    def from_document_record(cls, document_record: DocumentRecord, lineage_id: str | None = None) -> 'PidRecord':
        """
        Create a PidRecord from a DocumentRecord.
        """
        return cls(
            pid=document_record.pid,
            type=PidType.DOCUMENT,
            version=document_record.version,
            url=document_record.storage_url,
            parent_doc_pid=document_record.parent_doc_pid,
            lineage_id=lineage_id,
            created_at=document_record.created_at,
        )

    def to_dict(self) -> dict:
        """
        Convert the PidRecord instance to a dictionary for JSON serialization.
        """
        return {
            "pid": self.pid,
            "type": self.type.value,
            "version": self.version,
            "url": self.url,
            "hash": self.hash,
            "hash_algorithm": self.hash_algorithm,
            "created_at": self.created_at,
            "parent_doc_pid": self.parent_doc_pid,
            "successive_doc_pid": self.successive_doc_pid,
            "lineage_id": self.lineage_id,
            "first_document_pid": self.first_document_pid,
            "latest_document_pid": self.latest_document_pid,
            "latest_version": self.latest_version,
            **(({k: v for k, v in self.other.items() if v} or {}) if self.other else {}),
        }
