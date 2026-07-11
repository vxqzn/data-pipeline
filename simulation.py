import numpy as np
import pandas as pd

user_col = ["userid", "region", "group"]
purchases_col = ["userid", "timestamp", "value"]
arr1 = ["Control", "Variant"]

df_users = pd.DataFrame(columns=user_col)
df_purchases = pd.DataFrame(columns=purchases_col)

rng = np.random.default_rng(seed=64)
x = rng.choice(arr1, size=10000)

df_users["group"] = x

print(df_users)