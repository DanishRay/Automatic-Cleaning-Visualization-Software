import os
import pandas as pd
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.services.data_service import DataService
from app.services.cleaning_service import CleaningService
from app.services.ai_service import AIService

router = APIRouter(prefix="/api/v1/cleaning", tags=["Data Cleaning"])
ai_service = AIService()

class SaveCleanRequest(BaseModel):
    actions: dict
    save_filename: str

@router.get("/preview/{filename}")
async def preview_cleaning(filename: str):
    file_path = os.path.join("temp_storage", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found in storage.")
    try:
        df = DataService.load_data_to_df(file_path)
        cleaned_df = CleaningService.clean_baseline(df)
        return {
            "filename": filename,
            "original_rows": len(df),
            "cleaned_rows": len(cleaned_df),
            "duplicates_dropped": int(len(df) - len(cleaned_df)),
            "outliers_iqr": CleaningService.detect_outliers_iqr(cleaned_df),
            "outliers_zscore": CleaningService.detect_outliers_zscore(cleaned_df),
            "ai_imputation_suggestions": AIService.suggest_imputation(cleaned_df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/grid/{filename}")
async def get_cleaning_grid(filename: str, limit: int = 100):
    file_path = os.path.join("temp_storage", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found in storage.")
    try:
        df = DataService.load_data_to_df(file_path)
        cleaned_df = CleaningService.clean_baseline(df)
        ai_actions = AIService.suggest_imputation(cleaned_df)
        cleaning_summary = ai_service.summarize_cleaning_impact(cleaned_df, ai_actions)

        return {
            "columns": cleaned_df.columns.tolist(),
            "data": cleaned_df.head(limit).fillna("").to_dict(orient="records"),
            "ai_actions": ai_actions,
            "cleaning_summary": cleaning_summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/apply-actions/{filename}")
async def apply_cleaning_actions(filename: str, payload: dict = Body(...), limit: int = 100):
    file_path = os.path.join("temp_storage", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found in storage.")
    try:
        df = DataService.load_data_to_df(file_path)
        df = CleaningService.clean_baseline(df)
        
        actions = payload.get("actions", {})
        for col, strategy in actions.items():
            if col in df.columns:
                if strategy == "mean" and pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].fillna(df[col].mean())
                elif strategy == "median" and pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = df[col].fillna(df[col].median())
                elif strategy == "mode":
                    mode_val = df[col].mode()
                    if not mode_val.empty:
                        df[col] = df[col].fillna(mode_val[0])
                elif strategy == "drop":
                    df = df.dropna(subset=[col])

        cleaned_filename = f"cleaned_{filename}"
        save_path = os.path.join("temp_storage", cleaned_filename)
        if filename.endswith('.parquet'):
            df.to_parquet(save_path)
        else:
            df.to_csv(save_path, index=False)
        
        return {
            "status": "success", 
            "cleaned_filename": cleaned_filename, 
            "rows": len(df),
            "columns": df.columns.tolist(),
            "data": df.head(limit).fillna("").to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save-cleaned/{filename}")
async def save_cleaned_data(filename: str, payload: SaveCleanRequest):
    try:
        path = CleaningService.apply_actions_and_save(
            filename, payload.actions, payload.save_filename
        )
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Processed file not found.")
        return FileResponse(path, filename=payload.save_filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))