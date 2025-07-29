from dataclasses import dataclass

from application.settings import APP_URL


@dataclass
class DocumentRecord:
    pid: str
    version: int
    storage_id: str
    owner_id: str
    parent_doc_pid: str | None = None  # previous document pid in the lineage
    created_at: str | None = None  # timestamp of creation
    updated_at: str | None = None  # timestamp of the last update

    def __post_init__(self):
        if isinstance(self.version, str):
            self.version = int(self.version)

    @property
    def storage_url(self) -> str:
        return f"{APP_URL}/documents/{self.pid}/download"
