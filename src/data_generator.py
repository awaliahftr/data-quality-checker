import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

def generate_daily_data():
    today = datetime.now()
    seed = int(today.strftime("%Y%m%d"))
    random.seed(seed)
    np.random.seed(seed)

    n = 1000

    #1. ID with occasional duplicates and nulls
    ids = list(range(1, n + 1))
    if today.weekday() == 0:  # Monday
        ids.extend([100, 200, 300])
    if today.day % 5 == 0:
        ids.extend([np.nan] * 5)

    #2. Names with intentional formatting issues
    names = []
    base_names = ["john doe", "jane smith", "alice wonderland", "bob the builder", "do kyungsoo"]
    
    for _ in range(len(ids)):
        name = random.choice(base_names)
    
        if today.weekday() == 1:   
            name = f"   {name}  "
        elif today.weekday() == 2:  
            name = name.upper()
        
        names.append(name)
    
    #3. Ages with occasional text values
    ages = np.random.randint(18, 65, len(ids))
    if today.day == 1:
        ages[20:30] = "twenty"
    
    #4. Salaries with outliers and $ signs
    salaries = np.random.randint(30000, 120000, len(ids)).astype(str)
    if today.weekday() == 4:  
        salaries[200:210] = "-9999"
    if today.weekday() == 3:  
        for i in range(50, 60):
            salaries[i] = f"${salaries[i]}"

    #5. Dates with inconsistent formats
    dates = []
    start_date = datetime(2020, 1, 1)   
    for _ in range(len(ids)):
        date = start_date + timedelta(days=random.randint(0, 1500))
        fmt_choice = today.day % 3       
        if fmt_choice == 0:
            dates.append(date.strftime("%Y-%m-%d"))
        elif fmt_choice == 1:
            dates.append(date.strftime("%d/%m/%Y"))
        else:
            dates.append("Invalid Date")
    
    #6. Departments with inconsistent formatting
    depts = np.random.choice(["HR", "Finance", "IT", "Marketing"], len(ids))
    if today.weekday() == 5:  
        depts = [f" {d.lower()} " for d in depts]
    
    #7. Random missing values
    df = pd.DataFrame({
        'id': ids,
        'name': names,
        'age': ages,
        'salary': salaries,
        'join_date': dates,
        'department': depts
    })

    missing_rows = np.random.choice(df.index, size=random.randint(10, 20), replace=False)
    df.loc[missing_rows, 'department'] = np.nan

    #save
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/sample_data.csv', index=False)
    print(f"✅ Data generated for {today.strftime('%Y-%m-%d')}")
    print(f"   - Rows: {len(df):,}")
    print(f"   - Columns: {len(df.columns)}")

if __name__ == "__main__":
    generate_daily_data()
