import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text
from preprocessor import FraudPreprocessor

path = r"d:\down\DataSet.csv"
print("Loading dataset...")
df = pd.read_csv(path)
y = (df['F3897'] > 0).astype(int)

# Drop index and leak columns F3916, F3917
df_clean = df.drop(columns=['Unnamed: 0', 'F3916', 'F3917'])

prep = FraudPreprocessor()
X_prep, y_prep = prep.fit_transform(df_clean)

# Train a simple Decision Tree
tree = DecisionTreeClassifier(max_depth=3, random_state=42)
tree.fit(X_prep, y_prep)

print("\nDecision Tree Structure:")
print(export_text(tree, feature_names=list(X_prep.columns)))
