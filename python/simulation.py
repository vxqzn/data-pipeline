import numpy as np
import pandas as pd

def simulate_data(null_twin = False, seed = 64):
    
    ss = np.random.SeedSequence(seed)
    
    (
        u_group_rng, 
        u_region_rng, 
        ctrl_draw_rng, 
        var_draw_rng, 
        p_uid_rng, 
        offset_rng, 
        control_multi_rng, 
        variant_multi_rng, 
        purchase_value_rng
    ) = [np.random.default_rng(s) for s in ss.spawn(9)]

    group_options = ["Control", "Variant"]
    region_options = ["EMEA", "NA", "ASIA", "LATAM"]

    users_userids = np.arange(5_000_000)
    users_groups = u_group_rng.choice(group_options, p=[0.5, 0.5], size=5_000_000)
    users_regions = u_region_rng.choice(region_options, p=[0.25, 0.25, 0.25, 0.25], size=5_000_000)

    control_buyers = users_userids[users_groups == "Control"]
    variant_buyers = users_userids[users_groups == "Variant"]

    control_draw = ctrl_draw_rng.choice(control_buyers, size=100_000, replace=False)
    
    if null_twin:
        variant_draw = var_draw_rng.choice(variant_buyers, size=100_000, replace=False)
    else:
        variant_draw = var_draw_rng.choice(variant_buyers, size=150_000, replace=False)

    buyerids = np.concatenate([control_draw, variant_draw])

    purchases_uids = p_uid_rng.choice(buyerids, size=500_000, replace=True)

    offset = pd.to_timedelta(offset_rng.integers(1, 2678400, size=500_000), 's')
    purchases_timestamps = pd.to_datetime("2026-07-01") + offset

    df_users = pd.DataFrame({
        "userid": users_userids,
        "region": users_regions,
        "group": users_groups
    })

    df_purchases = pd.DataFrame({
        "userid": purchases_uids,
        "timestamp": purchases_timestamps
    })

    u_controls = df_users["group"] == "Control"
    u_variants = df_users["group"] == "Variant"
    df_users.loc[u_controls, "multiplier"] = control_multi_rng.lognormal(0.0, 0.5, u_controls.sum())
    if null_twin:
        df_users.loc[u_variants, "multiplier"] = variant_multi_rng.lognormal(0.0, 0.5, u_variants.sum())
    else:
        df_users.loc[u_variants, "multiplier"] = variant_multi_rng.lognormal(0.15, 0.5, u_variants.sum())
    
    df_purchases = df_purchases.merge(df_users, on="userid", how='left')

    nn = 0.99

    df_purchases["value"] = purchase_value_rng.integers(10, 25, 500_000)
    df_purchases["value"] = (df_purchases["value"] * df_purchases["multiplier"]).round().to_numpy(dtype=int) + nn

    return df_users, df_purchases
