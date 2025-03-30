import os
import multiprocessing
from enum import Enum
from typing import Dict
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass
from functools import cached_property
from src.config.config_validator import validate_positive_value


load_dotenv()


class Directory(Enum):
    """
    Directories used by the application.
    """

    INPUT_DATA = "data/input"
    OUTPUT_DATA = "data/output"
    LOGS = "logs"
    CONFIG = "src/config/"


class DirectoryManager:
    """
    Manages directory paths, ensuring they exist.
    """

    def __init__(self):
        self.base_dir: Path = Path.cwd()
        self.directory: Directory = Directory

    @cached_property
    def directory_paths(self) -> Dict[str, Path]:
        """
        Returns a dictionary with absolute paths for all directories.
        """
        paths = {}
        for dir in self.directory:
            dir_path = self.base_dir / dir.value
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                paths[dir.name] = dir_path
            except OSError as e:
                raise RuntimeError(
                    f"Unexpected error occured while creating {dir_path} : {e}"
                )
        return paths

    def get_directory_path(self, directory: Directory) -> Path:
        """
        Gets the absolute path for a specific directory
        """
        return self.directory_paths[directory.name]


@dataclass(frozen=True)
class DataProcessor:
    """
    Manage configuration for data processing.
    """

    retry_delay: int = int(os.getenv("RETRY_DELAY", 600))
    max_retry_no: int = int(os.getenv("MAX_RETRY_NO", 3))
    chunksize: int = int(os.getenv("CHUNKSIZE", 10))
    max_workers: int = int(
        os.getenv("MAX_WORKERS", max(1, multiprocessing.cpu_count() - 1))
    )

    def __post_init__(self):
        validate_positive_value(
            {
                "RETRY_DELAY": self.retry_delay,
                "MAX_RETRY_NO": self.max_retry_no,
                "CHUNKSIZE": self.chunksize,
                "MAX_WORKERS": self.max_workers,
            }
        )


class AppConfig:
    """
    Main application configuration.
    """

    def __init__(self):
        self.directory_manager: DirectoryManager = DirectoryManager()
        self.data_processor: DataProcessor = DataProcessor()


app_config = AppConfig()
