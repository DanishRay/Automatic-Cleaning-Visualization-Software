import pandas as pd
import numpy as np
from pathlib import Path
from app.services.data_service import DataService

TEMP_DIR = Path("temp_storage")

class CleaningService:
    @staticmethod
    def clean_baseline(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.drop_duplicates(inplace=True)
        for col in df.select_dtypes(include=['object', 'string']).columns:
            df[col] = df[col].astype(str).str.strip()
            try:
                parsed_dates = pd.to_datetime(df[col], errors='coerce', format='mixed')
                if parsed_dates.notnull().sum() / len(df) > 0.5:
                    df[col] = parsed_dates
                    continue
            except Exception:
                pass
        return df

    @staticmethod
    def detect_outliers_iqr(df: pd.DataFrame) -> dict:
        outliers = {}
        for col in df.select_dtypes(include=[np.number]).columns:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            outliers[col] = int(((df[col] < lower) | (df[col] > upper)).sum())
        return outliers

    @staticmethod
    def detect_outliers_zscore(df: pd.DataFrame, threshold: float = 3.0) -> dict:
        outliers = {}
        for col in df.select_dtypes(include=[np.number]).columns:
            s = df[col].dropna()
            if len(s) > 1 and s.std() > 0:
                z = np.abs((s - s.mean()) / s.std())
                outliers[col] = int((z > threshold).sum())
            else:
                outliers[col] = 0
        return outliers

    @staticmethod
    def apply_actions_and_save(filename: str, actions: dict, save_filename: str) -> str:
        file_path = TEMP_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError("File not found")
        
        df = DataService.load_data_to_df(str(file_path))
        df = CleaningService.clean_baseline(df)

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

        out_path = TEMP_DIR / save_filename
        if save_filename.endswith('.parquet'):
            df.to_parquet(out_path)
        elif save_filename.endswith(('.xlsx', '.xls')):
            df.to_excel(out_path, index=False)
        else:
            df.to_csv(out_path, index=False)
        return str(out_path)