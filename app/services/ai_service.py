from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
import pandas as pd
import numpy as np

class AIService:
    def __init__(self, model_name: str = "llama3"):
        self.llm = OllamaLLM(model=model_name)
        self.output_parser = StrOutputParser()

    def summarize_cleaning_impact(self, df: pd.DataFrame, ai_actions: dict) -> str:
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
            template=template
        )
        chain = prompt | self.llm | self.output_parser
        try:
            response = chain.invoke({
                "rows": total_rows,
                "columns": total_cols,
                "missing_count": missing_count,
                "actions": str(ai_actions)
            })
            return response
        except Exception as e:
            return f"Cleaning will process {total_rows} rows and handle missing values to prepare the dataset for analysis. (AI Model offline: {str(e)})"

    @staticmethod
    def suggest_imputation(df: pd.DataFrame) -> dict:
        suggestions = {}
        for col in df.columns:
            if df[col].isnull().sum() > 0:
                if pd.api.types.is_numeric_dtype(df[col]):
                    suggestions[col] = "median" if abs(df[col].skew()) > 1 else "mean"
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