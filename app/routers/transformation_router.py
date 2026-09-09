from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.services.data_service import DataService
from app.services.transformation_service import TransformationService
import os

router = APIRouter(prefix="/api/v1/transform", tags=["Data Transformation"])

class TransformationPayload(BaseModel):
    operations: Optional[List[Dict[str, Any]]] = None
    save_filename: str
    r_script: Optional[str] = None

@router.post("/preview/{filename}")
async def preview_transformations(filename: str, payload: Dict[str, Any] = Body(...)):
    file_path = os.path.join("temp_storage", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found in storage.")
    try:
        operations = payload.get("operations", [])
        original_df = DataService.load_data_to_df(file_path)
        transformed_df = TransformationService.apply_transformations(filename, operations=operations)

        return {
            "columns": transformed_df.columns.tolist(),
            "data": transformed_df.head(100).fillna("").to_dict(orient="records"),
            "original_rows": len(original_df),
            "transformed_rows": len(transformed_df),
            "original_columns": len(original_df.columns),
            "transformed_columns": len(transformed_df.columns)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/r-preview/{filename}")
async def r_preview_transformations(filename: str, payload: Dict[str, Any] = Body(...)):
    file_path = os.path.join("temp_storage", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found in storage.")
    try:
        r_script = payload.get("r_script", "")
        original_df = DataService.load_data_to_df(file_path)
        transformed_df = TransformationService.apply_transformations(filename, r_script=r_script)

        return {
            "columns": transformed_df.columns.tolist(),
            "data": transformed_df.head(100).fillna("").to_dict(orient="records"),
            "original_rows": len(original_df),
            "transformed_rows": len(transformed_df),
            "original_columns": len(original_df.columns),
            "transformed_columns": len(transformed_df.columns)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save/{filename}")
async def save_transformed_data(filename: str, payload: TransformationPayload):
    try:
        path = TransformationService.save_transformed_data(
            filename, operations=payload.operations, save_filename=payload.save_filename, r_script=payload.r_script
        )
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Processed file not found.")
        return FileResponse(path, filename=payload.save_filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))