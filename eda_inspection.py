# pyrefly: ignore [missing-import]
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np

path = r"d:\down\DataSet.csv"
print("Loading full dataset for EDA inspection...")
df = pd.read_csv(path)
print("Dataset loaded successfully.")

# Confirm F3897 values
if 'F3897' in df.columns:
    print("F3897 value counts:")
    print(df['F3897'].value_counts(dropna=False))
    
    # Binarize it: 0 stays 0, anything above 0 becomes 1
    y_bin = (df['F3897'] > 0).astype(int)
    print("Binarized target (y) counts:")
    print(y_bin.value_counts(normalize=True))
else:
    print("F3897 not found in columns!")

# NA density
na_counts = df.isna().sum()
total_elements = df.size
total_na = na_counts.sum()
print(f"Overall NA density: {total_na / total_elements * 100:.2f}%")

# Check F3886 (account type) and F3891 (occupation) distributions
for col in ['F3886', 'F3891']:
    if col in df.columns:
        print(f"\n{col} distribution:")
        print(df[col].value_counts(dropna=False))
    else:
        print(f"\n{col} not found in columns!")

# Check F3888 (date) format and missingness
if 'F3888' in df.columns:
    print("\nF3888 (date) examples:")
    print(df['F3888'].head(10))
    print("F3888 missing count:", df['F3888'].isna().sum())
else:
    print("\nF3888 not found in columns!")
