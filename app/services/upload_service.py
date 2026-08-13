import cloudinary
import asyncio
import cloudinary.uploader
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings
from typing import Optional

# Cloudinary Config
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)



async def upload_to_cloudinary(
    file: UploadFile,
    folder: str = "companies",
    public_id: Optional[str] = None,
) -> str:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files (jpg, png, etc.) are allowed",
        )
    
    try:
        content = await file.read()

        upload_result =  {
            "folder": f"bus_ticket/{folder}",
            "resource_type": "image",
            "transformation": [
                {"width": 500, "height": 500, "crop": "limit"},
                {"quality": "auto"},
                {"fetch_format": "auto"},
            ],
        }

        if public_id:
            upload_result["public_id"] = public_id

        result = await asyncio.to_thread(
            cloudinary.uploader.upload,
            content,
            **upload_result
        )

        return result["secure_url"]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload to Cloudinary: {str(e)}"
        )


async def delete_from_cloudinary(public_id: str) -> None:
    try:
        result = await asyncio.to_thread(
            cloudinary.uploader.destroy, 
            public_id
        )
        return result.get("result") == "ok"
    except Exception as e:
        return False


def extract_public_id_from_url(url: str) -> Optional[str]:
    try:
        parts = url.split("/upload/")
        if len(parts) < 2:
            return None

        # remove version and get path
        path_parts = parts[1].split("/")
        if path_parts[0].startswith("v"):
            path_parts = path_parts[1:]

        public_id = "/".join(path_parts)
        public_id = public_id.rsplit(".", 1)[0]  # Remove file extension
        return public_id
    except Exception:
        return None
