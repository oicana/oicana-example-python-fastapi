import json
import logging

from fastapi import APIRouter, HTTPException, Response
from oicana import CompilationMode
from pydantic import BaseModel, Field

from .templates import template_cache

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateCertificate(BaseModel):
    name: str = Field(description="Name to create the certificate for")

    model_config = {"json_schema_extra": {"examples": [{"name": "Jane Doe"}]}}


@router.post(
    "",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "The compiled PDF certificate",
        }
    },
    description="Create a certificate",
)
async def create_certificate(request: CreateCertificate):
    template_id = "certificate"

    if template_id not in template_cache:
        logger.error("Certificate template not found!")
        raise HTTPException(
            status_code=500,
            detail="Certificate template not found!",
        )

    template = template_cache[template_id]

    json_inputs = {"certificate": json.dumps({"name": request.name})}

    try:
        pdf_bytes = template.compile(
            json_inputs=json_inputs,
            export_format={"format": "pdf"},
            mode=CompilationMode.PRODUCTION,
        )
    except Exception as e:
        logger.error(f"Certificate template failed to compile: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to compile certificate: {e}",
        ) from e

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="certificate.pdf"'},
    )
