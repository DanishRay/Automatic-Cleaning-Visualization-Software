import os
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.visualization_service import (
    VisualizationService,
    generate_chart_data,
)

router = APIRouter(prefix="/api/v1/visualize", tags=["Visualization Studio"])
TEMP_DIR = Path("temp_storage")


class CustomChartRequest(BaseModel):
    filename: str
    chart_type: str
    x_col: Optional[str] = None
    y_col: Optional[str] = None
    metric: Optional[str] = "COUNT"
    bins: Optional[int] = 10


class SuggestionRequest(BaseModel):
    filename: str
    numeric_columns: List[str] = []
    categorical_columns: List[str] = []
    datetime_columns: List[str] = []


def _load_dataframe(file_path: Path) -> pd.DataFrame:
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    ext = file_path.suffix.lower()
    try:
        if ext == ".csv":
            return pd.read_csv(file_path)
        elif ext == ".xlsx":
            try:
                return pd.read_excel(file_path, engine="openpyxl")
            except (zipfile.BadZipFile, ValueError, Exception):
                return pd.read_csv(file_path)
        elif ext == ".xls":
            try:
                return pd.read_excel(file_path, engine="xlrd")
            except Exception:
                return pd.read_csv(file_path)
        elif ext == ".json":
            return pd.read_json(file_path)
        elif ext == ".parquet":
            return pd.read_parquet(file_path)
        else:
            return pd.read_csv(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read file: {str(e)}"
        )


@router.get("/recommend/{filename}")
def recommend_visualizations(filename: str):
    try:
        return VisualizationService.analyze_and_recommend(filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/custom-data/{filename}")
async def get_custom_chart_data(filename: str, xaxis: str, yaxis: str):
    file_path = TEMP_DIR / filename
    df = _load_dataframe(file_path)

    if xaxis not in df.columns or yaxis not in df.columns:
        raise HTTPException(
            status_code=400, detail="Selected columns do not exist in dataset."
        )

    try:
        grouped = df.groupby(xaxis)[yaxis].mean().reset_index().head(25)
        return {
            "labels": grouped[xaxis].astype(str).tolist(),
            "values": grouped[yaxis].tolist(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/render")
async def render_chart_data(payload: CustomChartRequest):
    file_path = TEMP_DIR / payload.filename
    df = _load_dataframe(file_path)

    try:
        chart_data = generate_chart_data(
            df=df,
            chart_type=payload.chart_type,
            x_col=payload.x_col,
            y_col=payload.y_col,
            metric=payload.metric or "COUNT",
            bins=payload.bins or 10,
        )
        return chart_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggest")
async def suggest_chart_parameters(payload: SuggestionRequest):
    file_path = TEMP_DIR / payload.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    suggestions = []

    if payload.datetime_columns and payload.numeric_columns:
        suggestions.append(
            {
                "chart_type": "line",
                "x_col": payload.datetime_columns[0],
                "y_col": payload.numeric_columns[0],
                "metric": "AVG",
                "title": f"Trend of {payload.numeric_columns[0]} over Time",
            }
        )

    if payload.categorical_columns and payload.numeric_columns:
        suggestions.append(
            {
                "chart_type": "bar",
                "x_col": payload.categorical_columns[0],
                "y_col": payload.numeric_columns[0],
                "metric": "SUM",
                "title": f"Total {payload.numeric_columns[0]} by {payload.categorical_columns[0]}",
            }
        )

    if len(payload.numeric_columns) >= 2:
        suggestions.append(
            {
                "chart_type": "scatter",
                "x_col": payload.numeric_columns[0],
                "y_col": payload.numeric_columns[1],
                "metric": "NONE",
                "title": f"{payload.numeric_columns[0]} vs {payload.numeric_columns[1]} Distribution",
            }
        )
    elif len(payload.numeric_columns) == 1:
        suggestions.append(
            {
                "chart_type": "histogram",
                "x_col": payload.numeric_columns[0],
                "y_col": None,
                "metric": "COUNT",
                "bins": 10,
                "title": f"Frequency Distribution of {payload.numeric_columns[0]}",
            }
        )

    if payload.categorical_columns:
        suggestions.append(
            {
                "chart_type": "pie",
                "x_col": payload.categorical_columns[0],
                "y_col": None,
                "metric": "COUNT",
                "title": f"Share of {payload.categorical_columns[0]}",
            }
        )

    return {
        "filename": payload.filename,
        "suggestions": suggestions,
    }