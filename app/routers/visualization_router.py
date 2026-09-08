from fastapi import APIRouter, HTTPException
import pandas as pd
import os
from app.services.visualization_service import VisualizationService

router = APIRouter(prefix="/api/v1/visualize", tags=["Visualization Studio"])
TEMP_DIR = "temp_storage"

@router.get("/recommend/{filename}")
def recommend_visualizations(filename: str):
    try:
        return VisualizationService.analyze_and_recommend(filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/custom-data/{filename}")
async def get_custom_chart_data(filename: str, xaxis: str, yaxis: str):
    file_path = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        ext = os.path.splitext(filename)[1].lower()
        if ext == '.csv':
            df = pd.read_csv(file_path)
        elif ext == '.xlsx':
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
            except Exception:
                df = pd.read_csv(file_path)
        elif ext == '.xls':
            try:
                df = pd.read_excel(file_path, engine='xlrd')
            except Exception:
                df = pd.read_csv(file_path)
        else:
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
            except Exception:
                df = pd.read_csv(file_path)
            
        if xaxis not in df.columns or yaxis not in df.columns:
            raise HTTPException(status_code=400, detail="Selected columns do not exist in dataset.")
            
        grouped = df.groupby(xaxis)[yaxis].mean().reset_index().head(25)
        
        return {
            "labels": grouped[xaxis].astype(str).tolist(),
            "values": grouped[yaxis].tolist()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))