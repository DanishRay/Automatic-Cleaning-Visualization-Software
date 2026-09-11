import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.ai_service import AIService
from app.services.data_service import DataService

router = APIRouter(prefix="/api/v1/ai", tags=["AI Processing"])
ai_service = AIService(model_name="phi3")
TEMP_DIR = Path("temp_storage")


class ChartRecommendRequest(BaseModel):
    filename: str
    numeric_columns: Optional[List[str]] = None
    categorical_columns: Optional[List[str]] = None
    datetime_columns: Optional[List[str]] = None


@router.get("/recommendations/{filename}")
async def get_ai_recommendations(filename: str):
    file_path = TEMP_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found in storage.")
    try:
        df = DataService.load_data_to_df(str(file_path))
        summary = DataService.get_summary_stats(df)
        recommendations = ai_service.generate_cleaning_suggestions(summary)
        return {"filename": filename, "ai_recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend-chart")
async def recommend_chart(payload: ChartRecommendRequest):
    file_path = TEMP_DIR / payload.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found in storage.")

    try:
        df = DataService.load_data_to_df(str(file_path))

        # Filter to requested columns if specific subsets were passed
        selected_cols = []
        if payload.numeric_columns:
            selected_cols.extend(payload.numeric_columns)
        if payload.categorical_columns:
            selected_cols.extend(payload.categorical_columns)
        if payload.datetime_columns:
            selected_cols.extend(payload.datetime_columns)

        if selected_cols:
            valid_cols = [c for c in selected_cols if c in df.columns]
            if valid_cols:
                df = df[valid_cols]

        recommendations = ai_service.suggest_chart_recommendations(df)
        return {
            "filename": payload.filename,
            "chart_recommendations": recommendations,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))