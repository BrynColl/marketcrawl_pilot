import pandas as pd
from urllib.parse import urlparse

df = pd.read_csv("companies.tsv", sep="\t")
df["normalized_domain"] = (
    df["domain"].str.replace(r"^https?://", "", regex=True)
                .str.replace(r"^www\.", "", regex=True)
                .str.rstrip("/")
                .str.lower()
)

print(df)
print("\nDuplicate normalized domains:")
dupes = df[df.duplicated("normalized_domain", keep=False)].sort_values("normalized_domain")
print(dupes if not dupes.empty else "None")
