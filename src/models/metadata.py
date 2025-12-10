import json
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import GenericAlias
from typing import get_origin, get_args
from types import UnionType


logger = logging.getLogger(__name__)


@dataclass
class DocumentMetadata:
    """
    Represents metadata for a document.
    NOTE: only str, list, and dict types are allowed for the attributes.
    """
    title: str | None = None
    description: str | None = None
    keywords: list[str] | None = None  # later converted to strings separated by pipe `|` character
    author: str | None = None
    extra: dict | None = None

    # When adding new fields, update also:
    # - services/pid/handle/base.py
    # - DocumentMetadataGet in routers/metadata/_get.py
    # - routers/documents/_create.py (when copying metadata from parent)

    def __post_init__(self):
        self._init_dataclass_fields()
    
    @classmethod
    def from_dict(cls, data: dict | None) -> 'DocumentMetadata':
        """
        Create a DocumentMetadata instance from a dictionary.
        
        :param data: Dictionary containing metadata fields.
        :return: DocumentMetadata instance.
        """
        if not data:
            return cls()
        if "extra" in data and isinstance(data["extra"], str):
            # Convert string to dict if it is a string
            if data["extra"] == "":
                data["extra"] = None
            else:
                try:
                    data["extra"] = json.loads(data["extra"])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode 'extra' field from string to dict. Setting it to None. Value: {data['extra']}")
        return cls(**data)
    
    def to_dict(self) -> dict:
        """
        Convert the DocumentMetadata instance to a dictionary for JSON serialization.
        
        :return: Dictionary representation of the metadata.
        """
        dict_values = {}
        for field in self.__dataclass_fields__:
            value = getattr(self, field)
            field_type = self.get_attribute_type(field)
            if field_type is list:
                if isinstance(value, list):
                    value = "|".join(value) if value else None
                dict_values[field] = str(value) if value is not None else None
            elif field_type is dict:
                # Keep dict as-is (will be JSON serialized)
                dict_values[field] = value if value else None
            else:
                dict_values[field] = str(value) if value is not None else None
        return dict_values
    
    @classmethod
    def get_attribute_type(cls, attribute_name: str) -> type:
        """
        Get the type of a specific attribute in the DocumentMetadata class.
        
        :param attribute_name: Name of the attribute to check.
        :return: Type of the attribute.
        """

        if attribute_name not in cls.__annotations__:
            raise Exception(f"Attribute '{attribute_name}' does not exist in DocumentMetadata.")
        attribute = DocumentMetadata.__annotations__[attribute_name]
        attribute_type = get_origin(attribute)
        if attribute_type == UnionType:
            types_tuple = tuple(t for t in get_args(attribute) if t is not type(None))
            if len(types_tuple) > 1:
                logger.warning(f"Multiple types found for metadata attribute '{attribute_name}': {types_tuple}. Using the first type: {types_tuple[0]}")
            attribute_type = types_tuple[0]
            
        if type(attribute_type) is GenericAlias:
            # f"The attribute '{attribute_name}' is a list of type: {attribute_type.__args__[0]}."
            attribute_type = attribute_type.__origin__  # Get the original type (e.g., list, dict)
        return attribute_type
    
    def _init_dataclass_fields(self):
        """
        Initialize the dataclass fields with default values.
        This is useful for ensuring that all fields are set correctly.
        """
        for field in self.__dataclass_fields__:
            field_type = self.get_attribute_type(field)
            if field_type is str and getattr(self, field) == "":
                setattr(self, field, None)
            elif field_type is list and isinstance(getattr(self, field), str):
                # Convert string to list if it is a string
                setattr(self, field, [item.strip() for item in getattr(self, field).split('|')] if getattr(self, field) else [])
            elif field_type not in (str, list, dict):
                raise TypeError(f"Unsupported type for metadata attribute '{field}': {field_type}. Only str, list, and dict types are allowed.")
            

@dataclass
class DocumentMetadataHistoryEntry:
    """
    Represents a single historical metadata entry for a document.
    """
    timestamp: str
    metadata: DocumentMetadata

    @classmethod
    def from_dict(cls, data: dict) -> 'DocumentMetadataHistoryEntry':
        """
        Create a DocumentMetadataHistoryEntry instance from a dictionary.
        
        :param data: Dictionary containing timestamp and metadata.
        :return: DocumentMetadataHistoryEntry instance.
        """
        return cls(
            timestamp=data.get('timestamp', ''),
            metadata=DocumentMetadata.from_dict(data.get('metadata', {}))
        )
    
    def to_dict(self) -> dict:
        """
        Convert the DocumentMetadataHistoryEntry instance to a dictionary for JSON serialization.
        
        :return: Dictionary representation of the metadata history entry.
        """
        return {
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'metadata': self.metadata.to_dict()
        }


@dataclass
class DocumentMetadataHistory:
    """
    Represents a collection of historical metadata entries for a document.
    """
    history: dict[str, DocumentMetadataHistoryEntry] = None

    @classmethod
    def from_dict(cls, data: dict | None) -> 'DocumentMetadataHistory':
        """
        Create a DocumentMetadataHistory instance from a dictionary.
        
        :param data: Dictionary containing history entries.
        :return: DocumentMetadataHistory instance.
        """
        if not data or 'history' not in data:
            return cls(history={})
        
        history_entries = {}
        for entry_data_key, entry_data in data.get('history', {}).items():
            entry = DocumentMetadataHistoryEntry.from_dict(entry_data)
            history_entries[entry_data_key] = entry
        return cls(history=history_entries)
    
    def to_dict(self) -> dict:
        """
        Convert the DocumentMetadataHistory instance to a dictionary for JSON serialization.
        
        :return: Dictionary representation of the metadata history.
        """
        return {
            'history': {key: entry.to_dict() for key, entry in self.history.items()}
        }
    
    @staticmethod
    def get_metadata_history_storage_id(pid: str) -> str:
        """
        Generate a storage ID for the metadata history based on the document PID.
        
        :return: Storage ID string.
        """
        return f"history/{pid}_metadata"
