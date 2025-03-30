import logging
from enum import Enum
from pathlib import Path
from typing import Optional
from src.config.app import AppConfig, app_config


class LoggerConfig:
    """
    Configures the application's logging system.
    """

    class Key(Enum):
        FILENAME = "app.log"
        FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
        DATEFMT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, level: int, app_config: AppConfig):
        self.app_dir = app_config.directory_manager
        self.level = level

    def _get_logs_file_path(self) -> Path:
        """
        Returns the log file path.
        """
        return (
            self.app_dir.get_directory_path(self.app_dir.directory.LOGS)
            / self.Key.FILENAME.value
        )

    def configure_logging(self) -> None:
        """
        Configures the logging system.
        """
        try:
            logging.basicConfig(
                format=LoggerConfig.Key.FORMAT.value,
                datefmt=LoggerConfig.Key.DATEFMT.value,
                level=self.level,
                force=True,
                handlers=[
                    logging.FileHandler(self._get_logs_file_path()),
                    logging.StreamHandler(),
                ],
            )
            logging.getLogger(__name__).info("Logging initialized successfully")
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error occurred while configuring logging : {e}"
            )

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        Returns a configured logger instance.
        """
        return logging.getLogger(name)


logger_config_inst = LoggerConfig(logging.INFO, app_config)
logger_config_inst.configure_logging()
logger = logger_config_inst.get_logger()
