import os
import logging
import subprocess
import tempfile
import traceback
from pathlib import Path
from fastapi import HTTPException
import pandas as pd
from app.services.data_service import data_service_instance, DataService

TEMP_DIR = Path("temp_storage")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TransformationService:
    @staticmethod
    def _resolve_dataframe(filename: str = None) -> pd.DataFrame:
        df = None

        if filename:
            file_path = TEMP_DIR / filename
            if file_path.exists():
                df = DataService.load_data_to_df(str(file_path))
            else:
                df = data_service_instance.get_df()
        else:
            df = data_service_instance.get_df()

        if df is None:
            logger.warning("Requested dataset resolved to None. Initializing empty DataFrame.")
            df = pd.DataFrame()

        if df.empty:
            logger.warning("Warning: DataFrame is empty at execution time!")

        return df

    @staticmethod
    def apply_transformations(
        filename: str = None, operations: list = None, r_script: str = None
    ) -> pd.DataFrame:
        df = TransformationService._resolve_dataframe(filename)

        if df.empty:
            logger.warning("Executing transformations on an empty DataFrame.")

        if r_script and r_script.strip():
            with tempfile.TemporaryDirectory() as temp_dir:
                in_csv = os.path.abspath(os.path.join(temp_dir, "input.csv")).replace("\\", "/")
                out_csv = os.path.abspath(os.path.join(temp_dir, "output.csv")).replace("\\", "/")
                df.to_csv(in_csv, index=False)

                r_code = f"""
                tryCatch({{
                    df <- read.csv("{in_csv}", check.names = FALSE)
                    {r_script}
                    write.csv(df, "{out_csv}", row.names=FALSE)
                }}, error = function(e) {{
                    cat("R_EXECUTION_ERROR:", conditionMessage(e), file=stderr())
                    quit(status=1)
                }})
                """
                script_path = os.path.join(temp_dir, "script.R")
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(r_code)

                result = subprocess.run(
                    ["Rscript", script_path], capture_output=True, text=True
                )
                
                if result.returncode != 0 or "R_EXECUTION_ERROR:" in result.stderr:
                    error_msg = result.stderr.replace("R_EXECUTION_ERROR:", "").strip()
                    if not error_msg and result.stdout:
                        error_msg = result.stdout.strip()
                    raise HTTPException(status_code=400, detail=f"R Script Error: {error_msg}")

                if os.path.exists(out_csv):
                    df = pd.read_csv(out_csv)
                else:
                    raise HTTPException(status_code=400, detail="R Script Error: R script failed to produce output dataset.")

            data_service_instance.set_df(df)
            return df

        operations = operations or []
        for op in operations:
            if df.empty:
                logger.warning("Skipping operation stack: DataFrame is empty.")
                break

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
                        try:
                            df = df[df[col] > float(val)]
                        except ValueError:
                            pass
                    elif condition == "<":
                        try:
                            df = df[df[col] < float(val)]
                        except ValueError:
                            pass
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
                            df[col] = (
                                pd.to_numeric(df[col], errors="coerce")
                                .fillna(0)
                                .astype(int)
                            )
                        elif target_type == "float":
                            df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
                        elif target_type == "str":
                            df[col] = df[col].astype(str)
                        elif target_type == "datetime":
                            df[col] = pd.to_datetime(df[col], errors="coerce")
                    except Exception as err:
                        logger.warning(f"Failed to cast column '{col}' to {target_type}: {err}")

        data_service_instance.set_df(df)
        return df

    @staticmethod
    def save_transformed_data(
        filename: str = None,
        operations: list = None,
        save_filename: str = "transformed_output.csv",
        r_script: str = None,
    ) -> str:
        try:
            df = TransformationService.apply_transformations(
                filename, operations=operations, r_script=r_script
            )
            
            TEMP_DIR.mkdir(parents=True, exist_ok=True)
            if not os.access(TEMP_DIR, os.W_OK):
                raise PermissionError(f"Write permissions denied for directory: {TEMP_DIR}")

            out_path = TEMP_DIR / save_filename

            if save_filename.endswith(".parquet"):
                df.to_parquet(out_path)
            elif save_filename.endswith((".xlsx", ".xls")):
                df.to_excel(out_path, index=False)
            else:
                df.to_csv(out_path, index=False)

            if hasattr(DataService, "register_dataset"):
                DataService.register_dataset(save_filename, str(out_path))

            return str(out_path)
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Error during save execution:\n{error_trace}")
            print(f"SERVICE_SAVE_EXCEPTION:\n{error_trace}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=500, detail=f"Save execution failed: {str(e)}")