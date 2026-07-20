from dataclasses import dataclass, field


@dataclass
class KnowledgeElement:
    text: str
    source: str
    page: int | None = None
    section_path: str = ""
    content_type: str = "text"
    extra_metadata: dict = field(default_factory=dict)

    def metadata(self) -> dict:
        metadata = {
            "source": self.source,
            "page": self.page if self.page is not None else "",
            "section_path": self.section_path,
            "content_type": self.content_type,
        }
        metadata.update(self.extra_metadata)
        return metadata
