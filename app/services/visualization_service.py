import math
import os
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

TEMP_DIR = Path("temp_storage")


def generate_chart_data(
    df: pd.DataFrame,
    chart_type: str,
    x_col: Optional[str] = None,
    y_col: Optional[str] = None,
    metric: str = "COUNT",
    bins: int = 10,
) -> Dict[str, Any]:
    if df.empty:
        return {"labels": [], "datasets": []}

    chart_type = chart_type.lower()

    if chart_type == "histogram":
        return _build_histogram(df, x_col, bins)
    elif chart_type == "scatter":
        return _build_scatter(df, x_col, y_col)

    if not x_col or x_col not in df.columns:
        raise ValueError(f"Column '{x_col}' does not exist in dataset.")

    cleaned_df = df.dropna(subset=[x_col]).copy()

    if metric.upper() == "COUNT" or not y_col or y_col not in df.columns:
        grouped = cleaned_df.groupby(x_col).size().reset_index(name="value")
        dataset_label = f"Count of {x_col}"
    else:
        cleaned_df[y_col] = pd.to_numeric(cleaned_df[y_col], errors="coerce")
        cleaned_df = cleaned_df.dropna(subset=[y_col])

        metric_upper = metric.upper()
        if metric_upper == "SUM":
            grouped = (
                cleaned_df.groupby(x_col)[y_col]
                .sum()
                .reset_index(name="value")
            )
            dataset_label = f"Sum of {y_col} by {x_col}"
        elif metric_upper == "AVG":
            grouped = (
                cleaned_df.groupby(x_col)[y_col]
                .mean()
                .reset_index(name="value")
            )
            dataset_label = f"Average of {y_col} by {x_col}"
        elif metric_upper == "MIN":
            grouped = (
                cleaned_df.groupby(x_col)[y_col]
                .min()
                .reset_index(name="value")
            )
            dataset_label = f"Min of {y_col} by {x_col}"
        elif metric_upper == "MAX":
            grouped = (
                cleaned_df.groupby(x_col)[y_col]
                .max()
                .reset_index(name="value")
            )
            dataset_label = f"Max of {y_col} by {x_col}"
        else:
            raise ValueError(f"Unsupported metric: '{metric}'")

    labels = [str(val) for val in grouped[x_col].tolist()]
    values = [
        float(val) if math.isfinite(val) else 0.0
        for val in grouped["value"].tolist()
    ]

    return {
        "labels": labels,
        "datasets": [
            {
                "label": dataset_label,
                "data": values,
            }
        ],
    }


def _build_histogram(
    df: pd.DataFrame, x_col: Optional[str], bins: int
) -> Dict[str, Any]:
    if not x_col or x_col not in df.columns:
        raise ValueError("Histogram requires a valid target column.")

    series = pd.to_numeric(df[x_col], errors="coerce").dropna()
    if series.empty:
        return {"labels": [], "datasets": []}

    counts, bin_edges = np.histogram(series, bins=bins)
    labels = [
        f"{bin_edges[i]:.2f} - {bin_edges[i+1]:.2f}"
        for i in range(len(counts))
    ]

    return {
        "labels": labels,
        "datasets": [
            {
                "label": f"Frequency ({x_col})",
                "data": [int(c) for c in counts],
            }
        ],
    }


def _build_scatter(
    df: pd.DataFrame, x_col: Optional[str], y_col: Optional[str]
) -> Dict[str, Any]:
    if not x_col or not y_col:
        raise ValueError("Scatter plots require both X and Y columns.")

    if x_col not in df.columns or y_col not in df.columns:
        raise ValueError("Specified X or Y column does not exist in dataset.")

    cleaned = df[[x_col, y_col]].copy()
    cleaned[x_col] = pd.to_numeric(cleaned[x_col], errors="coerce")
    cleaned[y_col] = pd.to_numeric(cleaned[y_col], errors="coerce")
    cleaned = cleaned.dropna()

    points = []
    for _, row in cleaned.iterrows():
        x_val = float(row[x_col])
        y_val = float(row[y_col])
        if math.isfinite(x_val) and math.isfinite(y_val):
            points.append({"x": x_val, "y": y_val})

    return {
        "labels": [],
        "datasets": [
            {
                "label": f"{x_col} vs {y_col}",
                "data": points,
            }
        ],
    }


class VisualizationService:
    @staticmethod
    def analyze_and_recommend(filename: str) -> dict:
        file_path = TEMP_DIR / filename
        if not file_path.exists():
            raise FileNotFoundError(f"File {filename} not found in storage.")

        ext = os.path.splitext(filename)[1].lower()
        try:
            if ext == ".csv":
                df = pd.read_csv(file_path)
            elif ext == ".xlsx":
                try:
                    df = pd.read_excel(file_path, engine="openpyxl")
                except (zipfile.BadZipFile, ValueError, Exception):
                    df = pd.read_csv(file_path)
            elif ext == ".xls":
                try:
                    df = pd.read_excel(file_path, engine="xlrd")
                except Exception:
                    df = pd.read_csv(file_path)
            elif ext == ".json":
                df = pd.read_json(file_path)
            elif ext == ".parquet":
                df = pd.read_parquet(file_path)
            else:
                df = pd.read_csv(file_path)
        except Exception:
            df = pd.read_csv(file_path)

        recommendations = []
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        categorical_cols = df.select_dtypes(
            include=["object", "category", "bool"]
        ).columns.tolist()

        datetime_cols = []
        for col in df.columns:
            if col not in numeric_cols:
                if any(
                    keyword in col.lower()
                    for keyword in ["date", "time", "year", "month", "day"]
                ):
                    try:
                        pd.to_datetime(df[col], errors="raise", format="mixed")
                        datetime_cols.append(col)
                    except Exception:
                        pass

        if datetime_cols and numeric_cols:
            x_col = datetime_cols[0]
            y_col = numeric_cols[0]
            ts_df = (
                df.dropna(subset=[x_col, y_col])
                .groupby(x_col)[y_col]
                .mean()
                .reset_index()
                .head(20)
            )

            recommendations.append(
                {
                    "chart_type": "line",
                    "title": f"Time-Series Trend: {y_col} over {x_col}",
                    "x_axis": x_col,
                    "y_axis": y_col,
                    "labels": ts_df[x_col].astype(str).tolist(),
                    "values": ts_df[y_col].tolist(),
                    "ai_rationale": f"Detected temporal column '{x_col}' and numeric metric '{y_col}', ideal for tracking trends over time.",
                }
            )

        for cat_col in categorical_cols[:3]:
            if df[cat_col].nunique() <= 50 and numeric_cols:
                y_col = numeric_cols[0]
                cat_df = (
                    df.groupby(cat_col)[y_col]
                    .mean()
                    .reset_index()
                    .head(15)
                )

                recommendations.append(
                    {
                        "chart_type": "bar",
                        "title": f"Categorical Distribution: {y_col} by {cat_col}",
                        "x_axis": cat_col,
                        "y_axis": y_col,
                        "labels": cat_df[cat_col].astype(str).tolist(),
                        "values": cat_df[y_col].tolist(),
                        "ai_rationale": f"Categorical column '{cat_col}' has low cardinality ({df[cat_col].nunique()} unique values), well-suited for group comparisons.",
                    }
                )
                break

        if len(numeric_cols) >= 2:
            corr_subset = df[numeric_cols[:5]].corr()
            second_col = (
                corr_subset.columns[1]
                if len(corr_subset.columns) > 1
                else corr_subset.columns[0]
            )
            corr_series = corr_subset[second_col].dropna()

            recommendations.append(
                {
                    "chart_type": "bar",
                    "title": f"Numerical Feature Correlation: {second_col} vs others",
                    "x_axis": corr_series.index.tolist(),
                    "y_axis": second_col,
                    "labels": corr_series.index.astype(str).tolist(),
                    "values": corr_series.values.tolist(),
                    "ai_rationale": f"Computed real correlation coefficients against '{second_col}' across numeric features to highlight linear relationships.",
                }
            )

        return {
            "filename": filename,
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "datetime_columns": datetime_cols,
            "recommendations": recommendations,
        }