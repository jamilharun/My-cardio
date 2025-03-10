import pandas as pd

# Paths to datasets
dataset1_path = "main/datasets/cardio_train.csv"  # Change to actual file names
dataset2_path = "main/datasets/Cardiovascular_Disease_Dataset.csv"

# Load datasets
df1 = pd.read_csv(dataset1_path, nrows=5)  # Load first few rows to avoid memory issues
df2 = pd.read_csv(dataset2_path, nrows=5)

# Extract column names
columns1 = df1.columns.tolist()
columns2 = df2.columns.tolist()

# Print results
print("📌 Columns in cardio_train.csv: ")
print(columns1)

print("\n📌 Columns in Cardiovascular_Disease_Dataset.csv: ")
print(columns2)
