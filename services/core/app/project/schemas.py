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


class ProjectContextRequest(BaseModel):
    path: str = "karen"
    task: str = Field(min_length=1, max_length=20_000)
    max_files: int = Field(default=8, ge=1, le=20)
    max_chars_per_file: int = Field(
        default=6000,
        ge=500,
        le=20_000,
    )
    max_total_chars: int = Field(
        default=30_000,
        ge=2000,
        le=80_000,
    )


class ContextFile(BaseModel):
    path: str
    language: str
    kind: str
    score: float
    reasons: list[str]
    content: str
    truncated: bool


class ProjectContext(BaseModel):
    index_id: str
    project_root: str
    task: str
    selected_files: list[ContextFile]
    total_characters: int
    generated_at: str


class ProjectChatRequest(ProjectContextRequest):
    model: str | None = None


class ProjectChatResponse(BaseModel):
    model: str
    response: str
    done: bool
    index_id: str
    context_files: list[str]
    context_characters: int
