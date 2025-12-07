import logging
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()

DEFAULT_BLOB_UUID = UUID("00000000-0000-0000-0000-000000000000")
blob_storage: dict[UUID, bytes] = {}


def initialize_blob_storage():
    blob_path = Path("blobs") / str(DEFAULT_BLOB_UUID)
    try:
        with open(blob_path, "rb") as f:
            data = f.read()
        blob_storage[DEFAULT_BLOB_UUID] = data
        logger.info(f"Loaded default blob (Oicana logo) with UUID {DEFAULT_BLOB_UUID}")
    except Exception as e:
        logger.error(f"Failed to load default blob from {blob_path}: {e}")


def get_blob(blob_id: UUID) -> bytes | None:
    if blob_id in blob_storage:
        return blob_storage[blob_id]

    blob_path = Path("blobs") / str(blob_id)
    try:
        with open(blob_path, "rb") as f:
            data = f.read()
        blob_storage[blob_id] = data
        logger.info(f"Loaded blob {blob_id} from disk and cached it")
        return data
    except Exception as e:
        logger.warning(f"Failed to read blob {blob_id} from {blob_path}: {e}")
        return None


class UploadResponse(BaseModel):
    id: UUID = Field(description="The UUID assigned to the uploaded blob")

    model_config = {
        "json_schema_extra": {"examples": [{"id": "550e8400-e29b-41d4-a716-446655440000"}]}
    }


@router.post(
    "",
    response_model=UploadResponse,
    responses={
        200: {"description": "Blob uploaded successfully"},
        400: {"description": "Invalid file upload"},
        500: {"description": "Failed to save file to disk"},
    },
    description=(
        "Upload a blob (image, file, etc.) to use as template input. "
        "Returns a UUID to reference the blob in compilation requests."
    ),
)
async def upload_blob(file: UploadFile = File(..., description="The file to upload")):
    try:
        file_data = await file.read()
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        raise HTTPException(status_code=400, detail="Failed to read file") from e

    blob_id = uuid4()
    blob_path = Path("blobs") / str(blob_id)

    try:
        blob_path.parent.mkdir(parents=True, exist_ok=True)
        with open(blob_path, "wb") as f:
            f.write(file_data)
    except Exception as e:
        logger.error(f"Failed to write blob {blob_id} to {blob_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file") from e

    blob_storage[blob_id] = file_data
    logger.info(f"Stored blob {blob_id} to disk and cache")

    return UploadResponse(id=blob_id)


initialize_blob_storage()
