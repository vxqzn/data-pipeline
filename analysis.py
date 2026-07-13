import pandas as pd
import scipy.stats as scs
from simulation import simulate_data


(
    users_std, 
    purchases_std 
) = simulate_data()

(
    users_null, 
    purchases_null 
) = simulate_data(null_twin=True)


control_total_users_std = (users_std["group"] == "Control").sum()
control_buyers_std = purchases_std.loc[purchases_std["group"] == "Control", "userid"].nunique()
control_nonbuyers_std = control_total_users_std - control_buyers_std

variant_total_users_std = (users_std["group"] == "Variant").sum()
variant_buyers_std = purchases_std.loc[purchases_std["group"] == "Variant", "userid"].nunique()
variant_nonbuyers_std = variant_total_users_std - variant_buyers_std


control_total_users_null = (users_null["group"] == "Control").sum()
control_buyers_null = purchases_null.loc[purchases_null["group"] == "Control", "userid"].nunique()
control_nonbuyers_null = control_total_users_null - control_buyers_null

variant_total_users_null = (users_null["group"] == "Variant").sum()
variant_buyers_null = purchases_null.loc[purchases_null["group"] == "Variant", "userid"].nunique()
variant_nonbuyers_null = variant_total_users_null - variant_buyers_null



control_values_std = purchases_std.loc[purchases_std["group"] == "Control", "value"].to_numpy()
variant_values_std = purchases_std.loc[purchases_std["group"] == "Variant", "value"].to_numpy()

control_values_null = purchases_null.loc[purchases_null["group"] == "Control", "value"].to_numpy()
variant_values_null = purchases_null.loc[purchases_null["group"] == "Variant", "value"].to_numpy()


std_table = [[control_buyers_std, control_nonbuyers_std], [variant_buyers_std, variant_nonbuyers_std]]
a = scs.chi2_contingency(std_table)

null_table = [[control_buyers_null, control_nonbuyers_null], [variant_buyers_null, variant_nonbuyers_null]]
b = scs.chi2_contingency(null_table)

aov_std = scs.ttest_ind(control_values_std, variant_values_std, equal_var=False)
aov_null = scs.ttest_ind(control_values_null, variant_values_null, equal_var=False)

std_users_grouped = users_std.groupby(["group", "region"]).size()
std_purchases_grouped = purchases_std.groupby(["group", "region"]).agg(transactions=("userid", "count"), unique_buyers=("userid", "nunique"), revenue=("value", "sum"))

std_metrics = std_users_grouped.to_frame(name="total_users").join(std_purchases_grouped)
std_metrics["conversion_rate"] = std_metrics["unique_buyers"] / std_metrics["total_users"]
std_metrics["average_order_value"] = std_metrics["revenue"] / std_metrics["transactions"]
std_metrics["revenue_per_user"] = std_metrics["revenue"] / std_metrics["total_users"]

print(std_metrics)