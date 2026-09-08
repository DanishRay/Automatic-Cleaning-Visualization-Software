import pandas as pd
import duckdb
import os
import zipfile
from typing import Generator, Dict, Any

class DataService:
    @staticmethod
    def load_data_to_df(file_path: str, chunksize: int = None) -> pd.DataFrame | Generator[pd.DataFrame, None, None]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.csv':
            return pd.read_csv(file_path, chunksize=chunksize) if chunksize else pd.read_csv(file_path)
        elif ext == '.xlsx':
            try:
                return pd.read_excel(file_path, engine='openpyxl')
            except (zipfile.BadZipFile, ValueError, Exception):
                return pd.read_csv(file_path, chunksize=chunksize) if chunksize else pd.read_csv(file_path)
        elif ext == '.xls':
            try:
                return pd.read_excel(file_path, engine='xlrd')
            except Exception:
                return pd.read_csv(file_path, chunksize=chunksize) if chunksize else pd.read_csv(file_path)
        elif ext == '.json':
            return pd.read_json(file_path)
        elif ext == '.parquet':
            return pd.read_parquet(file_path)
        else:
            try:
                return pd.read_csv(file_path, chunksize=chunksize) if chunksize else pd.read_csv(file_path)
            except Exception:
                raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def parse_schema(df: pd.DataFrame) -> Dict[str, Any]:
        row_count, col_count = df.shape
        columns_info = {}
        
        for col in df.columns:
            s = df[col]
            missing_count = int(s.isnull().sum())
            missing_ratio = float(missing_count / row_count) if row_count > 0 else 0.0
            
            if pd.api.types.is_integer_dtype(s):
                detected_type = "integer"
            elif pd.api.types.is_float_dtype(s):
                detected_type = "float"
            elif pd.api.types.is_bool_dtype(s):
                detected_type = "boolean"
            elif pd.api.types.is_datetime64_any_dtype(s):
                detected_type = "datetime"
            else:
                detected_type = "string"

            is_pk_candidate = bool(s.nunique() == row_count and missing_count == 0 and row_count > 0)

            columns_info[col] = {
                "data_type": detected_type,
                "original_dtype": str(s.dtype),
                "missing_values": missing_count,
                "missing_ratio": round(missing_ratio, 4),
                "is_primary_key_candidate": is_pk_candidate,
                "unique_values": int(s.nunique())
            }

        return {
            "row_count": row_count,
            "column_count": col_count,
            "columns": columns_info
        }

    @staticmethod
    def execute_duckdb_query(df: pd.DataFrame, query: str) -> pd.DataFrame:
        conn = duckdb.connect(database=':memory:')
        conn.register('data_title', df)
        result_df = conn.execute(query).df()
        conn.close()
        return result_df