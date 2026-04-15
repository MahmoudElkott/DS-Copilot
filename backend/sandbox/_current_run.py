
import pandas as pd
import json
import os

# Try to load the dataset
filepath = r"F:\source\DS-Copilot\backend\sandbox\IRIS.csv"

if filepath.endswith('.csv'):
    df = pd.read_csv(filepath)
elif filepath.endswith(('.xls', '.xlsx')):
    df = pd.read_excel(filepath)
elif filepath.endswith('.json'):
    df = pd.read_json(filepath)
else:
    raise ValueError(f"Unsupported file type: {filepath}")

info = {
    "shape": list(df.shape),
    "columns": list(df.columns),
    "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    "null_counts": df.isnull().sum().to_dict(),
    "null_percentage": (df.isnull().sum() / len(df) * 100).round(2).to_dict(),
    "numeric_columns": list(df.select_dtypes(include='number').columns),
    "categorical_columns": list(df.select_dtypes(include='object').columns),
    "sample_data": df.head(3).to_dict(),
    "describe": df.describe().to_dict(),
    "duplicates": int(df.duplicated().sum()),
    "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024**2, 2),
}

print(json.dumps(info, default=str))
