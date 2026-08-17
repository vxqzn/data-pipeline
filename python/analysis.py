import pandas as pd
import scipy.stats as scs
from simulation import simulate_data

def analyze_data(users, purchases, run_type):
        
    control_total_users = (users["group"] == "Control").sum()
    control_buyers = purchases.loc[purchases["group"] == "Control", "userid"].nunique()
    control_nonbuyers = control_total_users - control_buyers

    variant_total_users = (users["group"] == "Variant").sum()
    variant_buyers = purchases.loc[purchases["group"] == "Variant", "userid"].nunique()
    variant_nonbuyers = variant_total_users - variant_buyers

    values = users.join(purchases.groupby("userid").agg(value=("value", "sum")), on="userid")
    values["value"] = values["value"].fillna(0)
    control_values = values.loc[values["group"] == "Control", "value"].to_numpy()
    variant_values = values.loc[values["group"] == "Variant", "value"].to_numpy()


    table = [[control_buyers, control_nonbuyers], [variant_buyers, variant_nonbuyers]]

    chi2test = scs.chi2_contingency(table)
    aov = scs.ttest_ind(control_values, variant_values, equal_var=False)

    users_grouped = users.groupby(["group", "region"]).size()
    purchases_grouped = purchases.groupby(["group", "region"]).agg(transactions=("userid", "count"), unique_buyers=("userid", "nunique"), revenue=("value", "sum"))

    metrics = users_grouped.to_frame(name="total_users").join(purchases_grouped)
    metrics["conversion_rate"] = metrics["unique_buyers"] / metrics["total_users"]
    metrics["average_order_value"] = metrics["revenue"] / metrics["transactions"]
    metrics["revenue_per_user"] = metrics["revenue"] / metrics["total_users"]

    control_revenue = control_values.sum()
    variant_revenue = variant_values.sum()
    
    control_ts = (purchases["group"] == "Control").sum()
    variant_ts = (purchases["group"] == "Variant").sum()

    control_cr = control_buyers / control_total_users
    variant_cr = variant_buyers / variant_total_users
    
    control_aov = control_revenue / control_ts
    variant_aov = variant_revenue / variant_ts

    control_rpu = control_revenue / control_total_users
    variant_rpu = variant_revenue / variant_total_users
    
    global_cr_lift = (variant_cr - control_cr) / control_cr
    global_aov_lift = (variant_aov - control_aov) / control_aov
    global_rpu_lift = (variant_rpu - control_rpu) / control_rpu
    
    global_metrics = pd.DataFrame([
    {
        "group": "Control",
        "total_users": control_total_users,
        "transactions": control_ts,
        "unique_buyers": control_buyers,
        "revenue": control_revenue,
        "conversion_rate": control_cr,
        "average_order_value": control_aov,
        "revenue_per_user": control_rpu,
        "p_value": chi2test[1],
        "ttest_p_value": aov[1],
        "conversion_lift": global_cr_lift,
        "aov_lift": global_aov_lift,
        "rpu_lift": global_rpu_lift
    },
    {
        "group": "Variant",
        "total_users": variant_total_users,
        "transactions": variant_ts,
        "unique_buyers": variant_buyers,
        "revenue": variant_revenue,
        "conversion_rate": variant_cr,
        "average_order_value": variant_aov,
        "revenue_per_user": variant_rpu,
        "p_value": chi2test[1],
        "ttest_p_value": aov[1],
        "conversion_lift": global_cr_lift,
        "aov_lift": global_aov_lift,
        "rpu_lift": global_rpu_lift
    }
]).set_index("group")

    regions = ["EMEA", "NA", "ASIA", "LATAM"]

    for r in regions:
        region_mask = metrics.index.get_level_values("region") == r
        ctrl_users = metrics.loc[("Control", r), "total_users"]
        ctrl_buyers = metrics.loc[("Control", r), "unique_buyers"]
        ctrl_nonbuyers = ctrl_users - ctrl_buyers

        vrnt_users = metrics.loc[("Variant", r), "total_users"]
        vrnt_buyers = metrics.loc[("Variant", r), "unique_buyers"]
        vrnt_nonbuyers = vrnt_users - vrnt_buyers

        contingency_table = [[ctrl_buyers, ctrl_nonbuyers], [vrnt_buyers, vrnt_nonbuyers]]
        chi2_result = scs.chi2_contingency(contingency_table)

        metrics.loc[region_mask, "p_value"] = chi2_result[1]

        table_prep = values.loc[values["region"] == r]
        table_filtered_control = table_prep.loc[table_prep["group"] == "Control", "value"].to_numpy()
        table_filtered_variant = table_prep.loc[table_prep["group"] == "Variant", "value"].to_numpy()

        ttest_result = scs.ttest_ind(table_filtered_control, table_filtered_variant, equal_var=False)

        metrics.loc[region_mask, "ttest_p_value"] = ttest_result[1]

        control_cr = metrics.loc[("Control", r), "conversion_rate"]
        variant_cr = metrics.loc[("Variant", r), "conversion_rate"]
        control_aov = metrics.loc[("Control", r), "average_order_value"]
        variant_aov = metrics.loc[("Variant", r), "average_order_value"]
        control_rpu = metrics.loc[("Control", r), "revenue_per_user"]
        variant_rpu = metrics.loc[("Variant", r), "revenue_per_user"]

        cr_lift = (variant_cr - control_cr) / control_cr
        aov_lift = (variant_aov - control_aov) / control_aov
        rpu_lift = (variant_rpu - control_rpu) / control_rpu

        metrics.loc[region_mask, "conversion_lift"] = cr_lift
        metrics.loc[region_mask, "aov_lift"] = aov_lift
        metrics.loc[region_mask, "rpu_lift"] = rpu_lift

    metrics["run_type"] = run_type
    global_metrics["run_type"] = run_type

    metrics = metrics.reset_index()
    global_metrics = global_metrics.reset_index()

    return metrics, global_metrics

(
    users_std, 
    purchases_std 
) = simulate_data()

(
    users_null, 
    purchases_null 
) = simulate_data(null_twin=True)

region_std, global_std = analyze_data(users_std, purchases_std, run_type="Standard")
region_null, global_null = analyze_data(users_null, purchases_null, run_type="Null Twin")

pd.concat([region_std, region_null]).to_csv("data/region_metrics.csv", index=False)
pd.concat([global_std, global_null]).to_csv("data/global_metrics.csv", index=False)
