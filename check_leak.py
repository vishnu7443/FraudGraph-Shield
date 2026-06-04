import pandas as pd
import numpy as np

path = r"d:\down\DataSet.csv"
print("Loading dataset to check for label leakage...")
df = pd.read_csv(path)
y = (df['F3897'] > 0).astype(int)

# Let's drop F3897, Unnamed: 0, and any non-numeric columns to compute correlation
numeric_cols = df.select_dtypes(include=[np.number]).columns
numeric_cols = [c for c in numeric_cols if c not in ['F3897', 'Unnamed: 0']]

correlations = {}
for col in numeric_cols:
    # Handle NAs by dropping them for correlation calculation
    temp_df = pd.DataFrame({'feature': df[col], 'target': y}).dropna()
    if len(temp_df) > 10:
        corr = temp_df['feature'].corr(temp_df['target'])
        if not pd.isna(corr):
            correlations[col] = corr

# Sort by absolute correlation
sorted_corr = sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True)
print("\nTop 30 features correlated with the binarized target:")
for col, corr in sorted_corr[:30]:
    print(f"  - {col}: correlation = {corr:.4f}")
    
# Let's inspect object columns too by computing target means
object_cols = df.select_dtypes(exclude=[np.number]).columns
print("\nObject columns:")
print(list(object_cols))
for col in object_cols:
    print(f"\nTarget distribution per category in {col}:")
    temp_df = pd.DataFrame({'feature': df[col], 'target': y})
    print(temp_df.groupby('feature')['target'].mean())
