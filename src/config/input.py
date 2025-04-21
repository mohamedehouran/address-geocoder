import pandas as pd
import pandera as pa
from enum import Enum
import multiprocessing
from pathlib import Path
from typing import Callable
from dataclasses import dataclass, field
from src.config.app import AppConfig
from src.config.config_validator import (
    validate_required_vars,
    validate_file_exists,
    validate_value_is_allowed,
    validate_positive_value,
)


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

    class ValidationSchema(pa.DataFrameModel):
        """
        Pandera data validation schema.
        """

        id: str = pa.Field(unique=True, coerce=True)
        address: str = pa.Field(coerce=True)

    class SupportedFormats(Enum):
        """
        Supported file formats with their corresponding pandas readers.
        """

        CSV = "csv"
        PARQUET = "parquet"

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


@dataclass
class InputFileConfig:
    """
    Handles input file configuration and validation.
    """

    filename: str
    file_format: str
    app_config: AppConfig
    file_specs: InputFileSpecs = InputFileSpecs
    file_path: Path = field(init=False)

    def __post_init__(self):
        self.dir_manager = self.app_config.directory_manager
        self.env_manager = self.app_config.environment_manager
        self.file_path = self._get_input_file_path()

        self._validate_config()

    def _validate_config(self):
        """
        Centralized configuration validation.
        """
        validate_required_vars(
            {self.env_manager.variables.INPUT_FILENAME: self.filename}
        )
        validate_value_is_allowed(
            self.file_format, [ff.name for ff in self.file_specs.SupportedFormats]
        )
        validate_file_exists(self.file_path)

    def _get_file_extension(self) -> str:
        """
        Returns the file extension based on the input file format.
        """
        return f".{InputFileSpecs.SupportedFormats[self.file_format].value}"

    def _get_input_file_path(self) -> Path:
        """
        Returns input file path.
        """
        return (
            self.dir_manager.get_directory_path(self.dir_manager.directories.INPUT_DATA)
            / f"{self.filename}{self._get_file_extension()}"
        )

    def read_input_file(self) -> pd.DataFrame:
        """
        Reads and returns the input file as a pandas DataFrame.
        """

        try:
            file_format = self.file_specs.SupportedFormats[self.file_format]
            df = file_format.reader(self.file_path)
            df.dropna(inplace=True)

            # Validate schema
            InputFileSpecs.ValidationSchema.validate(df)
            return df
        except Exception as e:
            raise IOError(f"Failed to read input file : {e}")


@dataclass
class InputDataProcessorConfig:
    """
    Manage configuration for input data processing.
    """

    app_config: AppConfig
    max_workers: int = field(init=False)
    chunksize: int = field(init=False)
    retry_delay: int = field(init=False)
    max_retry_no: int = field(init=False)

    def __post_init__(self):
        self.env_manager = self.app_config.environment_manager
        self.max_workers = int(
            self.env_manager.get_environment_var(
                self.env_manager.variables.MAX_WORKERS,
                max(1, multiprocessing.cpu_count() - 1),
            )
        )
        self.chunksize = int(
            self.env_manager.get_environment_var(
                self.env_manager.variables.CHUNKSIZE, 100
            )
        )
        self.retry_delay = int(
            self.env_manager.get_environment_var(
                self.env_manager.variables.RETRY_DELAY, 600
            )
        )
        self.max_retry_no = int(
            self.env_manager.get_environment_var(
                self.env_manager.variables.MAX_RETRY_NO, 3
            )
        )

        validate_positive_value(
            {
                self.env_manager.variables.RETRY_DELAY.value: self.retry_delay,
                self.env_manager.variables.MAX_RETRY_NO.value: self.max_retry_no,
                self.env_manager.variables.CHUNKSIZE.value: self.chunksize,
                self.env_manager.variables.MAX_WORKERS.value: self.max_workers,
            }
        )
