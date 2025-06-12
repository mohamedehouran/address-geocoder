import time
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Generator, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.config.app import AppConfig
from src.config.input import InputFileSpecs, InputFileLoader, InputDataProcessorConfig
from src.config.iris_geocoding import IrisGeoJsonLoader
from src.config.logger import logger
from src.utils.geocoder import AddressGeocoder, IRISGeocoder
from src.utils.helpers import catch_exceptions, convert_to_numeric


@dataclass
class GeocodingDependencies:
    """
    Dependencies required for the geocoding processor and orchestrator.
    """

    app_config: AppConfig
    input_file_loader: InputFileLoader
    input_data_processor_config: InputDataProcessorConfig
    address_geocoder: AddressGeocoder
    iris_geocoding: bool
    iris_geojson_loader: IrisGeoJsonLoader
    iris_geocoder: IRISGeocoder


class GeocodingProcessor:
    """
    Processes geocoding results by formatting them and applying IRIS geocoding if needed.
    """

    def __init__(self, deps: GeocodingDependencies) -> None:
        self.deps = deps

        self.processed_file_path = deps.input_file_loader.processed_file_path
        self.iris_gdf = self.deps.iris_geojson_loader.get_iris_gdf()

    @catch_exceptions
    def _convert_to_dataframe_and_format(self, output: Dict[str, Any]) -> pd.DataFrame:
        """
        Converts geocoding results into a pandas DataFrame and applies necessary formatting.
        """
        df = pd.DataFrame(output).fillna(pd.NA)
        df = convert_to_numeric(df, numeric_columns=["latitude", "longitude"])
        return df

    @catch_exceptions
    def _save_processed_df(self, df: pd.DataFrame) -> None:
        """
        Saves the processed DataFrame to a CSV file, appending if the file already exists.
        """
        write_header = not self.processed_file_path.exists()
        df.to_csv(self.processed_file_path, mode="a", header=write_header, index=False)

    @catch_exceptions
    def process_output(
        self, output: Dict[str, Any], chunk_no: int, iris_geocoding: bool
    ) -> None:
        """
        Processes geocoding results by formatting them and applying IRIS geocoding if needed, then saves the final output.
        """
        logger.info(f"Applying transformations on chunk '{chunk_no}' ...")
        df = self._convert_to_dataframe_and_format(output)

        if iris_geocoding:
            logger.info("Adding IRIS Geocoding ...")
            df = self.deps.iris_geocoder.perform_iris_geocoding(df, self.iris_gdf)

        self._save_processed_df(df)
        logger.info(f"Successfully transformed and saved chunk {chunk_no}")


@dataclass
class GeocodingOrchestratorResult:
    """
    Result of the geocoding orchestration process.
    """

    status: str
    execution_time: str
    processed_file_path: str
    total_chunks: str
    total_processed: str
    success_count: str
    success_ratio: str
    error_count: str
    error_ratio: str


class GeocodingOrchestrator:
    """
    Orchestrates the geocoding workflow by fetching input data, performing geocoding, and processing the results.
    """

    def __init__(self, processor: GeocodingProcessor) -> None:
        self.processor = processor

        self.input_file_loader = processor.deps.input_file_loader
        self.input_data_processor_config = processor.deps.input_data_processor_config
        self.address_geocoder = processor.deps.address_geocoder
        self.iris_geocoding = processor.deps.iris_geocoding
        self.max_address_length = 75

    @catch_exceptions
    def _fetch_input_data_from_file(self) -> Generator[Tuple[str, str], None, None]:
        """
        Reads input data from a file and yields address entries for geocoding.
        """
        logger.info(
            f"Fetching input data from '{self.input_file_loader.file_format}' file ..."
        )
        df = self.input_file_loader.read_input_file()

        for _, row in df.iterrows():
            yield (
                row[InputFileSpecs.ColumnNames.ID.value],
                row[InputFileSpecs.ColumnNames.ADDRESS.value],
            )

    @catch_exceptions
    def _geocode_input_row(self, id: str, address: str) -> Dict[str, Any]:
        """
        Geocodes a single address entry and returns the result.
        """
        address = address[: self.max_address_length]
        geocoding_result = self.address_geocoder.geocode_address(address)
        key = {InputFileSpecs.ColumnNames.ID.value: id}

        if geocoding_result.status == "success":
            logger.info(
                f"Geocoding attempt {geocoding_result.attempt} for '{id}' succeeded with '{geocoding_result.geocoder}'"
            )
            geocoding_result.location["is_encoded"] = True
            return {**key, **geocoding_result.location}
        else:
            logger.warning(
                f"Geocoding attempt {geocoding_result.attempt} for '{id}' failed with '{geocoding_result.geocoder}' : {geocoding_result.error}"
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
    def execute_geocoding_workflow(self) -> GeocodingOrchestratorResult:
        """
        Executes the geocoding workflow.
        """
        total_failed = 0
        total_success = 0
        total_chunks = 0
        output = []
        time_start = time.time()

        logger.info(
            f"Starting geocoding workflow for file '{self.input_file_loader.filename}.{self.input_file_loader.file_format}' ..."
        )
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
                    total_success += 1

                    if len(output) >= self.input_data_processor_config.chunksize:
                        total_chunks += 1
                        self.processor.process_output(
                            output, total_chunks, self.iris_geocoding
                        )
                        output.clear()

                except Exception as e:
                    logger.error(f"Unexpected error processing '{id}' : {e}")
                    total_failed += 1
                    raise

        if output:
            total_chunks += 1
            self.processor.process_output(output, total_chunks, self.iris_geocoding)

        total_processed = total_success + total_failed
        time_end = time.time()
        elapsed_time = time_end - time_start

        logger.info(
            f"Geocoding workflow completed in {elapsed_time:.2f} seconds : {total_chunks} chunks, {total_processed} rows processed"
        )
        return GeocodingOrchestratorResult(
            status="success",
            execution_time=f"{elapsed_time:.2f} seconds",
            processed_file_path=str(self.processor.processed_file_path),
            total_chunks=str(total_chunks),
            total_processed=str(total_processed),
            success_count=str(total_success),
            success_ratio=f"{(total_success / total_processed) * 100:.2f}%",
            error_count=str(total_failed),
            error_ratio=f"{(total_failed / total_processed) * 100:.2f}%",
        )
