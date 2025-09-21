import pandas as pd

# read your existing CSV
df = pd.read_csv("./sap_data_dictionary.csv")

# insert new column after 'Sheet Name'
df.insert(1, "Mandatory Sheet", df["Sheet Name"].apply(lambda x: "Yes" if x == "Basic Data" else "No"))

# save back to the same file (overwrite)
df.to_csv("./sap_data_dictionary.csv", index=False)

# OR save as a new file to keep original safe
# df.to_csv("sap_data_dictionary_with_mandatory.csv", index=False)
