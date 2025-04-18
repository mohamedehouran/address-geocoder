import time
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Generator, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.config.app import AppConfig
from src.config.address_geocoding import AddressGeocodingConfig
from src.config.input import InputFileConfig, InputDataProcessorConfig
from src.config.iris_geocoding import IRISGeocodingConfig
from src.config.logger import logger
from src.utils.address_geocoder import AddressGeocoder
from src.utils.helpers import catch_exceptions, convert_to_numeric
from src.utils.iris_geocoder import IRISGeocoder


@dataclass
class GeocodingDependencies:
    """
    Container for all dependencies required by geocoding components.
    """

    app_config: AppConfig
    input_file_config: InputFileConfig
    input_data_processor_config: InputDataProcessorConfig
    address_geocoding_config: AddressGeocodingConfig
    iris_geocoding_config: IRISGeocodingConfig
    address_geocoder: AddressGeocoder
    iris_geocoder: IRISGeocoder
    iris_geocoding: bool


class GeocodingProcessor:
    """
    Processes geocoding results.
    """

    def __init__(self, deps: GeocodingDependencies) -> None:
        self.deps = deps
        self.app_config = deps.app_config
        self.input_file_config = deps.input_file_config
        self.address_geocoding_config = deps.address_geocoding_config
        self.iris_geocoder = deps.iris_geocoder
        self.iris_gdf = deps.iris_geocoding_config.get_iris_gdf()

    @catch_exceptions
    def _convert_to_dataframe_and_format(self, output: Dict[str, Any]) -> pd.DataFrame:
        """
        Converts geocoding results into a pandas DataFrame and applies necessary formatting.
        """
        df = pd.DataFrame(output).fillna(pd.NA)
        df = convert_to_numeric(df, self.address_geocoding_config.numeric_columns)
        return df

    @catch_exceptions
    def _save_output(self, df: pd.DataFrame) -> None:
        """
        Saves the geocoding results to an output CSV file.
        """
        app_dir = self.app_config.directory_manager
        file_path = (
            app_dir.get_directory_path(app_dir.directories.OUTPUT_DATA)
            / f"{self.input_file_config.filename}_processed.csv"
        )
        write_header = not file_path.exists()
        df.to_csv(file_path, mode="a", header=write_header, index=False)

    @catch_exceptions
    def process_output(
        self, output: Dict[str, Any], chunk_no: int, iris_geocoding: bool
    ) -> None:
        """
        Processes geocoding results by formatting them and applying IRIS geocoding if needed, then saves the final output.
        """
        logger.info(f"Applying transformations on chunk {chunk_no} ...")
        df = self._convert_to_dataframe_and_format(output)

        if iris_geocoding:
            logger.info("Adding IRIS Geocoding ...")
            df = self.iris_geocoder.perform_iris_geocoding(df, self.iris_gdf)

        self._save_output(df)
        logger.info(f"Successfully transformed and saved chunk {chunk_no}")


class GeocodingOrchestrator:
    """
    Orchestrates the geocoding workflow by processing input data and handling parallel execution.
    """

    def __init__(self, geocoding_processor: GeocodingProcessor) -> None:
        self.geocoding_processor = geocoding_processor
        self.input_file_config = geocoding_processor.deps.input_file_config
        self.address_geocoding_config = (
            geocoding_processor.deps.address_geocoding_config
        )
        self.address_geocoder = geocoding_processor.deps.address_geocoder
        self.input_data_processor_config = (
            geocoding_processor.deps.input_data_processor_config
        )
        self.iris_geocoding = geocoding_processor.deps.iris_geocoding
        self.max_address_length = 75

    @catch_exceptions
    def _fetch_input_data_from_file(self) -> Generator[Tuple[str, str], None, None]:
        """
        Reads input data from a file and yields address entries for geocoding.
        """
        logger.info("Fetching input data from file ...")
        df = self.input_file_config.read_input_file()

        for _, row in df.iterrows():
            yield (
                row[self.input_file_config.file_specs.ColumnNames.ID.value],
                row[self.input_file_config.file_specs.ColumnNames.ADDRESS.value],
            )

    @catch_exceptions
    def _geocode_input_row(self, id: str, address: str) -> Dict[str, Any]:
        """
        Geocodes a single address entry and returns the result.
        """
        address = address[: self.max_address_length]

        key = {self.input_file_config.file_specs.ColumnNames.ID.value: id}
        attempt_status, error_logs, location = self.address_geocoder.geocode_address(
            address
        )

        if location:
            logger.info(
                f"Geocoding attempt {attempt_status} for '{id}' succeeded with {self.address_geocoding_config.get_encoder(location)}"
            )
            location["is_encoded"] = True
            return {**key, **location}
        else:
            logger.warning(
                f"Geocoding attempt {attempt_status} for '{id}' failed : {error_logs}"
            )
            return {**key, "is_encoded": False}

    @catch_exceptions
    def _perform_geocoding(self, id: str, address: str) -> Dict[str, Any]:
        """
        Attempts to geocode an address entry with retries in case of failure.
        """
        retry_delay = self.input_data_processor_config.retry_delay
        for attempt in range(self.input_data_processor_config.max_retry_no):
            try:
                return self._geocode_input_row(id, address)

            except Exception as e:
                logger.warning(
                    f"Unexpected error occurred during geocoding attempt {attempt + 1} for '{id}': {e}"
                )
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2

        return {}

    @catch_exceptions
    def execute_geocoding_workflow(self) -> None:
        """
        Executes the geocoding workflow.
        """
        total_rows_processed = 0
        chunk_no = 0
        output = []

        logger.info("Starting geocoding workflow ...")
        with ThreadPoolExecutor(
            max_workers=self.input_data_processor_config.max_workers
        ) as executor:
            futures = {
                executor.submit(
                    self._perform_geocoding,
                    id,
                    address,
                ): id
                for id, address in self._fetch_input_data_from_file()
            }

            for future in as_completed(futures):
                id = futures[future]

                try:
                    result = future.result()
                    output.append(result)
                    total_rows_processed += 1

                    if len(output) >= self.input_data_processor_config.chunksize:
                        chunk_no += 1
                        self.geocoding_processor.process_output(
                            output, chunk_no, self.iris_geocoding
                        )
                        output.clear()

                except Exception as e:
                    logger.error(f"Unexpected error processing '{id}' : {e}")
                    raise

        if output:
            chunk_no += 1
            self.geocoding_processor.process_output(
                output, chunk_no, self.iris_geocoding
            )

        logger.info(
            f"Geocoding workflow completed successfully : {chunk_no} chunks, {total_rows_processed} rows"
        )
