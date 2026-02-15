import pandas as pd
def process_data(billing_df, orders_df):
    # Normalize headers
    billing_df.columns = billing_df.columns.str.lower().str.strip()
    orders_df.columns = orders_df.columns.str.lower().str.strip()

    # Rename to a common schema
    billing_df = billing_df.rename(columns={
        "insurance": "insurance_name",
        "qty_billed": "qty"
    })

    orders_df = orders_df.rename(columns={
        "qty_ordered": "qty"
    })

    # Aggregate billing
    billing_summary = (
        billing_df
        .groupby(
            ["ndc", "drug_name", "insurance_name", "bin_number"],
            as_index=False
        )
        .agg(billed_qty=("qty", "sum"))
    )

    # Aggregate orders
    orders_summary = (
        orders_df
        .groupby(["ndc", "drug_name"], as_index=False)
        .agg(ordered_qty=("qty", "sum"))
    )

    # Merge
    result = billing_summary.merge(
        orders_summary,
        on=["ndc", "drug_name"],
        how="left"
    )

    result["ordered_qty"] = result["ordered_qty"].fillna(0)

    result["qty_diff"] = result["billed_qty"] - result["ordered_qty"]


    # Status flag
    result["status"] = result.apply(
        lambda x: "PASSED" if x.ordered_qty >= x.billed_qty else "FAILED",
        axis=1
    )

    return result
