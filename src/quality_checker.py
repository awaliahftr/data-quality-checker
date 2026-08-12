import pandas as pd
import numpy as np
import os
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional

#Format detection
def detect_format_issue(df: pd.DataFrame) -> List[str]:
    issues = []

    for col in df.columns:
        if df[col].dropna().empty:
            continue

        is_string_col = df[col].dtype == 'object'

        if is_string_col:
            #1. Numeric as text
            test_convert = pd.to_numeric(df[col], errors='coerce')
            if test_convert.notna().sum() > 0:
                sample = df[col].dropna().iloc[0]
                issues.append(f"Column '{col}' is numeric but stored as text. Sample'{sample}'")

            #2. Leading/trailing spaces
            if df[col].str.contains(r'^\s+|\s+$', na=False).any():
                issues.append(f"Column '{col}' has leading/trailing spaces.")

            #3. Special/non-printable characters
            if df[col].str.contains(r'[^a-zA-Z0-9\s.,!?()\-]', na=False).any():
                issues.append(f"Column '{col}' has special/non-printable characters.")

            #4. Inconsistent casing
            sample = df[col].dropna().astype(str)
            if len(sample) > 0:
                has_upper = sample.str.isupper().any()
                has_lower = sample.str.islower().any()
                has_title = sample.str.istitle().any()
                if sum([has_upper, has_lower, has_title]) > 1:
                    issues.append(f"Column '{col}' has inconsistent casing (mix of UPPER, lower, Title.)")
    return issues        

#2. Schema Validation
def validate_schema(df:pd.DataFrame, expected_schema: Optional[Dict[str, str]] = None) -> Dict[str, List[str]]:
    result = {'critical': [], 'warning': []}

    current_columns = set(df.columns)

    if expected_schema is None:
        result['warning'].append("No expected schema provided. Recording current structure only.")
        for col in df.columns:
            result['warning'].append(f"   - {col}: {df[col].dtype}")
        return result
    expected_set = set(expected_schema.keys())

    #Missing columns
    missing_cols = expected_set - current_columns
    if missing_cols:
        result['critical'].append(f"Missing columns: {missing_cols}")
    
    #Extra columns
    extra_cols = current_columns - expected_set
    if extra_cols:
        result['warning'].append(f"Extra columns detected: {extra_cols}")
    
    #Type mismatch
    for col, expected_dtype in expected_schema.items():
        if col in df.columns:
            actual_dtype = str(df[col].dtype)
            if actual_dtype != expected_dtype:
                result['critical'].append(f"Type mismatch in '{col}': expected {expected_dtype}, got {actual_dtype} ")
    return result

#3. Primary key validation
def validate_primary_key(df:pd.DataFrame, pk_col: str = 'id') -> List[str]:
    issues = []

    if pk_col not in df.columns:
        issues.append(f"CRITICAL: Primary key '{pk_col}' not found!")
        return issues
    
    null_count = df[pk_col].isnull().sum()
    if null_count > 0:
        issues.append(f"CRITICAL: '{pk_col}' has {null_count} null values.")

    duplicate_count = df[pk_col].duplicated().sum()
    if duplicate_count > 0:
        issues.append(f"CRITICAL: '{pk_col}' has {duplicate_count} duplicate values.")
    
    if null_count == 0 and duplicate_count == 0:
        issues.append(f"Primary key '{pk_col}' is valid (unique, no nulls).")
    
    return issues

#4. Outlier Detection
def detect_outliers(df: pd.DataFrame) -> List[str]:
    issues = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    if numeric_cols.empty:
        issues.append("No numeric columns found for outlier detection.")
        return issues
    
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        outlier_count = df[(df[col] < lower_bound) | (df[col] > upper_bound)].shape[0]
        if outlier_count > 0:
            issues.append(f"Column '{col}': {outlier_count} potential outliers detected.")

    if not issues:
        issues.append("No outliers detected in numeric columns.")
    
    return issues

#5. Main Quality Check Function
def check_data_quality(
        df: pd.DataFrame,
        expected_schema: Optional[Dict[str, str]] = None,
        pk_col: str = 'id'
) -> Tuple[str, bool]:
    
    report_lines = []
    has_critical = False

    #Header
    report_lines.append("=" * 70)
    report_lines.append(f"DATA QUALITY REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 70)
    report_lines.append(f"Total rows: {len(df):,}")
    report_lines.append(f"Total columns: {len(df.columns)}")

    #1. Missing values
    report_lines.append("\n 1. Missing values:")
    missing = df.isnull().sum()
    missing_pct = (missing / len(df)) * 100
    has_missing = False

    for col in df.columns:
        if missing[col] > 0:
            report_lines.append(f"   - {col}: {missing[col]:,} rows ({missing_pct[col]:.2f}%)")
            has_missing = True
    if not has_missing:
        report_lines.append("No missing values found!")
    else:
        has_critical = True

    #2. Duplicates
    report_lines.append("\n 2. Duplicates:")
    duplicate_count = df.duplicated().sum()
    report_lines.append(f"- Total duplicate rows: {duplicate_count:,}")
    if duplicate_count == 0:
        report_lines.append("No duplicates found!")
    else:
        has_critical = True
    
    #3. Schema
    report_lines.append("\n 3. Schema Validation:")
    schema_result = validate_schema(df, expected_schema)
    for issue in schema_result['critical']:
        report_lines.append(f"  {issue}")
        has_critical = True
    for issue in schema_result['warning']:
        report_lines.append(f"  {issue}")

    #4. Primary key
    report_lines.append("\n 4. Primary Key Validation:")
    pk_issues = validate_primary_key(df, pk_col)
    for issue in pk_issues:
        report_lines.append(f"  {issue}")
        if "CRITICAL" in issue:
            has_critical = True
    
    #5. Outliers
    report_lines.append("\n 5. Outlier Detection:")
    outlier_issues = detect_outliers(df)
    for issue in outlier_issues:
        report_lines.append(f"  {issue}")
    
    #6. Format issues
    report_lines.append("\n 6. Format & Integrity:")
    format_issues = detect_format_issue(df)
    if format_issues:
        for issue in format_issues:
            report_lines.append(f"  {issue}")
    else:
        report_lines.append("   All format checks passed!")
    
    #7. Summary Statistics
    report_lines.append("\n 7. Summary Statistics:")
    report_lines.append("   (Numeric columns only)")
    numeric_desc = df.describe().to_string()
    for line in numeric_desc.split('\n'):
        report_lines.append(f"  {line}")
    
    #Footer
    report_lines.append("\n" + "=" * 70)
    report_lines.append(f"Report completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if has_critical:
        report_lines.append("CRITICAL ISSUES DETECTED! Action required.")
    else:
        report_lines.append("No critical issues found. Data quality is acceptable.")
    return "\n".join(report_lines), has_critical

#6. main
if __name__ == "__main__":
    EXPECTED_SCHEMA = {
        'id': 'int64',
        'name': 'object',
        'age': 'int64',
        'salary': 'int64',
        'join_date': 'object',
        'department': 'object'
    }

    PRIMARY_KEY = 'id'
    DATA_PATH = 'data/sample_data.csv'
    REPORTS_DIR = 'reports'

    try:
        df = pd.read_csv(DATA_PATH)
        print(f"Data loaded: {len(df):,} rows, {len(df.columns)} columns")
    except FileNotFoundError:
        print(f"Error: File '{DATA_PATH}' not found. Run data_generator.py first.")
        exit(1)
    except Exception as e:
        print(f"Error loading data: {e}")
        exit(1)
    
    #run quality check
    report, has_critical = check_data_quality(df, EXPECTED_SCHEMA, PRIMARY_KEY)

    #SAVE REPORT
    os.makedirs(REPORTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d")
    report_path = f'{REPORTS_DIR}/data_quality_{timestamp}.txt'

    with open(report_path, 'w') as f:
        f.write(report)

    print(f"\n Report saved to: {report_path}")

    #flag for email alert
    alert_path = f'{REPORTS_DIR}/alert_needed.txt'
    if has_critical:
        print("CRITICAL ISSUES DETECTED! Alert will be triggered.")
        with open(alert_path, 'w') as f:
            f.write("ALERT: Critical data quality issues detected.")
    else:
        print("All checks passed! No critical issues.")
        if os.path.exists(alert_path):
            os.remove(alert_path)



