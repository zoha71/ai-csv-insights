"""Validate and load CSV uploads without changing the original data."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from src.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES


@dataclass
class LoadResult:
    dataframe: pd.DataFrame | None
    error: str | None
    filename: str
    encoding_used: str | None = None


def _extension_ok(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def _read_with_encodings(raw: bytes) -> tuple[pd.DataFrame | None, str | None, str | None]:
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            df = pd.read_csv(BytesIO(raw), encoding=encoding)
            return df, encoding, None
        except UnicodeDecodeError as exc:
            last_error = f"Could not decode the file as text ({exc})."
        except pd.errors.EmptyDataError:
            return None, encoding, "The CSV file is empty. Please upload a file that has a header and at least one row."
        except pd.errors.ParserError as exc:
            return None, encoding, f"The CSV file could not be parsed. Details: {exc}"
        except Exception as exc:  # noqa: BLE001 — show a friendly message to beginners
            last_error = f"The CSV file could not be read. Details: {exc}"
    return None, None, last_error or "The CSV file could not be read."


def load_csv_bytes(raw: bytes, filename: str) -> LoadResult:
    """Load a CSV from raw bytes. Returns the original DataFrame copy, never edited in place."""
    if not filename:
        return LoadResult(None, "Please choose a file first.", filename)

    if not _extension_ok(filename):
        return LoadResult(
            None,
            "Only CSV files are allowed. Please upload a file that ends with .csv.",
            filename,
        )

    if len(raw) == 0:
        return LoadResult(None, "The uploaded file is empty.", filename)

    if len(raw) > MAX_UPLOAD_BYTES:
        size_mb = MAX_UPLOAD_BYTES / (1024 * 1024)
        return LoadResult(
            None,
            f"The file is too large. Please upload a CSV smaller than {size_mb:.0f} MB.",
            filename,
        )

    df, encoding, error = _read_with_encodings(raw)
    if error:
        return LoadResult(None, error, filename, encoding)

    if df is None:
        return LoadResult(None, "The CSV file could not be read.", filename, encoding)

    if df.shape[1] == 0:
        return LoadResult(None, "The CSV has no columns. Please check the file and try again.", filename, encoding)

    if df.shape[0] == 0:
        return LoadResult(
            None,
            "The CSV has column names but no data rows. Please upload a file with at least one row of data.",
            filename,
            encoding,
        )

    # Independent copy so later analysis cannot change the uploaded original.
    return LoadResult(df.copy(), None, filename, encoding)


def load_csv_file(file_obj: BinaryIO, filename: str) -> LoadResult:
    raw = file_obj.read()
    return load_csv_bytes(raw, filename)


def load_csv_path(path: str | Path) -> LoadResult:
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return LoadResult(None, f"Could not open the file: {exc}", path.name)
    return load_csv_bytes(raw, path.name)


def dataset_overview(df: pd.DataFrame) -> dict:
    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": list(df.columns),
        "dtypes": dtypes,
    }
