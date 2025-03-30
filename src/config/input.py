import os
import pandas as pd
import pandera as pa
from enum import Enum
from pathlib import Path
from typing import Callable
from dotenv import load_dotenv
from src.config.app import AppConfig
from src.config.config_validator import (
    validate_required_vars,
    validate_file_exists,
    validate_value_is_allowed,
)


load_dotenv()


class InputFileSpecs:
    """
    Defines the complete specification for input data file.
    """

    class ColumnNames(Enum):
        """
        Standardized column names for input files.
        """

        ID = "id"
        ADDRESS = "address"

        def __str__(self):
            return self.value

    class ValidationSchema(pa.DataFrameModel):
        """
        Pandera data validation schema.
        """

        id: pa.typing.Series[str] = pa.Field(unique=True, coerce=True)
        address: pa.typing.Series[str] = pa.Field(nullable=False)

    class SupportedFormats(Enum):
        """
        Supported file formats with their corresponding pandas readers.
        """

        CSV = "csv"
        PARQUET = "parquet"

        def __str__(self):
            return self.value

        @property
        def reader(self) -> Callable:
            """
            Returns the appropriate pandas reader function for this format.
            """
            readers = {
                InputFileSpecs.SupportedFormats.CSV: pd.read_csv,
                InputFileSpecs.SupportedFormats.PARQUET: pd.read_parquet,
            }
            return readers[self]


class InputFileConfig:
    """
    Handles input file configuration and validation.
    """

    def __init__(self, app_config: AppConfig):
        self.app_dir = app_config.directory_manager
        self.filename: str = os.getenv("INPUT_FILENAME")
        self.file_format: str = os.getenv("INPUT_FILE_FORMAT")
        self.file_path: Path = self._get_input_file_path()
        self.column: InputFileSpecs.ColumnNames = InputFileSpecs.ColumnNames

        self.__post_init__()

    def __post_init__(self):
        validate_required_vars({"INPUT_FILENAME": self.filename})
        validate_value_is_allowed(
            self.file_format, [ft.name for ft in InputFileSpecs.SupportedFormats]
        )
        validate_file_exists(self._get_input_file_path())

    def _get_file_extension(self) -> str:
        """
        Returns the file extension based on the input file format.
        """
        return f".{str(InputFileSpecs.SupportedFormats[self.file_format])}"

    def _get_input_file_path(self) -> Path:
        """
        Returns input file path.
        """
        return (
            self.app_dir.get_directory_path(self.app_dir.directory.INPUT_DATA)
            / f"{self.filename}{self._get_file_extension()}"
        )

    def read_input_file(self) -> pd.DataFrame:
        """
        Reads and returns the input file as a pandas DataFrame.
        """

        try:
            file_format = InputFileSpecs.SupportedFormats[self.file_format]
            df = file_format.reader(self.file_path)
            InputFileSpecs.ValidationSchema.validate(df)
            return df
        except Exception as e:
            raise IOError(f"Failed to read input file : {e}")
