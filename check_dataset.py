import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np

path = r"d:\down\DataSet.csv"
print("Loading dataset...")
df = pd.read_csv(path, nrows=5)
print("Shape of preview:", df.shape)
print("Columns:", list(df.columns[:20]), "...", list(df.columns[-20:]))

# Let's count the total rows and columns
print("Loading shape...")
df_shape = pd.read_csv(path, usecols=[0])
print("Total rows:", len(df_shape))
