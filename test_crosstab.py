import pandas as pd

path = r"d:\down\DataSet.csv"
df = pd.read_csv(path)
y = (df['F3897'] > 0).astype(int)

print("Crosstab of F3896 vs target:")
print(pd.crosstab(df['F3896'], y))

print("\nCrosstab of F3895 vs target:")
print(pd.crosstab(df['F3895'], y))
