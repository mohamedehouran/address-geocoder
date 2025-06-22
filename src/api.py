from dataclasses import asdict
from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException, UploadFile, Query, File
from src.config.app import app_config
from src.config.address_geocoding import (
    GeocodingServiceManager,
    GeocodingResponseFormatter,
)
from src.config.iris_geocoding import IrisGeoJsonLoader
from src.config.input import InputFileSpecs, InputFileLoader, InputDataProcessorConfig
from src.utils.geocoder import AddressGeocoder, IRISGeocoder
from src.utils.orchestrator import (
    GeocodingDependencies,
    GeocodingProcessor,
    GeocodingOrchestrator,
)


app = FastAPI(
    title="🌍 Address Geocoder",
    description="Address Geocoder is a powerful Python-based solution for geocoding raw addresses. Designed for efficiency and accuracy, it supports batch processing and integrates multiple geocoding services to ensure high reliability. Whether you're working with large datasets or need precise location data, this tool is built to handle your geocoding needs seamlessly.",
    version="0.1.0",
    github="https://github.com/mohamedehouran/address-geocoder/",
)


@app.post(
    "/geocode/",
    summary="Geocode Addresses from File",
    description="This endpoint allows you to upload a file containing addresses that need to be geocoded. The service will process the file and return a CSV file with the geocoded addresses.",
    response_description="CSV file with geocoded addresses",
    tags=["Geocoding"],
)
async def geocode_file(
    file: UploadFile = File(
        title="Input File",
        description=f"Upload a file containing addresses to be geocoded (Supported formats: {', '.join([ff.value for ff in InputFileSpecs.SupportedFormats])})",
    ),
    language: str = Query(
        default="fr",
        title="Language of input addresses",
        description="Specify the language of the input addresses. List of supported languages (case-insensitive) : https://developer.tomtom.com/online-search/online-search-documentation/supported-languages",
    ),
    iris_geocoding: bool = Query(
        default=False,
        title="IRIS Geocoding",
        description="Would you like to add IRIS geocoding?",
    ),
):
    try:
        # Initialize components
        iris_geojson_loader = IrisGeoJsonLoader(app_config=app_config)

        deps = GeocodingDependencies(
            app_config=app_config,
            input_file_loader=InputFileLoader(
                app_config=app_config,
                file=file,
            ),
            input_data_processor_config=InputDataProcessorConfig(app_config=app_config),
            address_geocoder=AddressGeocoder(
                service_manager=GeocodingServiceManager(app_config=app_config),
                formatter=GeocodingResponseFormatter(),
                language=language,
            ),
            iris_geocoding=iris_geocoding,
            iris_geojson_loader=iris_geojson_loader,
            iris_geocoder=IRISGeocoder(loader=iris_geojson_loader),
        )

        # Process geocoding
        processor = GeocodingProcessor(deps)
        orchestrator = GeocodingOrchestrator(processor)
        result = orchestrator.execute_geocoding_workflow()

        return FileResponse(
            path=result.processed_file_path,
            media_type="text/csv",
            headers=asdict(result),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Unexpected error occured : {str(e)}"
        )
