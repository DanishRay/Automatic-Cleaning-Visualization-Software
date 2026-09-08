import os
import zipfile
import pandas as pd
from pathlib import Path

TEMP_DIR = Path("temp_storage")

class VisualizationService:
    @staticmethod
    def analyze_and_recommend(filename: str) -> dict:
        file_path = TEMP_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError(f"File {filename} not found in storage.")
        
        ext = os.path.splitext(filename)[1].lower()
        try:
            if ext == '.csv':
                df = pd.read_csv(file_path)
            elif ext == '.xlsx':
                try:
                    df = pd.read_excel(file_path, engine='openpyxl')
                except (zipfile.BadZipFile, ValueError, Exception):
                    df = pd.read_csv(file_path)
            elif ext == '.xls':
                try:
                    df = pd.read_excel(file_path, engine='xlrd')
                except Exception:
                    df = pd.read_csv(file_path)
            elif ext == '.json':
                df = pd.read_json(file_path)
            elif ext == '.parquet':
                df = pd.read_parquet(file_path)
            else:
                df = pd.read_csv(file_path)
        except Exception:
            df = pd.read_csv(file_path)

        recommendations = []
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
        
        datetime_cols = []
        for col in df.columns:
            if col not in numeric_cols:
                if any(keyword in col.lower() for keyword in ['date', 'time', 'year', 'month', 'day']):
                    try:
                        pd.to_datetime(df[col], errors='raise', format='mixed')
                        datetime_cols.append(col)
                    except Exception:
                        pass

        if datetime_cols and numeric_cols:
            x_col = datetime_cols[0]
            y_col = numeric_cols[0]
            ts_df = df.dropna(subset=[x_col, y_col]).groupby(x_col)[y_col].mean().reset_index().head(20)
            
            recommendations.append({
                "chart_type": "line",
                "title": f"Time-Series Trend: {y_col} over {x_col}",
                "x_axis": x_col,
                "y_axis": y_col,
                "labels": ts_df[x_col].astype(str).tolist(),
                "values": ts_df[y_col].tolist(),
                "ai_rationale": f"Detected temporal column '{x_col}' and numeric metric '{y_col}', ideal for tracking trends over time."
            })

        for cat_col in categorical_cols[:3]:
            if df[cat_col].nunique() <= 50 and numeric_cols:
                y_col = numeric_cols[0]
                cat_df = df.groupby(cat_col)[y_col].mean().reset_index().head(15)
                
                recommendations.append({
                    "chart_type": "bar",
                    "title": f"Categorical Distribution: {y_col} by {cat_col}",
                    "x_axis": cat_col,
                    "y_axis": y_col,
                    "labels": cat_df[cat_col].astype(str).tolist(),
                    "values": cat_df[y_col].tolist(),
                    "ai_rationale": f"Categorical column '{cat_col}' has low cardinality ({df[cat_col].nunique()} unique values), well-suited for group comparisons."
                })
                break

        if len(numeric_cols) >= 2:
            corr_subset = df[numeric_cols[:5]].corr()
            second_col = corr_subset.columns[1] if len(corr_subset.columns) > 1 else corr_subset.columns[0]
            corr_series = corr_subset[second_col].dropna()

            recommendations.append({
                "chart_type": "bar",
                "title": f"Numerical Feature Correlation: {second_col} vs others",
                "x_axis": corr_series.index.tolist(),
                "y_axis": second_col,
                "labels": corr_series.index.astype(str).tolist(),
                "values": corr_series.values.tolist(),
                "ai_rationale": f"Computed real correlation coefficients against '{second_col}' across numeric features to highlight linear relationships."
            })

        return {
            "filename": filename,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "datetime_columns": datetime_cols,
            "recommendations": recommendations
        }