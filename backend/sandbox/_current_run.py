import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# Define output directory
output_dir = 'output/figures/'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

try:
    # Load the cleaned dataset
    df = pd.read_csv('data/processed/cleaned_data.csv')

    # 1. Generate distribution plots for all numeric columns
    numeric_cols = df.select_dtypes(include=['float64']).columns
    for col in numeric_cols:
        plt.figure(figsize=(8, 6))
        sns.histplot(df[col], kde=True)
        plt.title(f'Distribution of {col}')
        plt.xlabel(col)
        plt.ylabel('Frequency')
        plt.savefig(output_dir + f'{col}_distribution.png', dpi=150, bbox_inches='tight')
        plt.close()

    # 2. Correlation heatmap
    plt.figure(figsize=(10, 8))
    sns.heatmap(df.corr(), annot=False, cmap="coolwarm")
    plt.title('Correlation Heatmap')
    plt.savefig(output_dir + 'correlation_heatmap.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 3. Box plots for numeric columns
    numeric_cols = df.select_dtypes(include=['float64']).columns
    for col in numeric_cols:
        plt.figure(figsize=(8, 6))
        sns.boxplot(x=df[col])
        plt.title(f'Boxplot of {col}')
        plt.xlabel(col)
        plt.savefig(output_dir + f'{col}_boxplot.png', dpi=150, bbox_inches='tight')
        plt.close()

    # 4. Value counts for categorical columns
    categorical_cols = df.select_dtypes(include=['object']).columns
    for col in categorical_cols:
        plt.figure(figsize=(8, 6))
        sns.countplot(x=df[col])
        plt.title(f'Value Counts of {col}')
        plt.xlabel(col)
        plt.savefig(output_dir + f'{col}_value_counts.png', dpi=150, bbox_inches='tight')
        plt.close()

    # 5. Pair plot for top 5 most correlated features
    top_n = 5
    correlations = df.corr()['sepal_length'].sort_values(ascending=False)
    top_features = correlations[1:top_n+2].index.tolist()  # Include sepal_length

    plt.figure(figsize=(12, 10))
    sns.pairplot(df[top_features])
    plt.title('Pair Plot of Top {} Most Correlated Features'.format(top_n))
    plt.savefig(output_dir + 'pairplot_top5.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 6. Missing value visualization
    missing_values = df.isnull().sum()
    plt.figure(figsize=(8, 6))
    sns.heatmap(missing_values, annot=True, fmt="d", cmap="YlGnBu")
    plt.title('Missing Values')
    plt.savefig(output_dir + 'missing_values.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 7. Save ALL plots to 'output/figures/' directory
    print("All plots saved to output/figures/")

    # 8. Print a JSON summary of key findings
    summary = {
        "dataset_shape": df.shape,
        "numeric_columns": list(df.select_dtypes(include=['float64']).columns),
        "categorical_columns": list(df.select_dtypes(include=['object']).columns),
        "duplicates_count": df.duplicated().sum(),
        "memory_usage_mb": df.memory_usage().sum() / 1024,
    }

    import json
    print(json.dumps(summary, indent=4))

except FileNotFoundError:
    print("Error: The file 'data/processed/cleaned_data.csv' was not found.")
except Exception as e:
    print(f"An error occurred during EDA: {e}")