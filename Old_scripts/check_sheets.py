"""Check available sheets in Excel file"""
import pandas as pd
from pathlib import Path

excel_file = Path(r"C:\SoftDev\RPS\Typical Pushover Results\160Will_Global_Resp.xlsx")

xl = pd.ExcelFile(excel_file)
print(f"Available sheets in {excel_file.name}:")
for sheet in xl.sheet_names:
    print(f"  - {sheet}")
