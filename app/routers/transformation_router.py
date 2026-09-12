import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.data_service import DataService
from app.services.transformation_service import TransformationService

router = APIRouter(prefix="/api/v1/transform", tags=["transform"])


class PreviewCodeRequest(BaseModel):
    code: Optional[str] = ""
    r_script: Optional[str] = ""
    operations: Optional[List[Dict[str, Any]]] = None


class PreviewOperationsRequest(BaseModel):
    operations: Optional[List[Dict[str, Any]]] = []
    r_script: Optional[str] = ""


class SaveRequest(BaseModel):
    save_filename: str
    operations: Optional[List[Dict[str, Any]]] = None
    r_script: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None


@router.post("/preview")
async def preview_code_transformation(payload: PreviewCodeRequest):
    try:
        script = payload.code or payload.r_script or ""
        transformed_df = TransformationService.apply_transformations(
            "active_session", r_script=script, operations=payload.operations
        )

        return {
            "status": "success",
            "columns": list(transformed_df.columns),
            "rows": len(transformed_df),
            "columns_count": len(transformed_df.columns),
            "data": transformed_df.head(100)
            .fillna("")
            .to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview/{filename}")
async def preview_transformations(
    filename: str, payload: Dict[str, Any] = Body(default={})
):
    file_path = os.path.join("temp_storage", filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, detail="File not found in storage."
        )
    try:
        operations = payload.get("operations", [])
        r_script = payload.get("r_script", payload.get("code", ""))
        transformed_df = TransformationService.apply_transformations(
            filename, operations=operations, r_script=r_script
        )

        active_id = f"session_{filename}"
        DataService.save_session_data(active_id, transformed_df)

        return {
            "status": "success",
            "columns": list(transformed_df.columns),
            "rows": len(transformed_df),
            "columns_count": len(transformed_df.columns),
            "data": transformed_df.head(100)
            .fillna("")
            .to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/r-preview/{filename}")
async def r_preview_transformations(
    filename: str, payload: Dict[str, Any] = Body(default={})
):
    file_path = os.path.join("temp_storage", filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, detail="File not found in storage."
        )
    try:
        r_script = payload.get("r_script", payload.get("code", ""))
        transformed_df = TransformationService.apply_transformations(
            filename, r_script=r_script
        )

        active_id = f"session_{filename}"
        DataService.save_session_data(active_id, transformed_df)

        return {
            "status": "success",
            "columns": list(transformed_df.columns),
            "rows": len(transformed_df),
            "columns_count": len(transformed_df.columns),
            "data": transformed_df.head(100)
            .fillna("")
            .to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save/{filename}")
async def save_transformed_data(filename: str, payload: SaveRequest):
    try:
        path = TransformationService.save_transformed_data(
            filename,
            operations=payload.operations,
            save_filename=payload.save_filename,
            r_script=payload.r_script,
        )
        if not os.path.exists(path):
            raise HTTPException(
                status_code=404, detail="Processed file not found."
            )

        saved_df = DataService.load_data_to_df(path)
        active_id = f"session_{payload.save_filename}"
        DataService.save_session_data(active_id, saved_df)

        return FileResponse(path, filename=payload.save_filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))