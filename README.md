# Project Overview

DataAIEngine is a FastAPI-powered application designed for local data processing, cleaning, visualization, and AI-driven workflows utilizing DuckDB, Pandas, LangChain, and Ollama. The architecture consists of a modular backend structure and a Tailwind CSS-styled frontend packaged via PyInstaller.

## What to Prepare

* **Python Environment**: Verify dependencies listed in `requirements.txt` are fully installed.
* **Local AI Runtime**: Ensure Ollama is active and running locally with the **llama3** model to support `ai_router.py` and `ai_service.py`.
* **Frontend Assets**: Confirm that Chart.js scripts and Tailwind CSS output files are correctly structured inside `app/static/`.

## To-Do Checklist

| Category | Action Item | Target / Details |
| :--- | :--- | :--- |
| **Backend Validation** | Test all API endpoints | Verify routers for AI, cleaning, data, reporting, relational, and visualization |
| **Frontend Verification** | Check static HTML templates | Ensure `index.html`, `cleaning.html`, and `visualize.html` load styles correctly |
| **Build & Compile** | Execute PyInstaller build | Build the standalone executable using `DataAIEngine.spec` |
| **Distribution Test** | Run the bundled application | Test execution from `dist/DataAIEngine/DataAIEngine.exe` |

## Reminders & Notes

* Clean out stale build directories (`build/`, `dist/`, and `__pycache__`) before running fresh PyInstaller packaging cycles.
* Ensure all database drivers and binary dependencies (such as DuckDB and PyArrow modules) are correctly bundled within the PyInstaller internal spec.

## Setup Instructions for Other Users

1. **Create and Activate the Python Virtual Environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate

2. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt

3. **Install Node.js Dependencies (for Tailwind/frontend assets):**
   ```bash
   npm install

4. **Initialize Local AI Services: Ensure Ollama is installed and active on their machine so the application can communicate with local AI routers**

5. **Run the Application:**
    ```bash
    python run.py



# Guide: Compiling DataAIEngine into a Standalone Executable

This guide explains how to package **DataAIEngine** into a standalone executable (.exe) using **PyInstaller** and the provided `DataAIEngine.spec` configuration file.

---

## Prerequisites

Before compiling, ensure that:
1. Your Python virtual environment (`venv`) is activated.
2. All project dependencies (including `pyinstaller`) are installed.
3. Your frontend assets (Tailwind CSS and Chart.js scripts) are properly built and located in `app/static/`.

---

## Step-by-Step Compilation Instructions

### Step 1: Clean Stale Build Artifacts
To prevent caching issues or old files from being bundled, clean out any existing build or distribution folders.

**On Windows (PowerShell / Command Prompt):**
```bash
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
```

---

### Step 2: Build Tailwind CSS (If Frontend Changes Were Made)
If you modified any HTML templates or Tailwind classes, rebuild your CSS output file:
```bash
npm run build
```

---

### Step 3: Run PyInstaller Using the Spec File
Since your project includes a pre-configured `DataAIEngine.spec` file (which properly maps binary modules like DuckDB, Pandas, and static directories), you do not need long command-line flags. Just run:

```bash
pyinstaller DataAIEngine.spec
```

---

### Step 4: Locate Your Executable
Once the compilation process completes successfully:
1. PyInstaller will generate a new `build/` folder and `dist/` folder.
2. Navigate to your output directory:
   ```text
   dist/DataAIEngine/DataAIEngine.exe
   ```
3. You can now test running the standalone executable directly from that folder.

---

## Troubleshooting Tips

* **Missing Static Files or Database Drivers:** If the application crashes on startup complaining about missing templates or database drivers, check your `DataAIEngine.spec` file to ensure `datas` and `hiddenimports` include `app/static` and backend modules correctly.
* **Ollama Dependency:** Remember that the standalone executable still requires **Ollama** and the **llama3** model to be installed and running on the target machine for AI features to function properly.