import pandas as pd
from pathlib import Path
import subprocess
import tempfile
import os
from app.services.data_service import DataService

TEMP_DIR = Path("temp_storage")

class TransformationService:
    @staticmethod
    def apply_transformations(filename: str, operations: list = None, r_script: str = None) -> pd.DataFrame:
        file_path = TEMP_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError("File not found in storage.")
        
        df = DataService.load_data_to_df(str(file_path))

        if r_script and r_script.strip():
            with tempfile.TemporaryDirectory() as temp_dir:
                in_csv = os.path.abspath(os.path.join(temp_dir, "input.csv")).replace("\\", "/")
                out_csv = os.path.abspath(os.path.join(temp_dir, "output.csv")).replace("\\", "/")
                df.to_csv(in_csv, index=False)
                
                r_code = f"""
                df <- read.csv("{in_csv}", check.names = FALSE)
                {r_script}
                write.csv(df, "{out_csv}", row.names=FALSE)
                """
                script_path = os.path.join(temp_dir, "script.R")
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(r_code)
                
                result = subprocess.run(["Rscript", script_path], capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError(f"R execution error: {result.stderr.strip()}")
                
                if os.path.exists(out_csv):
                    df = pd.read_csv(out_csv)
                else:
                    raise RuntimeError("R script failed to produce output dataset.")
            return df

        operations = operations or []
        for op in operations:
            op_type = op.get("type")
            params = op.get("params", {})

            if op_type == "filter":
                col = params.get("column")
                condition = params.get("condition")
                val = params.get("value")
                if col in df.columns:
                    if condition == "==":
                        df = df[df[col] == val]
                    elif condition == "!=":
                        df = df[df[col] != val]
                    elif condition == ">":
                        df = df[df[col] > float(val)]
                    elif condition == "<":
                        df = df[df[col] < float(val)]
                    elif condition == "contains":
                        df = df[df[col].astype(str).str.contains(str(val), na=False)]

            elif op_type == "select_columns":
                columns = params.get("columns", [])
                existing_cols = [c for c in columns if c in df.columns]
                if existing_cols:
                    df = df[existing_cols]

            elif op_type == "rename_column":
                old_name = params.get("old_name")
                new_name = params.get("new_name")
                if old_name in df.columns and new_name:
                    df = df.rename(columns={old_name: new_name})

            elif op_type == "cast_type":
                col = params.get("column")
                target_type = params.get("target_type")
                if col in df.columns:
                    try:
                        if target_type == "int":
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                        elif target_type == "float":
                            df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
                        elif target_type == "str":
                            df[col] = df[col].astype(str)
                        elif target_type == "datetime":
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                    except Exception:
                        pass

        return df

    @staticmethod
    def save_transformed_data(filename: str, operations: list = None, save_filename: str = "transformed_output.csv", r_script: str = None) -> str:
        df = TransformationService.apply_transformations(filename, operations=operations, r_script=r_script)
        out_path = TEMP_DIR / save_filename
        if save_filename.endswith('.parquet'):
            df.to_parquet(out_path)
        elif save_filename.endswith(('.xlsx', '.xls')):
            df.to_excel(out_path, index=False)
        else:
            df.to_csv(out_path, index=False)
        return str(out_path)