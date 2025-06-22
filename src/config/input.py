import pandas as pd
import multiprocessing
import pandera.pandas as pa
from enum import Enum
from fastapi import File
from pathlib import Path
from io import StringIO, BytesIO
from dataclasses import dataclass, field
from src.config.app import AppConfig
from src.config.config_validator import (
    validate_value_is_allowed,
    validate_positive_value,
)


class InputFileSpecs:
    """
    Specifications for input files, including expected column names, validation schema, and supported formats.
    """

    class ColumnNames(Enum):
        """
        Column names expected in the input DataFrame.
        """

        ID = "id"
        ADDRESS = "address"

    class ValidationSchema(pa.DataFrameModel):
        """
        Pandera schema for validating the input DataFrame structure.
        """

        id: str = pa.Field(unique=True, coerce=True)
        address: str = pa.Field(coerce=True)

    class SupportedFormats(Enum):
        """
        Supported file formats for input files.
        """

        CSV = "csv"
        PARQUET = "parquet"


class InputFileLoader:
    """
    Loads and validates input files for geocoding, ensuring they conform to expected formats and schemas.
    """

    def __init__(
        self,
        app_config: AppConfig,
        file: File,
    ):
        self.app_config = app_config
        self.file = file

        self.filename = file.filename.split(".")[0]
        self.file_format = file.filename.split(".")[1]
        self.processed_file_path = self._get_processed_file_path()

        validate_value_is_allowed(
            self.file_format, [ff.value for ff in InputFileSpecs.SupportedFormats]
        )

    def _get_processed_file_path(self) -> Path:
        """
        Returns the path where the processed file will be saved.
        """
        dir_manager = self.app_config.directory_manager
        return (
            dir_manager.get_directory_path(dir_manager.directories.DATA)
            / f"{self.filename}_processed.csv"
        )

    def read_input_file(self) -> pd.DataFrame:
        """
        Reads and returns the input file as a pandas DataFrame.
        """

        try:
            content = self.file.file.read()

            if self.file_format == InputFileSpecs.SupportedFormats.CSV.value:
                df = pd.read_csv(StringIO(content.decode("utf-8")))
            elif self.file_format == InputFileSpecs.SupportedFormats.PARQUET.value:
                df = pd.read_parquet(BytesIO(content))
            else:
                raise ValueError(f"Unsupported file format: {self.file_format}")

            # Validate the DataFrame against the schema
            df.dropna(inplace=True)
            if df.empty:
                raise ValueError("Input file is empty or contains only NaN values.")

            InputFileSpecs.ValidationSchema.validate(df)

            return df
        except Exception as e:
            raise IOError(f"Failed to read input file : {e}")


@dataclass
class InputDataProcessorConfig:
    """
    Configuration for the input data processor, including settings for parallel processing and retry logic.
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
