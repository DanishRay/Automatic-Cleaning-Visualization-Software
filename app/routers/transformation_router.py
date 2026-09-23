import os
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.data_service import DataService
from app.services.transformation_service import TransformationService

router = APIRouter(prefix="/api/transformation", tags=["transform"])


def extract_script_list(pipeline_or_scripts: Optional[List[Any]]) -> Optional[List[str]]:
    if not pipeline_or_scripts:
        return None

    extracted_scripts = []
    for item in pipeline_or_scripts:
        if isinstance(item, dict):
            code = item.get("code") or item.get("script") or ""
            if code.strip():
                extracted_scripts.append(code)
        elif isinstance(item, str):
            if item.strip():
                extracted_scripts.append(item)
    return extracted_scripts if extracted_scripts else None


class RScriptPipelineRequest(BaseModel):
    scripts: Optional[List[str]] = []


class PreviewCodeRequest(BaseModel):
    code: Optional[str] = ""
    r_script: Optional[str] = ""
    operations: Optional[List[Dict[str, Any]]] = None
    scripts: Optional[List[Union[str, Dict[str, Any]]]] = None
    pipeline: Optional[List[Union[str, Dict[str, Any]]]] = None


class SaveRequest(BaseModel):
    save_filename: str
    operations: Optional[List[Dict[str, Any]]] = None
    r_script: Optional[str] = None
    scripts: Optional[List[Union[str, Dict[str, Any]]]] = None
    pipeline: Optional[List[Union[str, Dict[str, Any]]]] = None
    data: Optional[List[Dict[str, Any]]] = None


@router.post("/run-r-pipeline")
async def run_r_pipeline(payload: RScriptPipelineRequest):
    try:
        transformed_df = TransformationService.apply_transformations(
            scripts=payload.scripts
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
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-r-pipeline/{filename}")
async def run_r_pipeline_file(filename: str, payload: RScriptPipelineRequest):
    file_path = os.path.join("temp_storage", filename)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, detail="File not found in storage."
        )
    try:
        transformed_df = TransformationService.apply_transformations(
            filename, scripts=payload.scripts
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
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview")
async def preview_code_transformation(payload: PreviewCodeRequest):
    try:
        script = payload.code or payload.r_script or ""
        raw_scripts = payload.scripts or payload.pipeline
        scripts = extract_script_list(raw_scripts)

        transformed_df = TransformationService.apply_transformations(
            "active_session",
            r_script=script,
            operations=payload.operations,
            scripts=scripts,
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
        if isinstance(e, HTTPException):
            raise e
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
        raw_scripts = payload.get("scripts") or payload.get("pipeline")
        scripts = extract_script_list(raw_scripts)

        transformed_df = TransformationService.apply_transformations(
            filename, operations=operations, r_script=r_script, scripts=scripts
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
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save/{filename}")
async def save_transformed_data(filename: str, payload: SaveRequest):
    try:
        raw_scripts = payload.scripts or payload.pipeline
        scripts = extract_script_list(raw_scripts)

        path = TransformationService.save_transformed_data(
            filename,
            operations=payload.operations,
            save_filename=payload.save_filename,
            r_script=payload.r_script,
            scripts=scripts,
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
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))