import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional

#logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

#constants
# Default expected schema
DEFAULT_SCHEMA = {
    'id': 'int64',
    'name': 'object',
    'age': 'int64',
    'salary': 'int64',
    'join_date': 'object',
    'department': 'object'
}

# Columns that require special handling in clean_data
CATEGORICAL_COLUMNS = ['department']
NUMERIC_COLUMNS = ['salary', 'age']
DATE_COLUMNS = ['join_date']

#Format detection
def detect_format_issues(df: pd.DataFrame) -> List[str]:
    issues = []

    for col in df.columns:
        if df[col].dropna().empty:
            continue
        if df[col].dtype != 'object':
            continue
            
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

    #Missing columns (CRITICAL)
    missing_cols = expected_set - current_columns
    if missing_cols:
        result['critical'].append(f"Missing columns: {missing_cols}")
    
    #Extra columns (WARNING)
    extra_cols = current_columns - expected_set
    if extra_cols:
        result['warning'].append(f"Extra columns detected: {extra_cols}")
    
    #Type mismatch (CRITICAL)
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
def detect_outliers(df: pd.DataFrame, iqr_multiplier: float = 1.5) -> List[str]:
    issues = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    if numeric_cols.empty:
        issues.append("No numeric columns found for outlier detection.")
        return issues
    
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - iqr_multiplier * IQR
        upper_bound = Q3 + iqr_multiplier * IQR

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
    if not schema_result['critical'] and not schema_result['warning']:
        report_lines.append("   No schema issues detected. All columns match expectations.")
    else:
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
    format_issues = detect_format_issues(df)
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

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Safely standardizes data format WITHOUT altering business-critical numeric values.
    - Removes leading/trailing spaces (strip)
    - Standardizes capitalization (Title case for departments, lower case for names)
    - Converts strings to numeric types (if conversion fails, sets to NaN, but DOES NOT fill them)
    - Fills missing values ONLY for categorical columns ('Unknown')
    - Removes duplicates (safe, as primary keys must be unique)
    - DOES NOT touch numeric outliers or missing numeric values
    """
    df_clean = df.copy()
    
    # 1. TEXT STANDARDIZATION 
    for col in df_clean.select_dtypes(include=['object']).columns:
        df_clean[col] = df_clean[col].astype(str).str.strip()
        
        if col in CATEGORICAL_COLUMNS:
            # Standardize to Title Case (e.g., "hr" -> "Hr")
            df_clean[col] = df_clean[col].str.title()
        else:
            # For other text columns (like names), standardize to lower case
            df_clean[col] = df_clean[col].str.lower()
    
    # 2. NUMERIC CONVERSION: Convert strings to numbers (if it fails -> NaN)
    for col in NUMERIC_COLUMNS:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
     # 3. CATEGORICAL MISSING VALUES: Only fill categorical columns with 'Unknown'
    for col in CATEGORICAL_COLUMNS:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].fillna('Unknown')
    
    # 4. DATE FORMAT: Try to convert (if fails -> NaT/Null)
    for col in DATE_COLUMNS:
        if col in df_clean.columns:
            df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')
    
    # 5. DUPLICATES: This is the only safe "deletion" of data
    if 'id' in df_clean.columns:
        df_clean = df_clean.drop_duplicates(subset=['id'], keep='first')
    
    return df_clean

def generate_cleaning_summary(df_raw: pd.DataFrame, df_clean: pd.DataFrame) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append(f"CLEANING SUMMARY - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    
    # 1. Comparison between rows and columns
    lines.append(f"\n📊 Dataset Size:")
    lines.append(f"   - Raw rows: {len(df_raw):,}")
    lines.append(f"   - Clean rows: {len(df_clean):,}")
    
    # 2. Missing Values (Before vs After)
    raw_missing = df_raw.isnull().sum().sum()
    clean_missing = df_clean.isnull().sum().sum()
    lines.append(f"\n📊 Missing Values:")
    lines.append(f"   - Before cleaning: {raw_missing}")
    lines.append(f"   - After cleaning:  {clean_missing}")
    lines.append(f"   - ✅ Resolved:      {raw_missing - clean_missing}")
    
    # 3. Duplicate (Before vs After)
    raw_dupes = df_raw.duplicated().sum()
    clean_dupes = df_clean.duplicated().sum()
    lines.append(f"\n📊 Duplicate Rows:")
    lines.append(f"   - Before cleaning: {raw_dupes}")
    lines.append(f"   - After cleaning:  {clean_dupes}")
    lines.append(f"   - ✅ Removed:       {raw_dupes - clean_dupes}")
    
    # 4. Informations of cleaned columns
    lines.append(f"\n🧹 Cleaning Operations Applied:")
    lines.append(f"   - Text columns: stripped spaces, standardized casing")
    lines.append(f"   - Missing values (department): filled with 'Unknown'")
    lines.append(f"   - Numeric columns: converted to proper types (outliers preserved)")
    
    # 5. Outlier check in salary
    if 'salary' in df_clean.columns:
        outliers = df_clean[df_clean['salary'] < 0]
        if len(outliers) > 0:
            lines.append(f"\n⚠️ Outliers Still Present (Not Modified):")
            lines.append(f"   - Negative salaries found: {len(outliers)} rows")
            lines.append(f"   - (These require business review)")
    
    lines.append("\n" + "=" * 70)
    return "\n".join(lines)

#6. main
def main():    

    EXPECTED_SCHEMA = DEFAULT_SCHEMA
    PRIMARY_KEY = 'id'
    DATA_PATH = 'data/sample_data.csv'
    REPORTS_DIR = 'reports'

    try:
        df = pd.read_csv(DATA_PATH)
        logger.info(f"Data loaded: {len(df):,} rows, {len(df.columns)} columns")
    except FileNotFoundError:
        logger.error(f"File '{DATA_PATH}' not found. Run data_generator.py first.")
        exit(1)
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        exit(1)
    
    # Run quality check
    report, has_critical = check_data_quality(df, EXPECTED_SCHEMA, PRIMARY_KEY)
    
    # Save report
    os.makedirs(REPORTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d")
    report_path = f'{REPORTS_DIR}/data_quality_{timestamp}.txt'
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    logger.info(f"Report saved to: {report_path}")
    
    # Flag for email alert
    alert_path = f'{REPORTS_DIR}/alert_needed.txt'
    if has_critical:
        logger.warning("CRITICAL ISSUES DETECTED! Alert will be triggered.")
        with open(alert_path, 'w') as f:
            f.write("ALERT: Critical data quality issues detected.")
    else:
        logger.info("All checks passed! No critical issues.")
        if os.path.exists(alert_path):
            os.remove(alert_path)
    
    # Standardize data
    logger.info("Standardizing data format...")
    df_standardized = clean_data(df)
    
    # Save cleaned data
    os.makedirs('data/clean', exist_ok=True)
    clean_path = 'data/clean/sample_data_clean.csv'
    df_standardized.to_csv(clean_path, index=False)
    logger.info(f"Standardized data saved to: {clean_path}")
    
    # Generate and save cleaning summary
    cleaning_summary = generate_cleaning_summary(df, df_standardized)
    cleaning_report_path = f'{REPORTS_DIR}/cleaning_summary_{timestamp}.txt'
    
    with open(cleaning_report_path, 'w') as f:
        f.write(cleaning_summary)
    
    logger.info(f"Cleaning summary saved to: {cleaning_report_path}")
    
    logger.info("Quality check pipeline completed successfully!")


if __name__ == "__main__":
    main()
