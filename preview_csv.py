import csv

path = r"d:\down\DataSet.csv"
print("Reading CSV preview using standard csv module...")
with open(path, mode='r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    print(f"Number of columns: {len(header)}")
    print("First 20 columns:")
    print(header[:20])
    print("Last 20 columns:")
    print(header[-20:])
    
    # Read a few rows
    for i in range(3):
        row = next(reader)
        print(f"Row {i+1} preview:")
        # Print column index/name and value for some metadata columns
        # F3886 is account type, F3888 is opening date, F3891 is occupation, F3897 is target
        for col_name in ['F3886', 'F3888', 'F3891', 'F3897', 'F3900', 'F3880']:
            if col_name in header:
                idx = header.index(col_name)
                print(f"  {col_name} (index {idx}): {row[idx]}")
