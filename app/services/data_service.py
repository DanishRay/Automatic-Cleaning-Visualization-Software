import os
import zipfile
from typing import Any, Dict, Generator, Optional
import duckdb
import pandas as pd


class DataService:

    def __init__(self, temp_file_path: str = "temp_active_data.parquet"):
        self.temp_file_path = temp_file_path
        self._df: Optional[pd.DataFrame] = None

    def get_df(self) -> pd.DataFrame:
        if self._df is not None:
            return self._df
        if os.path.exists(self.temp_file_path):
            self._df = pd.read_parquet(self.temp_file_path)
            return self._df
        raise FileNotFoundError("No active dataset session found.")

    def set_df(self, df: pd.DataFrame) -> None:
        self._df = df.copy()
        self._df.to_parquet(self.temp_file_path, index=False)

    def clear(self) -> None:
        self._df = None
        if os.path.exists(self.temp_file_path):
            os.remove(self.temp_file_path)

    @staticmethod
    def save_session_data(session_id: str, df: pd.DataFrame) -> None:
        os.makedirs("temp_storage", exist_ok=True)
        file_path = os.path.join("temp_storage", session_id)
        if not file_path.endswith((".csv", ".parquet", ".xlsx", ".xls")):
            file_path = f"{file_path}.csv"

        if file_path.endswith(".parquet"):
            df.to_parquet(file_path, index=False)
        elif file_path.endswith((".xlsx", ".xls")):
            df.to_excel(file_path, index=False)
        else:
            df.to_csv(file_path, index=False)

    @staticmethod
    def load_data_to_df(
        file_path: str, chunksize: int = None
    ) -> pd.DataFrame | Generator[pd.DataFrame, None, None]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv":
            return (
                pd.read_csv(file_path, chunksize=chunksize)
                if chunksize
                else pd.read_csv(file_path)
            )
        elif ext == ".xlsx":
            try:
                return pd.read_excel(file_path, engine="openpyxl")
            except (zipfile.BadZipFile, ValueError, Exception):
                return (
                    pd.read_csv(file_path, chunksize=chunksize)
                    if chunksize
                    else pd.read_csv(file_path)
                )
        elif ext == ".xls":
            try:
                return pd.read_excel(file_path, engine="xlrd")
            except Exception:
                try:
                    return (
                        pd.read_csv(file_path, chunksize=chunksize)
                        if chunksize
                        else pd.read_csv(file_path)
                    )
                except Exception:
                    tables = pd.read_html(file_path)
                    if tables:
                        return tables[0]
                    raise ValueError(f"Unable to parse legacy XLS file: {file_path}")
        elif ext == ".json":
            return pd.read_json(file_path)
        elif ext == ".parquet":
            return pd.read_parquet(file_path)
        else:
            try:
                return (
                    pd.read_csv(file_path, chunksize=chunksize)
                    if chunksize
                    else pd.read_csv(file_path)
                )
            except Exception:
                raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def parse_schema(df: pd.DataFrame) -> Dict[str, Any]:
        row_count, col_count = df.shape
        columns_info = {}

        for col in df.columns:
            s = df[col]
            missing_count = int(s.isnull().sum())
            missing_ratio = (
                float(missing_count / row_count) if row_count > 0 else 0.0
            )

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

            is_pk_candidate = bool(
                s.nunique() == row_count
                and missing_count == 0
                and row_count > 0
            )

            columns_info[col] = {
                "data_type": detected_type,
                "original_dtype": str(s.dtype),
                "missing_values": missing_count,
                "missing_ratio": round(missing_ratio, 4),
                "is_primary_key_candidate": is_pk_candidate,
                "unique_values": int(s.nunique()),
            }

        return {
            "row_count": row_count,
            "column_count": col_count,
            "columns": columns_info,
        }

    @staticmethod
    def execute_duckdb_query(df: pd.DataFrame, query: str) -> pd.DataFrame:
        conn = duckdb.connect(database=":memory:")
        conn.register("data_title", df)
        result_df = conn.execute(query).df()
        conn.close()
        return result_df


data_service_instance = DataService()