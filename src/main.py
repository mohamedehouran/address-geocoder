from src.config.app import app_config
from src.config.address_geocoding import address_geocoding_config
from src.config.iris_geocoding import iris_geocoding_config
from src.config.input import InputFileConfig
from src.utils.address_geocoder import AddressGeocoder
from src.utils.geocoding_orchestrator import GeocodingProcessor, GeocodingOrchestrator
from src.utils.helpers import catch_exceptions
from src.utils.iris_geocoder import IRISGeocoder


@catch_exceptions
def main():
    # Initialize common workflow components
    input_file_config = InputFileConfig(app_config)

    address_geocoder = AddressGeocoder(address_geocoding_config)
    iris_geocoder = IRISGeocoder(iris_geocoding_config)

    geocoding_processor = GeocodingProcessor(
        input_file_config,
        address_geocoding_config,
        iris_geocoding_config,
        iris_geocoder,
        app_config,
    )

    # Initialize workflow
    orchestrator = GeocodingOrchestrator(
        input_file_config,
        address_geocoding_config,
        address_geocoder,
        geocoding_processor,
        app_config,
    )

    # Execute the workflow
    orchestrator.execute_geocoding_workflow()


if __name__ == "__main__":
    main()
