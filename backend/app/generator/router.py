"""FastAPI router for document, code, and DDL generation endpoints."""

import logging
import tempfile
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.connections.pool import pool_manager
from app.connections.service import ConnectionService
from app.database.session import get_db
from app.explorer.service import ExplorerService
from app.generator.code_generator import CodeGenerator
from app.generator.ddl_converter import DDLConverter
from app.generator.ddl_generator import DDLGenerator
from app.generator.doc_generator import DocGenerator
from app.utils.audit import log_audit
from app.utils.responses import ErrorResponse, SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generator", tags=["Generator"])

conn_svc = ConnectionService()


# --- Request / Response schemas ---


class DocGenerateRequest(BaseModel):
    connection_id: int
    tables: list[str] = Field(..., description="List of table names to document")
    format: str = Field(default="markdown", description="Output format: markdown, docx, pdf")
    schema_name: Optional[str] = Field(default=None, description="Database schema name")


class CodeGenerateRequest(BaseModel):
    connection_id: int
    tables: list[str] = Field(..., description="List of table names")
    target: str = Field(..., description="Target: sqlalchemy, django, pydantic, typescript, go, java")
    naming_style: str = Field(default="snake_case", description="Naming style: snake_case, camelCase, PascalCase")
    include_comments: bool = Field(default=False)
    schema_name: Optional[str] = Field(default=None)


class DDLGenerateRequest(BaseModel):
    connection_id: int
    tables: list[str] = Field(..., description="List of table names")
    include_indexes: bool = Field(default=True)
    include_foreign_keys: bool = Field(default=True)
    schema_name: Optional[str] = Field(default=None)


class DDLConvertRequest(BaseModel):
    ddl: str = Field(..., description="DDL statement to convert")
    source: str = Field(..., description="Source dialect: mysql, postgresql, oracle")
    target: str = Field(..., description="Target dialect: mysql, postgresql, oracle")


# --- Helpers ---


async def _resolve(db: AsyncSession, connection_id: int):
    """Resolve connection and return (connection_model, engine, inspector) or None."""
    connection = await conn_svc.get_connection_model(db, connection_id)
    if connection is None:
        return None
    config = {
        "db_type": connection.db_type,
        "host": connection.host,
        "port": connection.port,
        "username": connection.username,
        "password": ConnectionService.get_decrypted_password(connection),
        "database_name": connection.database_name,
        "extra_params": connection.get_extra_params(),
        "pool_size": connection.pool_size,
    }
    engine = pool_manager.get_or_create_pool(connection_id, config)
    inspector = inspect(engine)
    return connection, engine, inspector


def _gather_table_metadata(engine, inspector, table_name: str, schema: Optional[str], db_type: str) -> dict:
    """Gather complete metadata for a single table, including its comment."""
    explorer = ExplorerService(inspector)
    columns = explorer.get_columns(table_name, schema=schema)
    indexes = explorer.get_indexes(table_name, schema=schema)
    foreign_keys = explorer.get_foreign_keys(table_name, schema=schema)

    # Fetch table comment
    comment = ""
    try:
        from sqlalchemy import text

        if db_type == "mysql":
            with engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT TABLE_COMMENT FROM INFORMATION_SCHEMA.TABLES "
                        "WHERE TABLE_NAME = :tbl AND TABLE_SCHEMA = DATABASE()"
                    ),
                    {"tbl": table_name},
                )
                row = result.fetchone()
                if row:
                    comment = row[0] or ""
        elif db_type == "postgresql":
            with engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT obj_description(c.oid) FROM pg_class c "
                        "JOIN pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE c.relname = :tbl AND n.nspname = 'public'"
                    ),
                    {"tbl": table_name},
                )
                row = result.fetchone()
                if row and row[0]:
                    comment = row[0]
        elif db_type == "oracle":
            with engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT COMMENTS FROM ALL_TAB_COMMENTS "
                        "WHERE TABLE_NAME = :tbl AND OWNER = USER"
                    ),
                    {"tbl": table_name.upper()},
                )
                row = result.fetchone()
                if row and row[0]:
                    comment = row[0]
    except Exception:
        comment = ""

    return {
        "name": table_name,
        "columns": columns,
        "indexes": indexes,
        "foreign_keys": foreign_keys,
        "comment": comment,
        "db_type": db_type,
    }


# --- Endpoints ---


@router.post("/doc", response_model=None)
async def generate_document(
    req: DocGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate database documentation in the specified format.

    Supports markdown (returned as text), docx (Word file), and pdf (HTML-based).
    """
    resolved = await _resolve(db, req.connection_id)
    if resolved is None:
        return ErrorResponse(message="Connection not found.", code=404)

    connection, engine, inspector = resolved
    db_type = connection.db_type
    db_name = connection.database_name

    # Gather metadata for requested tables
    tables_metadata = []
    for table_name in req.tables:
        meta = _gather_table_metadata(engine, inspector, table_name, req.schema_name, db_type)
        # Generate DDL for each table
        ddl = DDLGenerator.generate_create_table(meta)
        meta["ddl"] = ddl
        tables_metadata.append(meta)

    fmt = req.format.lower()

    if fmt == "markdown":
        content = DocGenerator.generate_markdown(tables_metadata, db_name, db_type)
        return Response(
            content=content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={db_name}_doc.md"},
        )
    elif fmt == "docx":
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            DocGenerator.generate_docx(tables_metadata, db_name, db_type, tmp.name)
            tmp.seek(0)
            with open(tmp.name, "rb") as f:
                content = f.read()
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={db_name}_doc.docx"},
        )
    elif fmt == "pdf":
        content, actual_format = DocGenerator.generate_pdf_bytes(
            tables_metadata, db_name, db_type
        )
        if actual_format == "pdf":
            return Response(
                content=content,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={db_name}_doc.pdf"},
            )
        else:
            # WeasyPrint not available — fallback to HTML
            return Response(
                content=content,
                media_type="text/html; charset=utf-8",
                headers={"Content-Disposition": f"attachment; filename={db_name}_doc.html"},
            )
    else:
        return ErrorResponse(
            message=f"Unsupported format: '{fmt}'. Use markdown, docx, or pdf.",
            code=400,
        )


@router.post("/code", response_model=None)
async def generate_code(
    req: CodeGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate ORM/model code for the specified tables and target language."""
    resolved = await _resolve(db, req.connection_id)
    if resolved is None:
        return ErrorResponse(message="Connection not found.", code=404)

    connection, engine, inspector = resolved
    db_type = connection.db_type

    # Gather metadata for requested tables
    tables_metadata = []
    for table_name in req.tables:
        meta = _gather_table_metadata(engine, inspector, table_name, req.schema_name, db_type)
        tables_metadata.append(meta)

    # Generate code for each table
    code_parts = []
    generator = CodeGenerator()
    for table_meta in tables_metadata:
        try:
            code = generator.generate(
                table=table_meta,
                target=req.target,
                naming_style=req.naming_style,
                include_comments=req.include_comments,
            )
            code_parts.append(code)
        except ValueError as exc:
            return ErrorResponse(message=str(exc), code=400)

    combined = "\n\n".join(code_parts)
    return SuccessResponse(data={"code": combined, "target": req.target, "tables": req.tables})


@router.post("/ddl", response_model=None)
async def generate_ddl(
    req: DDLGenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate DDL (CREATE TABLE) statements for the specified tables."""
    resolved = await _resolve(db, req.connection_id)
    if resolved is None:
        return ErrorResponse(message="Connection not found.", code=404)

    connection, engine, inspector = resolved
    db_type = connection.db_type

    tables_metadata = []
    for table_name in req.tables:
        meta = _gather_table_metadata(engine, inspector, table_name, req.schema_name, db_type)
        tables_metadata.append(meta)

    ddl_parts = []
    generator = DDLGenerator()
    for table_meta in tables_metadata:
        ddl = generator.generate_create_table(
            table_meta,
            include_indexes=req.include_indexes,
            include_foreign_keys=req.include_foreign_keys,
        )
        ddl_parts.append(ddl)

    combined = "\n\n".join(ddl_parts)

    # Audit log for DDL export
    await log_audit(
        db,
        action="create",
        resource_type="ddl_export",
        user_info=request.client.host if request.client else None,
        details={
            "connection_id": req.connection_id,
            "tables": req.tables,
            "include_indexes": req.include_indexes,
            "include_foreign_keys": req.include_foreign_keys,
        },
    )
    await db.commit()

    return SuccessResponse(data={"ddl": combined, "tables": req.tables})


@router.post("/ddl/convert", response_model=None)
async def convert_ddl(req: DDLConvertRequest):
    """Convert a DDL statement from one database dialect to another."""
    try:
        converted = DDLConverter.convert(
            ddl=req.ddl,
            source=req.source,
            target=req.target,
        )
        return SuccessResponse(data={
            "original": req.ddl,
            "converted": converted,
            "source": req.source,
            "target": req.target,
        })
    except ValueError as exc:
        return ErrorResponse(message=str(exc), code=400)
