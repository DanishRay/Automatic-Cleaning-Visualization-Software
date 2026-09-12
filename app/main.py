from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import shutil
import sys
from app.routers import data_router, ai_router, cleaning_router, visualization_router, transformation_router

app = FastAPI(title="Local-First Data AI Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = "temp_storage"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.get("/health")
async def health_check():
    return {"status": "active", "architecture": "FastAPI + Uvicorn"}

@app.post("/api/v1/cleanup-temp")
async def cleanup_temp():
    try:
        if os.path.exists(TEMP_DIR):
            for filename in os.listdir(TEMP_DIR):
                file_path = os.path.join(TEMP_DIR, filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
        return {"status": "success", "message": "temp_storage cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear temp storage: {str(e)}")

@app.post("/api/v1/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")
    file_path = os.path.join(TEMP_DIR, file.filename)
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
    return {"filename": file.filename, "saved_path": file_path, "size_bytes": len(contents)}

app.include_router(data_router.router)
app.include_router(ai_router.router)
app.include_router(cleaning_router.router)
app.include_router(visualization_router.router)
app.include_router(transformation_router.router)

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/app/static", StaticFiles(directory=STATIC_DIR), name="app_static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static_assets")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")