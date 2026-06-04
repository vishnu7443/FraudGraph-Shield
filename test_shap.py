# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
import pandas as pd
# pyrefly: ignore [missing-import]
import lightgbm as lgb
# pyrefly: ignore [missing-import]
import shap
# pyrefly: ignore [missing-import]
import matplotlib.pyplot as plt
import os

os.makedirs("test_plots", exist_ok=True)
print("Testing SHAP with LightGBM...")

# Create dummy binary dataset
np.random.seed(42)
X = pd.DataFrame(np.random.randn(100, 10), columns=[f'col_{i}' for i in range(10)])
y = np.random.randint(0, 2, size=100)

model = lgb.LGBMClassifier(n_estimators=10, max_depth=3, random_state=42, verbose=-1)
model.fit(X, y)

explainer = shap.TreeExplainer(model)
shap_values = explainer(X)

print("shap_values type:", type(shap_values))
print("shap_values shape:", shap_values.shape)

# Let's see if we can plot beeswarm
plt.figure()
shap.plots.beeswarm(shap_values, show=False)
plt.tight_layout()
plt.savefig("test_plots/test_beeswarm.png")
plt.close()

# Let's see if we can plot bar
plt.figure()
shap.plots.bar(shap_values, show=False)
plt.tight_layout()
plt.savefig("test_plots/test_bar.png")
plt.close()

# Let's see if we can plot waterfall
# For waterfall, we pass shap_values[idx]
plt.figure()
shap.plots.waterfall(shap_values[0], show=False)
plt.tight_layout()
plt.savefig("test_plots/test_waterfall.png")
plt.close()

print("SHAP test passed successfully! Generated plots in test_plots/")
