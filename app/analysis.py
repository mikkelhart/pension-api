import pandas as pd
import matplotlib.pyplot as plt
import io
from pathlib import Path


#Load data once at module level (cached)
DATA_DIR = Path(__file__).parent / "data"
codes = pd.read_csv(DATA_DIR / "codes.csv")
euro_pension_spending_q = pd.read_csv(DATA_DIR / "european_pension_spending_quickstart.csv")

# Mapping for codes to names for use in plot_compare function at line 39

COUNTRY_CODE_TO_NAME = {
    row["code"]: row["label"]
    for _, row in codes[codes["dimension"] == "country"].iterrows()
}
ls

#Valid metrics (from the CSV)
VALID_METRICS = [
    'pensions_pct_gdp', "pensions_mio_eur", 'pensions_pp_per_head',
    'old_age_pct_gdp', 'survivors_pct_gdp', 'disability_pct_gdp',
    'means_tested_pct_gdp', 'old_age_share_pct', 'survivors_share_pct',
    'disability_share_pct'
]

def get_countries():
    """Return list of available countries"""
    countries_df = codes[codes["dimension"] == "country"]
    countries = countries_df[countries_df["code"].str.len() <= 2]
    groups = countries_df[countries_df["code"].str.len() > 2]

    return {
        "countries": [{"code":row["code"], "name": row["label"]} for _, row in countries.iterrows()],
        "groups": groups["label"].tolist()
    }

def plot_compare(countries, metric="pensions_pct_gdp"):
    """Generate comparison plot (returns PNG bytes)"""
    country_list = [c.strip() for c in countries.split(",")]
    filtered = euro_pension_spending_q[euro_pension_spending_q["country_code"].isin(country_list)].copy()

    filtered = filtered.dropna(subset=[metric])
    if filtered.empty:
        raise ValueError(f"No data available for selected countries and metric '{metric}'")

    plt.figure(figsize=(12,6))
    colors = ['blue', 'red', 'green', 'purple', 'orange', 'brown', 'pink', 'gray']

    for i, country_code in enumerate(country_list):
        country_data = filtered[filtered["country_code"] == country_code].sort_values('year')
        if not country_data.empty:
            country_name = COUNTRY_CODE_TO_NAME.get(country_code, country_code)
            plt.plot(country_data["year"], 
                     country_data[metric], 
                     label=country_name, 
                     color=colors[i % len(colors)],
                     marker='o', 
                     linewidth=2)
    plt.xlabel("Year")
    plt.ylabel(metric.replace( '_', ' ').title())
    plt.title(f"{metric.replace( '_', ' ').title()} Comparison")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return buf.getvalue()