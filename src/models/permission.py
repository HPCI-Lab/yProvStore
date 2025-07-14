from enum import Enum
from dataclasses import dataclass


class PermissionLevel(Enum):
    READ = "read"
    WRITE = "write"

    def __lt__(self, other):
        if not isinstance(other, PermissionLevel):
            return NotImplemented
        return list(PermissionLevel).index(self) < list(PermissionLevel).index(other)

    def __le__(self, other):
        if not isinstance(other, PermissionLevel):
            return NotImplemented
        return list(PermissionLevel).index(self) <= list(PermissionLevel).index(other)

    def __gt__(self, other):
        if not isinstance(other, PermissionLevel):
            return NotImplemented
        return list(PermissionLevel).index(self) > list(PermissionLevel).index(other)

    def __ge__(self, other):
        if not isinstance(other, PermissionLevel):
            return NotImplemented
        return list(PermissionLevel).index(self) >= list(PermissionLevel).index(other)

    def __str__(self):
        return self.value


@dataclass
class DocumentPermission:
    pid: str
    user_id: str
    permission_level: PermissionLevel
