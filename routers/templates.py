import json
import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from oicana import BlobInput, CompilationMode, Template
from pydantic import BaseModel, Field

from .blobs import get_blob

logger = logging.getLogger(__name__)

router = APIRouter()

TEMPLATES = [
    ("accessibility", "0.1.0"),
    ("certificate", "0.1.0"),
    ("dependency", "0.1.0"),
    ("fonts", "0.1.0"),
    ("invoice", "0.1.0"),
    ("invoice_zugferd", "0.1.0"),
    ("minimal", "0.1.0"),
    ("table", "0.1.0"),
    ("multi_input", "0.1.0"),
]

template_cache: dict[str, Template] = {}


class JsonInputDto(BaseModel):
    key: str
    value: dict

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "key": "data",
                    "value": {
                        "test": "example content",
                        "items": [
                            {"name": "Frank", "one": "A", "two": "C", "three": "A"},
                            {"name": "John", "one": "C", "two": "no show", "three": "B"},
                        ],
                    },
                }
            ]
        }
    }


class BlobInputDto(BaseModel):
    key: str
    blob_id: UUID = Field(alias="blobId")

    model_config = {
        "json_schema_extra": {
            "examples": [{"key": "logo", "blobId": "00000000-0000-0000-0000-000000000000"}]
        },
        "populate_by_name": True,
    }


class CompilationPayload(BaseModel):
    json_inputs: list[JsonInputDto] = Field(default=[], alias="jsonInputs")
    blob_inputs: list[BlobInputDto] = Field(default=[], alias="blobInputs")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "jsonInputs": [
                        {
                            "key": "data",
                            "value": {
                                "description": "from sample data",
                                "rows": [
                                    {
                                        "name": "Frank",
                                        "one": "first",
                                        "two": "second",
                                        "three": "third",
                                    },
                                    {
                                        "name": "John",
                                        "one": "first_john",
                                        "two": "second_john",
                                        "three": "third_john",
                                    },
                                ],
                            },
                        }
                    ],
                    "blobInputs": [
                        {"key": "logo", "blobId": "00000000-0000-0000-0000-000000000000"}
                    ],
                }
            ]
        },
        "populate_by_name": True,
    }


def warm_up_templates():
    for template_id, version in TEMPLATES:
        template_file = Path(f"templates/{template_id}-{version}.zip")
        if not template_file.exists():
            logger.error(f"Template file not found: {template_file}")
            continue

        try:
            with open(template_file, "rb") as f:
                template_bytes = f.read()
            template = Template(template_bytes, mode=CompilationMode.DEVELOPMENT)
            template_cache[template_id] = template
            logger.info(f"Warmed-up {template_id} v{version}")
        except Exception as e:
            logger.error(f"Failed to warm up template {template_id} v{version}: {e}")


@router.post(
    "/{template_id}/compile",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Success",
        }
    },
    description="Compile a template with given inputs.",
)
async def compile_template(template_id: str, payload: CompilationPayload):
    if template_id not in template_cache:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found!")

    template = template_cache[template_id]

    json_inputs = {}
    for json_input in payload.json_inputs:
        json_inputs[json_input.key] = json.dumps(json_input.value)

    blob_inputs = {}
    for blob_input in payload.blob_inputs:
        blob_data = get_blob(blob_input.blob_id)
        if blob_data is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Blob with id {blob_input.blob_id} not found. "
                    "Please use an ID of a blob that was previously uploaded."
                ),
            )
        blob_inputs[blob_input.key] = BlobInput(data=blob_data)

    try:
        pdf_bytes = template.compile(
            json_inputs=json_inputs,
            blob_inputs=blob_inputs,
            export={"format": "pdf"},
            mode=CompilationMode.PRODUCTION,
        )
    except Exception as e:
        logger.error(f"Template '{template_id}' failed to compile: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Template '{template_id}' failed to compile with given inputs: {e}",
        ) from e

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{template_id}.pdf"'},
    )


@router.post(
    "/{template_id}/preview",
    response_class=Response,
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "Success",
        }
    },
    description="Generate a PNG preview of the template with given inputs.",
)
async def preview_template(template_id: str, payload: CompilationPayload):
    if template_id not in template_cache:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found!")

    template = template_cache[template_id]

    json_inputs = {}
    for json_input in payload.json_inputs:
        json_inputs[json_input.key] = json.dumps(json_input.value)

    blob_inputs = {}
    for blob_input in payload.blob_inputs:
        blob_data = get_blob(blob_input.blob_id)
        if blob_data is None:
            raise HTTPException(
                status_code=400,
                detail=f"Blob with id {blob_input.blob_id} not found.",
            )
        blob_inputs[blob_input.key] = BlobInput(data=blob_data)

    try:
        png_bytes = template.compile(
            json_inputs=json_inputs,
            blob_inputs=blob_inputs,
            export={"format": "png", "pixelsPerPt": 1.0},
            mode=CompilationMode.DEVELOPMENT,
        )
    except Exception as e:
        logger.error(f"Template '{template_id}' failed to compile: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Template '{template_id}' failed to compile: {e}",
        ) from e

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="{template_id}.png"'},
    )


@router.post(
    "/{template_id}/reset",
    status_code=204,
    responses={
        204: {"description": "Template successfully removed from cache"},
        404: {"description": "Template not found in cache"},
    },
    description=(
        "Reset (remove) a template from the cache. The template will be reloaded on next use."
    ),
)
async def reset_template(template_id: str):
    if template_id in template_cache:
        del template_cache[template_id]
        logger.info(f"Template '{template_id}' removed from cache")
        return Response(status_code=204)
    else:
        logger.error(f"Template '{template_id}' not found in cache")
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found in cache")


@router.get(
    "/{template_id}",
    response_class=FileResponse,
    responses={
        200: {
            "content": {"application/zip": {}},
            "description": "Success",
        }
    },
    description="Download a packed template.",
)
async def get_template(template_id: str):
    template_path = Path(f"templates/{template_id}-0.1.0.zip")
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")

    return FileResponse(
        path=template_path,
        media_type="application/zip",
        filename=f"{template_id}.zip",
    )


@router.get(
    "",
    response_model=list[str],
    description="Get a list of all template IDs known to the service.",
)
async def get_template_list():
    return [template_id for template_id, _ in TEMPLATES]
