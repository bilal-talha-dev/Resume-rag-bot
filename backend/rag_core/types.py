from dataclasses import dataclass, field


@dataclass
class SourceFile:
    rel_path: str          # posix path relative to resumes_dir (unique id of the source)
    abs_path: str
    size: int
    sha256: str


@dataclass
class ParsedResume:
    source: str
    name: str
    email: str = ""
    phone: str = ""
    links: list = field(default_factory=list)
    headline: str = ""
    # ordered [(SECTION_TITLE, [lines])]; first one is always "HEADER"
    sections: list = field(default_factory=list)
    raw_text: str = ""


@dataclass
class Chunk:
    id: str
    candidate_id: str
    candidate_name: str
    source: str
    section: str
    entry: str
    index: int
    text: str

    def metadata(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "candidate_name": self.candidate_name,
            "source": self.source,
            "section": self.section,
            "entry": self.entry,
            "chunk_index": self.index,
        }


class EmbeddingUnavailable(Exception):
    """Raised by an embedder when the remote service can't be used right now."""


class LoaderError(Exception):
    pass


class NothingIndexed(Exception):
    pass
