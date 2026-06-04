import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt
import seaborn as sns
import os

def run_eda(csv_path, output_dir="plots"):
    os.makedirs(output_dir, exist_ok=True)
    print("Loading dataset for EDA...")
    df = pd.read_csv(csv_path)
    
    # 1. Binarize F3897 and print value counts
    print("Binarizing target variable F3897...")
    y = (df['F3897'] > 0).astype(int)
    class_counts = y.value_counts()
    class_pct = y.value_counts(normalize=True) * 100
    print(f"Class distribution: 0 = {class_counts[0]} ({class_pct[0]:.2f}%), 1 = {class_counts[1]} ({class_pct[1]:.2f}%)")
    
    # Plot Class Distribution
    plt.figure(figsize=(6, 4))
    sns.barplot(x=class_counts.index, y=class_counts.values, palette='viridis')
    plt.title('Binarized Target Class Distribution (F3897)')
    plt.xlabel('Suspicious / Fraud Label (0 = Clean, 1 = Suspicious/Fraud)')
    plt.ylabel('Count')
    for i, v in enumerate(class_counts.values):
        plt.text(i, v + 100, f"{v}\n({class_pct[i]:.1f}%)", ha='center', fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'class_distribution.png'))
    plt.close()
    
    # 2. NA Heatmap across columns (sampling columns or visualizing density)
    print("Analyzing missingness/NA density...")
    na_matrix = df.isna()
    overall_na_density = na_matrix.mean().mean() * 100
    print(f"Overall NA density: {overall_na_density:.2f}%")
    
    # Let's plot NA density across columns as a line/bar chart, and a sample heatmap
    # Plotting a full 9082x3924 heatmap can be extremely slow and memory intensive,
    # so we will compute the NA percentage per column and plot the density distribution.
    col_na_pct = na_matrix.mean() * 100
    
    plt.figure(figsize=(10, 4))
    sns.histplot(col_na_pct, bins=30, kde=True, color='darkred')
    plt.title('Distribution of Missingness (NA %) per Column')
    plt.xlabel('NA %')
    plt.ylabel('Number of Columns')
    plt.axvline(68, color='blue', linestyle='--', label='68% NA Average')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'na_column_distribution.png'))
    plt.close()
    
    # Create a small representative heatmap of NA (e.g. first 100 columns, 500 rows)
    plt.figure(figsize=(12, 6))
    sns.heatmap(na_matrix.iloc[:1000, 1:101], cbar=False, yticklabels=False, cmap='viridis')
    plt.title('NA Heatmap (First 1000 Rows, Columns F1-F100)')
    plt.xlabel('Features')
    plt.ylabel('Accounts')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'na_heatmap_sample.png'))
    plt.close()
    
    # 3. Categorical Distributions (F3886 and F3891)
    print("Plotting categorical distributions...")
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # F3886 (top 8 account types)
    acc_types = df['F3886'].value_counts()
    sns.barplot(x=acc_types.values[:8], y=acc_types.index[:8], ax=axes[0], palette='magma')
    axes[0].set_title('Top 8 Account Types (F3886)')
    axes[0].set_xlabel('Count')
    axes[0].set_ylabel('Account Type')
    
    # F3891 (occupation)
    occupations = df['F3891'].value_counts()
    sns.barplot(x=occupations.values, y=occupations.index, ax=axes[1], palette='plasma')
    axes[1].set_title('Occupation Distribution (F3891)')
    axes[1].set_xlabel('Count')
    axes[1].set_ylabel('Occupation')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'categorical_distributions.png'))
    plt.close()
    
    # 4. Check date parsing format
    print("Testing date parsing on F3888...")
    parsed_dates = pd.to_datetime(df['F3888'], format='%m-%d-%Y', errors='coerce')
    failed_parses = parsed_dates.isna().sum()
    print(f"Failed parses with '%m-%d-%Y': {failed_parses} out of {len(df)}")
    
    if failed_parses > 0:
        parsed_dates = pd.to_datetime(df['F3888'], errors='coerce')
        print(f"Failed parses with default parser: {parsed_dates.isna().sum()}")
        
    print("EDA completed successfully. All plots saved to:", output_dir)

if __name__ == '__main__':
    run_eda(r"d:\down\DataSet.csv")
