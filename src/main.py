import click
from src.config.app import app_config
from src.config.address_geocoding import GeocodingService, AddressGeocodingConfig
from src.config.iris_geocoding import IRISGeocodingConfig
from src.config.input import InputFileConfig, InputDataProcessorConfig
from src.utils.address_geocoder import AddressGeocoder
from src.utils.geocoding_orchestrator import (
    GeocodingDependencies,
    GeocodingProcessor,
    GeocodingOrchestrator,
)
from src.utils.helpers import catch_exceptions
from src.utils.iris_geocoder import IRISGeocoder


env_manager = app_config.environment_manager


@click.command()
@click.option(
    "--filename",
    type=str,
    required=True,
    default=env_manager.get_environment_var(env_manager.variables.INPUT_FILENAME),
    show_default=True,
    prompt="Input filename",
)
@click.option(
    "--file_format",
    type=str,
    required=True,
    default=env_manager.get_environment_var(env_manager.variables.INPUT_FILE_FORMAT),
    show_default=True,
    prompt="Input file format",
)
@click.option(
    "--iris_geocoding",
    type=bool,
    required=False,
    default=False,
    show_default=True,
    prompt="Would you like to add IRIS geocoding?",
)
@catch_exceptions
def main(filename: str, file_format: str, iris_geocoding: bool):
    # Initialize common workflow components
    address_geocoding_config = AddressGeocodingConfig(
        geocoding_service=GeocodingService(app_config=app_config)
    )
    iris_geocoding_config = IRISGeocodingConfig(app_config=app_config)

    geocoding_deps = GeocodingDependencies(
        app_config=app_config,
        input_file_config=InputFileConfig(
            filename=filename,
            file_format=file_format,
            app_config=app_config,
        ),
        input_data_processor_config=InputDataProcessorConfig(app_config=app_config),
        address_geocoding_config=address_geocoding_config,
        iris_geocoding_config=iris_geocoding_config,
        address_geocoder=AddressGeocoder(config=address_geocoding_config),
        iris_geocoder=IRISGeocoder(config=iris_geocoding_config),
        iris_geocoding=iris_geocoding,
    )

    # Initialize workflow
    geocoding_processor = GeocodingProcessor(geocoding_deps)
    geocoding_orchestrator = GeocodingOrchestrator(geocoding_processor)

    # Execute the workflow
    geocoding_orchestrator.execute_geocoding_workflow()


if __name__ == "__main__":
    main()
