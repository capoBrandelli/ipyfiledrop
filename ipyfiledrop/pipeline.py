"""
Data Import Pipeline for ipyfiledrop

Provides intelligent extraction, cleaning, and combination of DataFrames
from messy CSV/Excel files with headers, footers, and sparse regions.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import re
import pandas as pd
import numpy as np


@dataclass
class ExtractedData:
    """Result of core data extraction from a messy DataFrame."""
    core: pd.DataFrame                         # Main data table
    metadata: Dict[str, Any] = field(default_factory=dict)  # Key-value metadata
    header_row: Optional[int] = None           # Original header row index
    data_range: Tuple[int, int] = (0, 0)       # (start, end) row indices
    footer: List[str] = field(default_factory=list)  # Footer content
    confidence: float = 0.0                    # 0-1 quality score
    warnings: List[str] = field(default_factory=list)  # Issues detected


# =============================================================================
# Density Analysis Functions
# =============================================================================

def _is_empty(value) -> bool:
    """Check if a cell value is empty (NaN, None, or empty string)."""
    if pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == '':
        return True
    return False


def calculate_row_density(row: pd.Series) -> float:
    """
    Calculate the fraction of non-empty cells in a row.
    
    Args:
        row: A pandas Series representing a row
        
    Returns:
        Float between 0 and 1 representing density
    """
    if len(row) == 0:
        return 0.0
    non_empty = sum(1 for v in row if not _is_empty(v))
    return non_empty / len(row)


def calculate_column_density(col: pd.Series) -> float:
    """
    Calculate the fraction of non-empty cells in a column.
    
    Args:
        col: A pandas Series representing a column
        
    Returns:
        Float between 0 and 1 representing density
    """
    if len(col) == 0:
        return 0.0
    non_empty = sum(1 for v in col if not _is_empty(v))
    return non_empty / len(col)


# =============================================================================
# Region Detection
# =============================================================================

def find_dense_region(df: pd.DataFrame, threshold: float = 0.4) -> Tuple[int, int]:
    """
    Find the first and last rows that form a contiguous dense region.
    
    A dense region is a set of contiguous rows where each has density >= threshold.
    
    Args:
        df: Input DataFrame
        threshold: Minimum density for a row to be considered dense
        
    Returns:
        Tuple of (start_row, end_row) indices (inclusive)
    """
    if df.empty:
        return (0, 0)
    
    row_densities = [calculate_row_density(df.iloc[i]) for i in range(len(df))]
    
    # Find first dense row
    start_row = None
    for i, density in enumerate(row_densities):
        if density >= threshold:
            start_row = i
            break
    
    if start_row is None:
        return (0, 0)
    
    # Find last dense row (allowing small gaps for empty rows within data)
    end_row = start_row
    gap_count = 0
    max_gap = 2  # Allow up to 2 consecutive sparse rows within data
    
    for i in range(start_row, len(row_densities)):
        if row_densities[i] >= threshold:
            end_row = i
            gap_count = 0
        else:
            gap_count += 1
            if gap_count > max_gap:
                break
    
    return (start_row, end_row)


def find_dense_columns(df: pd.DataFrame, row_start: int, row_end: int, 
                       threshold: float = 0.3) -> List[int]:
    """
    Find columns with sufficient density within the specified row range.
    
    Args:
        df: Input DataFrame
        row_start: Start row index (inclusive)
        row_end: End row index (inclusive)
        threshold: Minimum density for a column to be included
        
    Returns:
        List of column indices that are dense enough
    """
    if df.empty or row_start > row_end:
        return []
    
    # Slice to the relevant rows
    region = df.iloc[row_start:row_end + 1]
    
    dense_cols = []
    for col_idx in range(len(df.columns)):
        col = region.iloc[:, col_idx]
        density = calculate_column_density(col)
        if density >= threshold:
            dense_cols.append(col_idx)
    
    return dense_cols


# =============================================================================
# Header Detection
# =============================================================================

def _is_likely_header_cell(value) -> bool:
    """Check if a cell value looks like a header (string, not numeric pattern)."""
    if _is_empty(value):
        return False
    val_str = str(value).strip()
    # Numeric values or IDs are not headers
    if re.match(r'^[\d\.\-\+]+$', val_str):
        return False
    # Very short values might be codes, not headers
    if len(val_str) <= 1:
        return False
    return True


def _is_data_cell(value) -> bool:
    """Check if a cell value looks like data (ID patterns, numbers, etc.)."""
    if _is_empty(value):
        return False
    val_str = str(value).strip()
    # ID patterns like SAMP-001, ABC123, etc.
    if re.match(r'^[A-Z]{2,}-\d+$', val_str):
        return True
    # Pure numbers
    if re.match(r'^[\d\.\-\+]+$', val_str):
        return True
    return False


def _looks_like_row_number(col: pd.Series, start_row: int, end_row: int) -> bool:
    """
    Check if a column looks like row numbers (sequential integers starting from 1 or 0).
    """
    values = []
    for i in range(start_row, min(end_row + 1, len(col))):
        v = col.iloc[i]
        if not _is_empty(v):
            try:
                values.append(int(float(str(v).strip())))
            except (ValueError, TypeError):
                return False
    
    if len(values) < 3:
        return False
    
    # Check if it's sequential (allowing some gaps)
    expected_start = values[0]
    sequential_count = 0
    for i, v in enumerate(values):
        if v == expected_start + i:
            sequential_count += 1
    
    return sequential_count / len(values) >= 0.7


def detect_header_row(df: pd.DataFrame, search_start: int, search_end: int) -> Optional[int]:
    """
    Detect which row is most likely the header within the given range.
    
    Headers typically:
    - Have mostly string values (not numbers)
    - Have high density
    - Are followed by rows with different (more numeric) patterns
    - Do NOT contain ID patterns like "SAMP-001"
    
    Args:
        df: Input DataFrame
        search_start: Start of search range
        search_end: End of search range
        
    Returns:
        Row index of detected header, or None if not found
    """
    if df.empty:
        return None
    
    best_header = None
    best_score = -1
    
    for row_idx in range(search_start, min(search_end + 1, len(df))):
        row = df.iloc[row_idx]
        non_empty_cells = [v for v in row if not _is_empty(v)]
        
        if len(non_empty_cells) < 2:
            continue
        
        # Strong penalty if row contains data-like values (IDs, mostly numbers)
        data_like_count = sum(1 for v in non_empty_cells if _is_data_cell(v))
        data_ratio = data_like_count / len(non_empty_cells)
        if data_ratio > 0.3:
            # This row looks like data, not a header
            continue
        
        # Score based on how "header-like" the row is
        header_like_count = sum(1 for v in non_empty_cells if _is_likely_header_cell(v))
        header_ratio = header_like_count / len(non_empty_cells)
        
        # Check if values are unique (headers usually have unique column names)
        str_values = [str(v).strip().lower() for v in non_empty_cells]
        unique_ratio = len(set(str_values)) / len(str_values)
        
        # Bonus: check if following row contains data patterns (IDs or numbers)
        data_follows_bonus = 0
        if row_idx + 1 < len(df):
            next_row = df.iloc[row_idx + 1]
            next_non_empty = [v for v in next_row if not _is_empty(v)]
            if next_non_empty:
                data_in_next = sum(1 for v in next_non_empty if _is_data_cell(v))
                if data_in_next / len(next_non_empty) > 0.2:
                    data_follows_bonus = 0.4
        
        # Prefer rows with more non-empty cells
        density_bonus = len(non_empty_cells) / len(row) * 0.2
        
        score = (header_ratio * 0.4) + (unique_ratio * 0.2) + data_follows_bonus + density_bonus
        
        if score > best_score:
            best_score = score
            best_header = row_idx
    
    return best_header


# =============================================================================
# Metadata and Footer Extraction
# =============================================================================

def extract_metadata(df: pd.DataFrame, end_row: int) -> Dict[str, Any]:
    """
    Extract key-value metadata from rows above the header.
    
    Looks for patterns like:
    - "Key: Value" in a single cell
    - Key in column A, Value in column B
    - "Key = Value" format
    
    Args:
        df: Input DataFrame
        end_row: Row index up to which to search for metadata (exclusive)
        
    Returns:
        Dictionary of extracted metadata
    """
    metadata = {}
    
    for row_idx in range(min(end_row, len(df))):
        row = df.iloc[row_idx]
        # Filter out cells that look like row numbers (small integers in first few columns)
        non_empty = []
        for i, v in enumerate(row):
            if _is_empty(v):
                continue
            # Skip likely row number cells (small int in column 0)
            if i == 0:
                try:
                    val = int(float(str(v).strip()))
                    if 0 <= val <= 1000:  # Looks like a row number
                        continue
                except (ValueError, TypeError):
                    pass
            non_empty.append((i, v))
        
        if len(non_empty) == 0:
            continue
        
        # Pattern 1: Single cell with "Key: Value" or "Key = Value"
        if len(non_empty) == 1:
            _, val = non_empty[0]
            val_str = str(val).strip()
            # Try colon pattern
            match = re.match(r'^([^:]+):\s*(.+)$', val_str)
            if match:
                metadata[match.group(1).strip()] = match.group(2).strip()
                continue
            # Try equals pattern
            match = re.match(r'^([^=]+)=\s*(.+)$', val_str)
            if match:
                metadata[match.group(1).strip()] = match.group(2).strip()
                continue
        
        # Pattern 2: Key in one column, Value in adjacent column
        if len(non_empty) == 2:
            idx1, val1 = non_empty[0]
            idx2, val2 = non_empty[1]
            # Check if they're adjacent or near each other
            if abs(idx2 - idx1) <= 2:
                key = str(val1).strip()
                value = str(val2).strip()
                # Key should look like a label (not a number)
                if not re.match(r'^[\d\.\-\+]+$', key) and len(key) > 1:
                    metadata[key] = value
                    continue
        
        # Pattern 3: Multiple pairs in a row (less common)
        if len(non_empty) >= 4 and len(non_empty) % 2 == 0:
            # Try to extract pairs
            for i in range(0, len(non_empty), 2):
                if i + 1 < len(non_empty):
                    _, key = non_empty[i]
                    _, value = non_empty[i + 1]
                    key_str = str(key).strip()
                    if not re.match(r'^[\d\.\-\+]+$', key_str) and len(key_str) > 1:
                        metadata[key_str] = str(value).strip()
    
    return metadata


def extract_footer(df: pd.DataFrame, start_row: int) -> List[str]:
    """
    Extract footer content from rows after the main data.
    
    Args:
        df: Input DataFrame
        start_row: Row index from which to start extracting footer
        
    Returns:
        List of non-empty footer strings
    """
    footer = []
    
    for row_idx in range(start_row, len(df)):
        row = df.iloc[row_idx]
        non_empty = []
        for i, v in enumerate(row):
            if _is_empty(v):
                continue
            # Skip likely row number cells (small int in column 0)
            if i == 0:
                try:
                    val = int(float(str(v).strip()))
                    if 0 <= val <= 1000:  # Looks like a row number
                        continue
                except (ValueError, TypeError):
                    pass
            non_empty.append(str(v).strip())
        
        if non_empty:
            # Join non-empty values from the row
            footer_line = ' '.join(non_empty)
            footer.append(footer_line)
    
    return footer


# =============================================================================
# Main Extraction Function
# =============================================================================

def extract_core_data(df: pd.DataFrame, density_threshold: float = 0.4) -> ExtractedData:
    """
    Extract core data table from a messy DataFrame.
    
    This function analyzes the DataFrame to find the main data table,
    separating it from metadata headers and footer rows.
    
    Args:
        df: Input DataFrame (typically loaded with header=None)
        density_threshold: Minimum row density to be considered part of core data
        
    Returns:
        ExtractedData object containing:
        - core: The cleaned data table
        - metadata: Extracted key-value metadata
        - header_row: Original row index of the detected header
        - data_range: (start, end) row indices of data
        - footer: Extracted footer content
        - confidence: Quality score (0-1)
        - warnings: List of any issues detected
    """
    warnings = []
    
    if df.empty:
        return ExtractedData(
            core=df.copy(),
            confidence=0.0,
            warnings=["Empty DataFrame provided"]
        )
    
    # Step 1: Find dense region
    dense_start, dense_end = find_dense_region(df, density_threshold)
    
    if dense_start == dense_end == 0 and not calculate_row_density(df.iloc[0]) >= density_threshold:
        warnings.append("No dense region found; returning entire DataFrame")
        return ExtractedData(
            core=df.copy(),
            confidence=0.3,
            warnings=warnings
        )
    
    # Step 2: Detect header row
    header_row = detect_header_row(df, dense_start, min(dense_start + 3, dense_end))
    
    if header_row is None:
        header_row = dense_start
        warnings.append("Could not detect header row; using first dense row")
    
    # Step 3: Find dense columns within the data region
    data_start = header_row + 1 if header_row < dense_end else header_row
    dense_cols = find_dense_columns(df, data_start, dense_end, threshold=0.3)
    
    if not dense_cols:
        dense_cols = list(range(len(df.columns)))
        warnings.append("No dense columns found; using all columns")
    
    # Step 4: Check for row number column and exclude it
    first_col = df.iloc[:, dense_cols[0]] if dense_cols else None
    if first_col is not None and _looks_like_row_number(first_col, data_start, dense_end):
        dense_cols = dense_cols[1:]
        if not dense_cols:
            dense_cols = list(range(1, len(df.columns)))
    
    # Step 5: Extract metadata from rows above header
    metadata = extract_metadata(df, header_row)
    
    # Step 6: Extract footer from rows after dense region
    footer = extract_footer(df, dense_end + 1) if dense_end + 1 < len(df) else []
    
    # Step 7: Slice core data
    # Get header names
    if header_row is not None:
        header_values = df.iloc[header_row, dense_cols].tolist()
        # Clean header values
        header_values = [
            str(v).strip() if not _is_empty(v) else f'col_{i}'
            for i, v in enumerate(header_values)
        ]
    else:
        header_values = [f'col_{i}' for i in range(len(dense_cols))]
    
    # Extract data rows (after header, up to dense_end)
    data_start_row = header_row + 1 if header_row is not None else dense_start
    core_data = df.iloc[data_start_row:dense_end + 1, dense_cols].copy()
    core_data.columns = header_values
    core_data = core_data.reset_index(drop=True)
    
    # Step 8: Calculate confidence score
    confidence = _calculate_confidence(
        df, core_data, header_row, data_start_row, dense_end, dense_cols, warnings
    )
    
    return ExtractedData(
        core=core_data,
        metadata=metadata,
        header_row=header_row,
        data_range=(data_start_row, dense_end),
        footer=footer,
        confidence=confidence,
        warnings=warnings
    )


def _calculate_confidence(df: pd.DataFrame, core: pd.DataFrame,
                          header_row: Optional[int], data_start: int, 
                          data_end: int, dense_cols: List[int],
                          warnings: List[str]) -> float:
    """Calculate a confidence score for the extraction."""
    score = 1.0
    
    # Penalty for warnings
    score -= len(warnings) * 0.1
    
    # Bonus for finding metadata
    # (implicit in no warnings about header)
    
    # Check core data density
    if not core.empty:
        avg_density = sum(calculate_row_density(core.iloc[i]) for i in range(len(core))) / len(core)
        score *= (0.5 + avg_density * 0.5)
    
    # Check that we extracted a reasonable portion of the data
    if len(df) > 0:
        extraction_ratio = len(core) / len(df)
        if extraction_ratio < 0.1:
            score -= 0.2
        elif extraction_ratio > 0.8:
            score += 0.1
    
    # Check header quality
    if core.columns.tolist():
        default_col_count = sum(1 for c in core.columns if str(c).startswith('col_'))
        if default_col_count / len(core.columns) > 0.5:
            score -= 0.15
    
    return max(0.0, min(1.0, score))


# =============================================================================
# Cleaning Functions
# =============================================================================

def normalize_columns(df: pd.DataFrame, filename: Optional[str] = None, 
                       *, preserve_case: bool = False,
                       preserve_dashes: bool = False,
                       preserve_dots: bool = False) -> pd.DataFrame:
    """
    Normalize column names: strip, replace spaces/special chars with underscore.
    
    Args:
        df: Input DataFrame
        filename: Optional filename (unused, for cleaner signature consistency)
        preserve_case: If True, preserve original case. If False (default), convert to lowercase.
        preserve_dashes: If True, keep dashes (-) instead of replacing with underscore.
        preserve_dots: If True, keep dots (.) instead of replacing with underscore.
        
    Returns:
        DataFrame with normalized column names
        
    Example:
        >>> normalize_columns(df)  # lowercase, all special chars -> _
        >>> normalize_columns(df, preserve_case=True)  # keep original case
        >>> normalize_columns(df, preserve_dashes=True)  # keep dashes: Sample-ID
        >>> normalize_columns(df, preserve_dots=True)  # keep dots: v1.2
    """
    df = df.copy()
    new_columns = []
    for col in df.columns:
        col_str = str(col).strip()
        if not preserve_case:
            col_str = col_str.lower()
        
        # Build regex pattern for characters to replace
        # \w matches [a-zA-Z0-9_], we want to replace everything else
        # But preserve dashes/dots if requested
        preserve_chars = ''
        if preserve_dashes:
            preserve_chars += '-'
        if preserve_dots:
            preserve_chars += '.'
        
        if preserve_chars:
            # Escape special regex chars and build pattern
            escaped = re.escape(preserve_chars)
            pattern = r'[^\w' + escaped + r']+'
        else:
            pattern = r'[^\w]+'
        
        col_str = re.sub(pattern, '_', col_str)
        # Remove leading/trailing underscores
        col_str = col_str.strip('_')
        # Handle empty column names
        if not col_str:
            col_str = 'unnamed'
        new_columns.append(col_str)
    
    # Handle duplicate column names
    seen = {}
    final_columns = []
    for col in new_columns:
        if col in seen:
            seen[col] += 1
            final_columns.append(f'{col}_{seen[col]}')
        else:
            seen[col] = 0
            final_columns.append(col)
    
    df.columns = final_columns
    return df


def make_normalize_columns(preserve_case: bool = False,
                           preserve_dashes: bool = False,
                           preserve_dots: bool = False) -> Callable[[pd.DataFrame, Optional[str]], pd.DataFrame]:
    """
    Factory function to create a normalize_columns cleaner with custom settings.
    
    Args:
        preserve_case: If True, preserve original case. If False, convert to lowercase.
        preserve_dashes: If True, keep dashes (-) instead of replacing with underscore.
        preserve_dots: If True, keep dots (.) instead of replacing with underscore.
        
    Returns:
        A cleaner function with the standard (df, filename) signature.
        
    Example:
        >>> fd = FileDrop("Data", cleaners=[make_normalize_columns(preserve_case=True)])
        >>> fd = FileDrop("Data", cleaners=[make_normalize_columns(preserve_dashes=True)])
    """
    def cleaner(df: pd.DataFrame, filename: Optional[str] = None) -> pd.DataFrame:
        return normalize_columns(df, filename, 
                                 preserve_case=preserve_case,
                                 preserve_dashes=preserve_dashes,
                                 preserve_dots=preserve_dots)
    # Build descriptive name
    opts = []
    if preserve_case:
        opts.append('preserve_case=True')
    if preserve_dashes:
        opts.append('preserve_dashes=True')
    if preserve_dots:
        opts.append('preserve_dots=True')
    cleaner.__name__ = f'normalize_columns({", ".join(opts)})' if opts else 'normalize_columns()'
    return cleaner


def strip_whitespace(df: pd.DataFrame, filename: Optional[str] = None,
                      *, normalize_inner: bool = False) -> pd.DataFrame:
    """
    Strip leading/trailing whitespace from string values.
    
    Args:
        df: Input DataFrame
        filename: Optional filename (unused)
        normalize_inner: If True, also collapse multiple inner spaces to single space.
                        If False (default), only strip edges, preserve inner whitespace.
        
    Returns:
        DataFrame with stripped string values
        
    Example:
        >>> strip_whitespace(df)  # "  hello   world  " -> "hello   world"
        >>> strip_whitespace(df, normalize_inner=True)  # "  hello   world  " -> "hello world"
    """
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object:
            if normalize_inner:
                # Strip edges and collapse inner whitespace
                df[col] = df[col].apply(
                    lambda x: ' '.join(x.split()) if isinstance(x, str) else x
                )
            else:
                # Only strip edges
                df[col] = df[col].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )
    return df


def make_strip_whitespace(normalize_inner: bool = False) -> Callable[[pd.DataFrame, Optional[str]], pd.DataFrame]:
    """
    Factory function to create a strip_whitespace cleaner with custom settings.
    
    Args:
        normalize_inner: If True, collapse multiple inner spaces to single space.
        
    Returns:
        A cleaner function with the standard (df, filename) signature.
        
    Example:
        >>> fd = FileDrop("Data", cleaners=[make_strip_whitespace(normalize_inner=True)])
    """
    def cleaner(df: pd.DataFrame, filename: Optional[str] = None) -> pd.DataFrame:
        return strip_whitespace(df, filename, normalize_inner=normalize_inner)
    cleaner.__name__ = f'strip_whitespace(normalize_inner={normalize_inner})'
    return cleaner


def drop_empty_rows(df: pd.DataFrame, filename: Optional[str] = None) -> pd.DataFrame:
    """
    Remove rows where all values are NaN or empty.
    
    Args:
        df: Input DataFrame
        filename: Optional filename (unused)
        
    Returns:
        DataFrame with empty rows removed
    """
    df = df.copy()
    
    # Create mask: True for rows that have at least one non-empty value
    def row_has_data(row):
        return any(not _is_empty(v) for v in row)
    
    mask = df.apply(row_has_data, axis=1)
    return df[mask].reset_index(drop=True)


def drop_empty_cols(df: pd.DataFrame, filename: Optional[str] = None) -> pd.DataFrame:
    """
    Remove columns where all values are NaN or empty.
    
    Args:
        df: Input DataFrame
        filename: Optional filename (unused)
        
    Returns:
        DataFrame with empty columns removed
    """
    df = df.copy()
    
    cols_to_keep = []
    for col in df.columns:
        if any(not _is_empty(v) for v in df[col]):
            cols_to_keep.append(col)
    
    return df[cols_to_keep]


def standardize_na(df: pd.DataFrame, filename: Optional[str] = None) -> pd.DataFrame:
    """
    Convert common NA representations to NaN.
    
    Converts: "N/A", "n/a", "NA", "na", "-", "null", "NULL", "None", ""
    
    Args:
        df: Input DataFrame
        filename: Optional filename (unused)
        
    Returns:
        DataFrame with standardized NA values
    """
    df = df.copy()
    na_values = {'n/a', 'na', 'N/A', 'NA', '-', 'null', 'NULL', 'None', 'none', ''}
    
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].apply(
                lambda x: np.nan if isinstance(x, str) and x.strip() in na_values else x
            )
    return df


def deduplicate(df: pd.DataFrame, filename: Optional[str] = None) -> pd.DataFrame:
    """
    Remove duplicate rows.
    
    Args:
        df: Input DataFrame
        filename: Optional filename (unused)
        
    Returns:
        DataFrame with duplicate rows removed
    """
    return df.drop_duplicates().reset_index(drop=True)


def infer_types(df: pd.DataFrame, filename: Optional[str] = None) -> pd.DataFrame:
    """
    Infer and convert column types (numeric, datetime).
    
    Args:
        df: Input DataFrame
        filename: Optional filename (unused)
        
    Returns:
        DataFrame with inferred types
    """
    df = df.copy()
    
    for col in df.columns:
        if df[col].dtype == object:
            # Try numeric conversion
            try:
                numeric_col = pd.to_numeric(df[col], errors='coerce')
                # Only convert if at least 50% could be converted
                valid_ratio = numeric_col.notna().sum() / len(numeric_col) if len(numeric_col) > 0 else 0
                if valid_ratio >= 0.5:
                    df[col] = numeric_col
                    continue
            except (ValueError, TypeError):
                pass
            
            # Try datetime conversion
            try:
                datetime_col = pd.to_datetime(df[col], errors='coerce')
                non_null_count = datetime_col.notna().sum()
                total_count = len(datetime_col)
                valid_ratio = non_null_count / total_count if total_count > 0 else 0
                if valid_ratio >= 0.5:
                    df[col] = datetime_col
                    continue
            except (ValueError, TypeError):
                pass
    
    return df


# Cleaning presets
CLEANING_PRESETS: Dict[str, List[Callable]] = {
    "none": [],
    "minimal": [
        normalize_columns,
        strip_whitespace,
    ],
    "standard": [
        normalize_columns,
        strip_whitespace,
        drop_empty_rows,
        standardize_na,
    ],
    "aggressive": [
        normalize_columns,
        strip_whitespace,
        drop_empty_rows,
        drop_empty_cols,
        standardize_na,
        deduplicate,
        infer_types,
    ],
}


def apply_cleaners(df: pd.DataFrame, cleaners: List[Callable], 
                   filename: Optional[str] = None) -> pd.DataFrame:
    """
    Apply a list of cleaner functions to a DataFrame.
    
    Args:
        df: Input DataFrame
        cleaners: List of cleaner functions (each takes df and optional filename)
        filename: Optional filename to pass to cleaners
        
    Returns:
        Cleaned DataFrame
    """
    result = df.copy()
    for cleaner in cleaners:
        result = cleaner(result, filename)
    return result


def clean_dataframe(df: pd.DataFrame, 
                    preset: Optional[str] = None,
                    cleaners: Optional[List[Callable]] = None,
                    cleaner: Optional[Callable] = None,
                    filename: Optional[str] = None) -> pd.DataFrame:
    """
    Clean a DataFrame using presets, custom cleaners, or a single cleaner function.
    
    Args:
        df: Input DataFrame
        preset: Name of preset ("none", "minimal", "standard", "aggressive")
        cleaners: List of cleaner functions to apply in order
        cleaner: Single custom cleaner function
        filename: Optional filename to pass to cleaners
        
    Returns:
        Cleaned DataFrame
    """
    if cleaner is not None:
        return cleaner(df, filename)
    
    if cleaners is not None:
        return apply_cleaners(df, cleaners, filename)
    
    if preset is not None:
        if preset not in CLEANING_PRESETS:
            raise ValueError(f"Unknown preset: {preset}. Available: {list(CLEANING_PRESETS.keys())}")
        return apply_cleaners(df, CLEANING_PRESETS[preset], filename)
    
    # Default to standard preset
    return apply_cleaners(df, CLEANING_PRESETS["standard"], filename)


# =============================================================================
# Combine Function
# =============================================================================

def combine_dataframes(
    data: Dict[str, pd.DataFrame],
    add_source: bool = False,
    ignore_index: bool = True,
    metadata: Optional[Dict[str, Dict[str, Any]]] = None,
    include_metadata: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Combine multiple DataFrames into one.
    
    Args:
        data: Dictionary mapping filenames to DataFrames
        add_source: If True, add '_source' column with original filename
        ignore_index: If True, reset index after concatenation
        metadata: Dictionary mapping filenames to their metadata dicts
        include_metadata: List of metadata keys to include as columns (prefixed with '_')
        
    Returns:
        Combined DataFrame
    """
    if not data:
        return pd.DataFrame()
    
    frames = []
    
    for filename, df in data.items():
        frame = df.copy()
        
        # Add source column if requested
        if add_source:
            frame['_source'] = filename
        
        # Add metadata columns if requested
        if include_metadata and metadata and filename in metadata:
            file_metadata = metadata[filename]
            for key in include_metadata:
                col_name = f'_{key}'
                if key in file_metadata:
                    frame[col_name] = file_metadata[key]
                else:
                    frame[col_name] = np.nan
        
        frames.append(frame)
    
    # Concatenate all frames
    result = pd.concat(frames, ignore_index=ignore_index)
    
    return result
