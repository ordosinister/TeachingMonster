"""Core Pydantic models for PDF RAG quality management."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PASS = "pass"
    RETRY = "retry"
    REVIEW_REQUIRED = "review_required"
    QUARANTINED = "quarantined"
    FAILED = "failed"


class IssueType(str, Enum):
    TEXT_MISMATCH = "text_mismatch"
    TABLE_STRUCTURE_MISMATCH = "table_structure_mismatch"
    CRITICAL_VALUE_MISMATCH = "critical_value_mismatch"
    COVERAGE_GAP = "coverage_gap"
    VISUAL_CONTENT_UNRESOLVED = "visual_content_unresolved"
    SOURCE_MAPPING_ERROR = "source_mapping_error"
    MODEL_OUTPUT_INVALID = "model_output_invalid"
    PROCESSING_ERROR = "processing_error"
    UNKNOWN = "unknown"


class VerificationStatus(str, Enum):
    PASS = "pass"
    RETRY = "retry"
    REVIEW_REQUIRED = "review_required"
    QUARANTINED = "quarantined"
    FAILED = "failed"


class ReportStatus(str, Enum):
    OPEN = "open"
    CONFIRMED = "confirmed"
    PENDING = "pending"
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    DUPLICATE = "duplicate"


class ReportCategory(str, Enum):
    TEXT_ERROR = "text_error"
    VALUE_ERROR = "value_error"
    TABLE_ERROR = "table_error"
    SOURCE_MISMATCH = "source_mismatch"
    MISSING_CONTENT = "missing_content"
    RETRIEVAL_ERROR = "retrieval_error"
    GENERATION_ERROR = "generation_error"
    OTHER = "other"


class RootCause(str, Enum):
    PDF_ISSUE = "pdf_issue"
    PARSING_ERROR = "parsing_error"
    RETRIEVAL_ERROR = "retrieval_error"
    GENERATION_ERROR = "generation_error"
    UNKNOWN = "unknown"


class BoundingBox(BaseModel):
    x0: float = Field(..., description="左側座標")
    y0: float = Field(..., description="上側座標")
    x1: float = Field(..., description="右側座標")
    y1: float = Field(..., description="下側座標")
    page_width: Optional[float] = Field(None, description="頁面寬度")
    page_height: Optional[float] = Field(None, description="頁面高度")


class TableCell(BaseModel):
    row: int
    col: int
    text: str
    bbox: Optional[BoundingBox] = None


class ExtractedTable(BaseModel):
    table_id: str
    page_number: int
    header_rows: list[list[str]] = Field(default_factory=list)
    cells: list[TableCell] = Field(default_factory=list)
    bbox: Optional[BoundingBox] = None
    row_count: int = 0
    col_count: int = 0


class ExtractedImage(BaseModel):
    image_id: str
    page_number: int
    description: Optional[str] = None
    bbox: Optional[BoundingBox] = None


class PageExtraction(BaseModel):
    page_number: int
    page_number_1_indexed: int
    text: str = ""
    tables: list[ExtractedTable] = Field(default_factory=list)
    images: list[ExtractedImage] = Field(default_factory=list)
    bbox: Optional[BoundingBox] = None
    raw_data: Optional[dict[str, Any]] = None


class DoclingResult(BaseModel):
    docling_version: Optional[str] = None
    pages: list[PageExtraction] = Field(default_factory=list)
    full_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class VLMResult(BaseModel):
    model_name: str
    provider: str
    pages: list[PageExtraction] = Field(default_factory=list)
    full_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PageComparison(BaseModel):
    page_number: int
    text_similarity: float = 0.0
    structure_score: float = 0.0
    coverage_score: float = 0.0
    critical_value_match: bool = False
    issues: list[dict[str, Any]] = Field(default_factory=list)
    details: str = ""


class ComparisonResult(BaseModel):
    comparison_id: str
    document_id: str
    run_id: str
    overall_text_similarity: float = 0.0
    overall_structure_score: float = 0.0
    overall_coverage_score: float = 0.0
    critical_values_pass: bool = False
    page_comparisons: list[PageComparison] = Field(default_factory=list)
    status: VerificationStatus = VerificationStatus.REVIEW_REQUIRED
    threshold_config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DiagnosticIssue(BaseModel):
    issue_id: str
    document_id: str
    page_number: int
    chunk_id: Optional[str] = None
    issue_type: IssueType
    bbox: Optional[BoundingBox] = None
    docling_value: Optional[str] = None
    vlm_value: Optional[str] = None
    difference: Optional[str] = None
    retry_count: int = 0
    model_name: Optional[str] = None
    model_params: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    suggested_action: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: ProcessingStatus = ProcessingStatus.REVIEW_REQUIRED
    resolved_at: Optional[datetime] = None


class ProcessingRun(BaseModel):
    run_id: str
    document_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    docling_version: Optional[str] = None
    vlm_model: Optional[str] = None
    vlm_provider: Optional[str] = None
    prompt_version: Optional[str] = None
    pipeline_version: Optional[str] = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: Optional[str] = None


class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    page_number: int
    page_number_1_indexed: int
    bbox: Optional[BoundingBox] = None
    raw_text: str = ""
    normalized_text: str = ""
    docling_text: Optional[str] = None
    vlm_text: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.REVIEW_REQUIRED
    comparison_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeedbackReport(BaseModel):
    report_id: str
    document_id: str
    chunk_id: Optional[str] = None
    page_number: Optional[int] = None
    bbox: Optional[BoundingBox] = None
    category: ReportCategory
    user_description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: ReportStatus = ReportStatus.OPEN
    root_cause: Optional[RootCause] = None
    diagnosis_result: Optional[str] = None
    reprocessing_run_id: Optional[str] = None
    resolved_at: Optional[datetime] = None


class RegressionCase(BaseModel):
    case_id: str
    document_id: str
    page_number: int
    chunk_id: Optional[str] = None
    issue_type: IssueType
    expected_value: Optional[str] = None
    correct_value: Optional[str] = None
    error_type: Optional[str] = None
    model_version: Optional[str] = None
    pipeline_version: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    test_sample_path: Optional[str] = None


class DocumentRecord(BaseModel):
    document_id: str
    original_path: str
    storage_path: str
    sha256: str
    original_filename: str
    file_size_bytes: int
    imported_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    docling_version: Optional[str] = None
    vlm_model: Optional[str] = None
    vlm_provider: Optional[str] = None
    prompt_version: Optional[str] = None
    pipeline_version: str = "1.0.0"


class SourceTrace(BaseModel):
    answer_text: Optional[str] = None
    chunk_id: str
    document_id: str
    document_filename: str
    page_number: int
    page_number_1_indexed: int
    bbox: Optional[BoundingBox] = None
    storage_path: str
    chunk_text: Optional[str] = None
    extraction_method: Optional[str] = None
    verification_status: Optional[VerificationStatus] = None
