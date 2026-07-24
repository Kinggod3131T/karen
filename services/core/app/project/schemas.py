from pydantic import BaseModel, Field


class ProjectScanRequest(BaseModel):
    path: str = "karen"
    max_files: int = Field(default=5000, ge=1, le=20_000)
    max_file_bytes: int = Field(
        default=2_000_000,
        ge=1024,
        le=5_000_000,
    )


class ProjectFile(BaseModel):
    path: str
    size: int
    language: str
    kind: str


class ProjectSummary(BaseModel):
    index_id: str
    root: str
    name: str
    git_repository: bool
    total_files: int
    total_bytes: int
    truncated: bool
    languages: dict[str, int]
    frameworks: list[str]
    manifests: list[str]
    entrypoints: list[str]
    ignored_directories: list[str]
    sample_files: list[ProjectFile]
    indexed_at: str
