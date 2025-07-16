from enum import Enum
from dataclasses import dataclass


# Existing default values for handle records:
# HS_ADMIN, HS_SECKEY, EMAIL, URL, HS_PUBKEY, URN, HS_SERV, HS_VLIST, HS_ALIAS
class HandleValueType(Enum):
    URL = "URL"
    EMAIL = "EMAIL"
    HS_ADMIN = "HS_ADMIN"
    HS_VLIST = "HS_VLIST"
    HS_PUBKEY = "HS_PUBKEY"

    # Document PID record attributes
    TYPE = "TYPE"
    VERSION = "VERSION"
    LOCATION = "LOCATION"
    PARENT_DOC_PID = "PARENT_DOC_PID"
    TREE_PID = "TREE_PID"

    # Tree PID record attributes
    FIRST_DOCUMENT_PID = "FIRST_DOCUMENT_PID"
    LATEST_DOCUMENT_PID = "LATEST_DOCUMENT_PID"
    LATEST_VERSION = "LATEST_VERSION"

    # Metadata attributes
    TITLE = "TITLE"
    DESCRIPTION = "DESCRIPTION"
    KEYWORDS = "KEYWORDS"
    # ...

    @classmethod
    def from_pid_record_attribute(cls, attribute: str) -> 'HandleValueType':
        """
        Convert a PID record attribute to a HandleValueType.
        """
        if attribute not in cls.__members__:
            raise AttributeError(f"Attribute '{attribute}' is not a valid storable metadata.")
        return cls[attribute]

    def __str__(self):
        return self.value


# Allowed values:
# string, base64, vlist, admin, hex, site, key (of which some are not used)
class HandleValueDataFormat(Enum):
    STRING = "string"
    VLIST = "vlist"
    ADMIN = "admin"

    def __str__(self):
        return self.value


@dataclass
class HandleValueDataListItem:
    """
    Represents an item in a HandleValueObject where format='vlist' and type='HS_VLIST'(?).
    Not used in the application at the moment but added for the eventuality we need a list of PIDs.
    """
    handle: str
    list: int


@dataclass
class HandleValueDataAdmin:
    handle: str
    index: int
    permissions: str
    # The admin permission set is twelve characters with the following order:
    # 1. add handle
    # 2. delete handle
    # 3. no add naming authority
    # 4. no delete naming authority
    # 5. modify values
    # 6. remove values
    # 7. add values
    # 8. read values
    # 9. modify administrator
    # 10. remove administrator
    # 11. add administrator
    # 12. list handles


@dataclass
class HandleValueObject:
    format: HandleValueDataFormat
    value: str | HandleValueDataListItem | HandleValueDataAdmin


@dataclass
class HandleValue:

    index: int
    type: HandleValueType
    data: str | HandleValueObject

    # `permissions` is a string representing the bitmask of permissions.
    # Generally this is "1110" (admin read, admin write, public read, not public write) in which case it is omitted.
    # Values of type "HS_SECKEY" generally use "permissions":"1100"
    # permissions: str = "1110"

    def __post_init__(self):
        if type == HandleValueType.HS_ADMIN:
            if not isinstance(self.data, HandleValueObject) or self.data.format != HandleValueDataFormat.ADMIN \
                or not isinstance(self.data.value, HandleValueDataAdmin):
                raise ValueError("HS_ADMIN type must have data in HandleValueObject format with ADMIN value type.")
        elif type == HandleValueType.HS_VLIST:
            if not isinstance(self.data, HandleValueObject) or self.data.format != HandleValueDataFormat.VLIST \
                or not isinstance(self.data.value, list) or not all(isinstance(item, HandleValueDataListItem) for item in self.data.value):
                raise ValueError("HS_VLIST type must have data in HandleValueObject format with VLIST value type containing a list of HandleValueDataListItem.")
