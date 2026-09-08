from fastapi import APIRouter, HTTPException
from app.services.data_service import DataService
from app.services.ai_service import AIService
import os

router = APIRouter(prefix="/api/v1/ai", tags=["AI Processing"])
ai_service = AIService(model_name="phi3")

@router.get("/recommendations/{filename}")
async def get_ai_recommendations(filename: str):
    file_path = os.path.join("temp_storage", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found in storage.")
    try:
        df = DataService.load_data_to_df(file_path)
        summary = DataService.get_summary_stats(df)
        recommendations = ai_service.generate_cleaning_suggestions(summary)
        return {"filename": filename, "ai_recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))