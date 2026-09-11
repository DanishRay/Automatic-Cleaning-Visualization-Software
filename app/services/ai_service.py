import json
import numpy as np
import pandas as pd
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM


class AIService:
    def __init__(self, model_name: str = "llama3"):
        self.llm = OllamaLLM(model=model_name)
        self.output_parser = StrOutputParser()

    def summarize_cleaning_impact(
        self, df: pd.DataFrame, ai_actions: dict
    ) -> str:
        missing_count = int(df.isnull().sum().sum())
        total_rows = len(df)
        total_cols = len(df.columns)

        template = """
        You are an expert data engineer. Analyze a dataset with {rows} rows and {columns} columns, containing a total of {missing_count} missing values.
        The automated data cleaning and imputation plan includes: {actions}.
        Write a concise, professional 3-4 sentence paragraph summarizing the expected impact of applying these cleaning steps on data integrity, distribution quality, and readiness for downstream tasks.
        """
        prompt = PromptTemplate(
            input_variables=["rows", "columns", "missing_count", "actions"],
            template=template,
        )
        chain = prompt | self.llm | self.output_parser
        try:
            response = chain.invoke(
                {
                    "rows": total_rows,
                    "columns": total_cols,
                    "missing_count": missing_count,
                    "actions": str(ai_actions),
                }
            )
            return response
        except Exception as e:
            return f"Cleaning will process {total_rows} rows and handle missing values to prepare the dataset for analysis. (AI Model offline: {str(e)})"

    def suggest_chart_recommendations(self, df: pd.DataFrame) -> dict:
        metadata = {
            "total_rows": len(df),
            "columns": {},
        }

        for col in df.columns:
            dtype_str = str(df[col].dtype)
            null_count = int(df[col].isnull().sum())
            nunique = int(df[col].nunique(dropna=True))

            col_meta = {
                "dtype": dtype_str,
                "null_count": null_count,
                "unique_values": nunique,
            }

            if pd.api.types.is_numeric_dtype(df[col]):
                valid_series = df[col].dropna()
                if not valid_series.empty:
                    col_meta["range"] = {
                        "min": float(valid_series.min()),
                        "max": float(valid_series.max()),
                        "mean": float(valid_series.mean()),
                    }

            metadata["columns"][col] = col_meta

        template = """
        You are an expert data visualization consultant. Analyze the following dataset schema metadata:
        {metadata}

        Recommend the top 3 best visualization charts based strictly on these rules:
        1. Recommend a 'scatter' plot when two continuous numeric columns are present to analyze correlation.
        2. Recommend a 'histogram' for single numerical continuous variables to display frequency distributions.
        3. Recommend a 'line' chart when temporal or date-based columns are paired with numeric metrics.
        4. Recommend a 'bar', 'pie', or 'doughnut' chart when low-cardinality categorical columns are paired with numeric metrics or used for counts.

        Return ONLY a valid, raw JSON object without markdown formatting or code blocks matching this structure:
        {{
            "recommendations": [
                {{
                    "chart_type": "scatter|histogram|line|bar|pie|doughnut",
                    "title": "Short Descriptive Title",
                    "x_col": "column_name",
                    "y_col": "column_name or null",
                    "metric": "COUNT|SUM|AVG|MIN|MAX|NONE",
                    "bins": 10,
                    "ai_rationale": "Clear explanation of why this chart fits the schema."
                }}
            ]
        }}
        """

        prompt = PromptTemplate(
            input_variables=["metadata"],
            template=template,
        )
        chain = prompt | self.llm | self.output_parser

        try:
            raw_response = chain.invoke({"metadata": json.dumps(metadata)})
            cleaned_response = raw_response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

            return json.loads(cleaned_response.strip())
        except Exception as e:
            return {
                "error": f"Failed to generate dynamic AI chart recommendations: {str(e)}",
                "recommendations": [],
            }

    @staticmethod
    def suggest_imputation(df: pd.DataFrame) -> dict:
        suggestions = {}
        for col in df.columns:
            if df[col].isnull().sum() > 0:
                if pd.api.types.is_numeric_dtype(df[col]):
                    suggestions[col] = (
                        "median" if abs(df[col].skew()) > 1 else "mean"
                    )
                else:
                    suggestions[col] = "mode"
        return suggestions

    @staticmethod
    def classify_anomalies(df: pd.DataFrame, col: str) -> list:
        if not pd.api.types.is_numeric_dtype(df[col]):
            return []
        s = df[col].dropna()
        if len(s) <= 1 or s.std() == 0:
            return []
        z_scores = np.abs((s - s.mean()) / s.std())
        return s[z_scores > 3].index.tolist()