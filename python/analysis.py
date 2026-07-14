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


def analyze_data(users, purchases):
        
    control_total_users = (users["group"] == "Control").sum()
    control_buyers = purchases.loc[purchases["group"] == "Control", "userid"].nunique()
    control_nonbuyers = control_total_users - control_buyers

    variant_total_users = (users["group"] == "Variant").sum()
    variant_buyers = purchases.loc[purchases["group"] == "Variant", "userid"].nunique()
    variant_nonbuyers = variant_total_users - variant_buyers

    values = users.join(purchases.groupby("userid").agg(value=("value", "sum")), on="userid").fillna(0)
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
    
    return chi2test, aov, metrics


a, b, std_results = analyze_data(users=users_std, purchases=purchases_std)
c, d, null_results = analyze_data(users=users_null, purchases=purchases_null)

std_results.to_csv("data/std_metrics_results.csv")
null_results.to_csv("data/null_metrics_results.csv")


#print(f"### Metrics table (std) ###")
#print(std_results)
#print(f"\nchi2test P-value (std): {a[1]}")
#print(f"ttest P-value (std): {b[1]}")

#print(f"\n### Metrics table (null) ###")
#print(null_results)
#print(f"\nchi2test P-value (null): {c[1]}")
#print(f"ttest P-value (null)): {d[1]}")
