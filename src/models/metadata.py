from dataclasses import dataclass


@dataclass
class DocumentMetadata:
    title: str | None = None
    description: str | None = None
    keywords: list[str] | None = None  # later converted to strings separated by pipe `|` character

    # When adding new fields, update also:
    # - services/pid/handle/record.py and base.py
    # - DocumentMetadataGet in routers/metadata/_get.py

    def __post_init__(self):
        if isinstance(self.keywords, str):
            self.keywords = [k.strip() for k in self.keywords.split('|')] if self.keywords else []
        if self.title == "":
            self.title = None
        if self.description == "":
            self.description = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DocumentMetadata':
        """
        Create a DocumentMetadata instance from a dictionary.
        
        :param data: Dictionary containing metadata fields.
        :return: DocumentMetadata instance.
        """
        if not data:
            return cls()
        return cls(
            title=data.get('title'),
            description=data.get('description'),
            keywords=data.get('keywords')
        )
    
    def to_dict(self) -> dict:
        """
        Convert the DocumentMetadata instance to a dictionary for JSON serialization.
        
        :return: Dictionary representation of the metadata.
        """
        return {
            "title": self.title,
            "description": self.description,
            "keywords": "|".join([k.strip() for k in self.keywords]) if self.keywords else None
        }
