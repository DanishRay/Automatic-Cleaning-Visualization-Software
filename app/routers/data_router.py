from fastapi import APIRouter, HTTPException
from app.services.data_service import DataService
import os

router = APIRouter(prefix="/api/v1/data", tags=["Data Processing"])

@router.get("/summary/{filename}")
async def get_file_summary(filename: str):
    file_path = os.path.join("temp_storage", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found in storage.")
    try:
        df = DataService.load_data_to_df(file_path)
        summary = DataService.get_summary_stats(df) if hasattr(DataService, "get_summary_stats") else DataService.parse_schema(df)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/schema/{filename}")
async def get_file_schema(filename: str):
    file_path = os.path.join("temp_storage", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found in storage.")
    try:
        df = DataService.load_data_to_df(file_path)
        schema_profile = DataService.parse_schema(df)
        return {"filename": filename, "schema": schema_profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))