# pyrefly: ignore [missing-import]
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np

path = r"d:\down\DataSet.csv"
df = pd.read_csv(path)
y = (df['F3897'] > 0).astype(int)

cols = ['F3917', 'F3916', 'F3896', 'F3895', 'F3897']
print("Inspection of highly correlated features:")
print(df[cols].head(20))

print("\nValue counts for F3917 vs target:")
print(pd.crosstab(df['F3917'].fillna(-1), y))

print("\nValue counts for F3916 vs target:")
print(pd.crosstab(df['F3916'].fillna(-1), y))
