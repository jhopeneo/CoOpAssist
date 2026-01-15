"""
Excel and CSV document loader for QmanAssist.
Uses pandas to extract and structure tabular data.
Supports both local files and SMB network shares.
"""

from pathlib import Path
from typing import List
from loguru import logger
import pandas as pd
import smbclient
import io

from .base_loader import BaseDocumentLoader, Document


class ExcelLoader(BaseDocumentLoader):
    """Loader for Excel and CSV files."""

    def __init__(
        self,
        file_path: Path,
        generate_descriptions: bool = True,
        max_rows_per_chunk: int = 50,
    ):
        """Initialize Excel/CSV loader.

        Args:
            file_path: Path to Excel or CSV file.
            generate_descriptions: Whether to generate natural language descriptions.
            max_rows_per_chunk: Maximum rows to include in a single document chunk.
        """
        super().__init__(file_path)
        self.generate_descriptions = generate_descriptions
        self.max_rows_per_chunk = max_rows_per_chunk

    def get_supported_extensions(self) -> List[str]:
        """Get supported file extensions."""
        return [".xlsx", ".xls", ".xlsm", ".csv", ".XLSX", ".XLS", ".XLSM", ".CSV"]

    def load(self) -> List[Document]:
        """Load Excel/CSV file and extract data.

        Returns:
            List of Document objects (one per sheet or chunk).
        """
        documents = []

        try:
            extension = self.file_path.suffix.lower()

            if extension == ".csv":
                documents = self._load_csv()
            else:
                documents = self._load_excel()

            logger.info(f"Loaded {len(documents)} chunks from {self.file_path.name}")
            return documents

        except Exception as e:
            logger.error(f"Error loading Excel/CSV {self.file_path}: {e}")
            raise

    def _load_csv(self) -> List[Document]:
        """Load CSV file.

        Returns:
            List of Document objects.
        """
        base_metadata = self._get_base_metadata()
        base_metadata["doc_type"] = "csv"

        # Check if it's an SMB path
        path_str = str(self.file_path)
        if path_str.startswith("//") or path_str.startswith("\\\\"):
            # Read from SMB into memory
            smb_path = path_str.replace("//", "\\\\").replace("/", "\\")
            with smbclient.open_file(smb_path, mode="rb") as smb_file:
                df = pd.read_csv(io.BytesIO(smb_file.read()))
        else:
            # Read local CSV
            df = pd.read_csv(self.file_path)

        # Create documents from chunks
        documents = self._dataframe_to_documents(
            df, sheet_name="data", base_metadata=base_metadata
        )

        return documents

    def _load_excel(self) -> List[Document]:
        """Load Excel file (all sheets).

        Returns:
            List of Document objects.
        """
        documents = []
        base_metadata = self._get_base_metadata()
        base_metadata["doc_type"] = "excel"

        # Check if it's an SMB path
        path_str = str(self.file_path)
        if path_str.startswith("//") or path_str.startswith("\\\\"):
            # Read from SMB into memory
            smb_path = path_str.replace("//", "\\\\").replace("/", "\\")
            with smbclient.open_file(smb_path, mode="rb") as smb_file:
                excel_file = pd.ExcelFile(io.BytesIO(smb_file.read()))
        else:
            # Read local Excel file
            excel_file = pd.ExcelFile(self.file_path)
        base_metadata["sheet_count"] = len(excel_file.sheet_names)

        for sheet_name in excel_file.sheet_names:
            try:
                df = excel_file.parse(sheet_name)

                sheet_metadata = base_metadata.copy()
                sheet_metadata["sheet_name"] = sheet_name

                # Create documents from this sheet
                sheet_docs = self._dataframe_to_documents(
                    df, sheet_name=sheet_name, base_metadata=sheet_metadata
                )

                documents.extend(sheet_docs)

            except Exception as e:
                logger.warning(f"Error loading sheet '{sheet_name}': {e}")
                continue

        return documents

    def _dataframe_to_documents(
        self, df: pd.DataFrame, sheet_name: str, base_metadata: dict
    ) -> List[Document]:
        """Convert DataFrame to Document objects.

        Args:
            df: pandas DataFrame.
            sheet_name: Name of the sheet/data source.
            base_metadata: Base metadata to include.

        Returns:
            List of Document objects.
        """
        documents = []

        if df.empty:
            logger.warning(f"Sheet '{sheet_name}' is empty")
            return documents

        # Clean column names
        df.columns = df.columns.astype(str)

        # Split into chunks if needed
        num_chunks = (len(df) + self.max_rows_per_chunk - 1) // self.max_rows_per_chunk

        for chunk_idx in range(num_chunks):
            start_row = chunk_idx * self.max_rows_per_chunk
            end_row = min(start_row + self.max_rows_per_chunk, len(df))

            chunk_df = df.iloc[start_row:end_row]

            # Generate content
            content = self._format_dataframe(chunk_df, sheet_name)

            # Add natural language description if requested
            if self.generate_descriptions:
                description = self._generate_description(chunk_df, sheet_name)
                content = description + "\n\n" + content

            # Create metadata
            metadata = base_metadata.copy()
            metadata.update({
                "row_start": start_row + 2,  # +2 for 1-indexed + header row
                "row_end": end_row + 2,
                "row_count": len(chunk_df),
                "column_count": len(chunk_df.columns),
                "columns": ", ".join(str(col) for col in chunk_df.columns),  # Convert to comma-separated string
                "chunk_index": chunk_idx,
                "total_chunks": num_chunks,
            })

            documents.append(Document(content=content, metadata=metadata))

        return documents

    def _format_dataframe(self, df: pd.DataFrame, sheet_name: str) -> str:
        """Format DataFrame as structured text.

        Args:
            df: pandas DataFrame.
            sheet_name: Name of the sheet.

        Returns:
            Formatted text representation.
        """
        lines = [f"Sheet: {sheet_name}", ""]

        # Add column headers
        headers = " | ".join(str(col) for col in df.columns)
        lines.append(f"Columns: {headers}")
        lines.append("")

        # Add rows
        for idx, row in df.iterrows():
            row_data = []
            for col in df.columns:
                value = row[col]
                if pd.isna(value):
                    value = ""
                row_data.append(f"{col}: {value}")

            row_text = " | ".join(row_data)
            lines.append(f"Row {idx + 2}: {row_text}")  # +2 for 1-indexed + header

        return "\n".join(lines)

    def _generate_description(self, df: pd.DataFrame, sheet_name: str) -> str:
        """Generate natural language description of the data.

        Args:
            df: pandas DataFrame.
            sheet_name: Name of the sheet.

        Returns:
            Natural language description.
        """
        description_parts = [
            f"This is data from the sheet '{sheet_name}'.",
            f"It contains {len(df)} rows and {len(df.columns)} columns.",
        ]

        # List columns
        col_list = ", ".join(str(col) for col in df.columns)
        description_parts.append(f"The columns are: {col_list}.")

        # Add summary statistics for numeric columns
        numeric_cols = df.select_dtypes(include=["number"]).columns
        if len(numeric_cols) > 0:
            description_parts.append("Numeric columns:")
            for col in numeric_cols:
                try:
                    mean_val = df[col].mean()
                    min_val = df[col].min()
                    max_val = df[col].max()
                    description_parts.append(
                        f"  - {col}: range {min_val:.2f} to {max_val:.2f}, average {mean_val:.2f}"
                    )
                except:
                    pass

        return " ".join(description_parts)
