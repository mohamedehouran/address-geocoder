import ssl
import geopy
import certifi
from enum import Enum, auto
from typing import Dict, Any
from geopy.geocoders import Nominatim, Photon, OpenCage
from src.config.app import AppConfig
from src.config.config_validator import (
    validate_required_vars,
    validate_geocoder_with_api_key,
)

# Set SSL context
ctx = ssl.create_default_context(cafile=certifi.where())
geopy.geocoders.options.default_ssl_context = ctx


class GeocodingResponseSchema:
    """
    Standardized field mappings for geocoding service responses and output.
    """

    class Default(Enum):
        """
        Default mapping of location attributes.
        """

        street_number = "house_number"
        street_name = "road"
        postal_code = "postcode"
        city = "city"
        admin_level_1 = "county"
        admin_level_2 = "state"
        country = "country"

    class Photon(Enum):
        """
        Photon-specific mapping of location attributes.
        """

        street_number = "housenumber"
        street_name = "name"
        postal_code = "postcode"
        city = "city"
        admin_level_1 = "county"
        admin_level_2 = "state"
        country = "country"

    class Extra:
        """
        Additional attributes provided by different geocoders.
        """

        class Nominatim(Enum):
            latitude = "lat"
            longitude = "lon"
            location_type = "type"
            address_type = "addresstype"

        class Photon(Enum):
            latitude = auto()
            longitude = auto()
            location_type = "type"
            address_type = "osm_value"

        class OpenCage(Enum):
            latitude = "lat"
            longitude = "lng"
            location_type = "_type"
            address_type = "_category"

    class Output(Enum):
        """
        Standardized output fields for geocoding results.
        """

        street_number = auto()
        street_name = auto()
        postal_code = auto()
        city = auto()
        admin_level_1 = auto()
        admin_level_2 = auto()
        country = auto()
        latitude = auto()
        longitude = auto()
        location_type = auto()
        address_type = auto()


class GeocodingService(Enum):
    """
    Available geocoding services.
    """

    NOMINATIM = "Nominatim"
    PHOTON = "Photon"
    OPENCAGE = "OpenCage"


class GeocodingServiceManager:
    """
    Manages the initialization and usage of geocoding services.
    """

    def __init__(self, app_config: AppConfig) -> None:
        self.app_config = app_config
        self.default_user_agent = "address-geocoder"
        self.default_delay = 5

        self.__post_init__()

    def __post_init__(self):
        self.env_manager = self.app_config.environment_manager
        self.opencage_api_key = self.env_manager.get_environment_var(
            self.env_manager.variables.OPENCAGE_API_KEY
        )
        self._initialize_geocoders()

        self._validate_config()

    def _initialize_geocoders(self) -> None:
        """
        Initializes geocoding services.
        """
        try:
            self.Nominatim: geopy.Nominatim = Nominatim(
                user_agent=self.default_user_agent
            )
            self.Photon: geopy.Photon = Photon(user_agent=self.default_user_agent)
            self.OpenCage: geopy.OpenCage = OpenCage(api_key=self.opencage_api_key)
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error occurred initializing geocoders : {e}"
            )

    def _validate_config(self):
        """
        Centralized configuration validation.
        """
        validate_required_vars(
            {self.env_manager.variables.OPENCAGE_API_KEY.value: self.opencage_api_key}
        )
        validate_geocoder_with_api_key(GeocodingService.OPENCAGE, self.OpenCage)


class GeocodingResponseFormatter:
    """
    Formats geocoding results from various services into a standardized schema.
    """

    def _get_nominatim_format_config(self, location: str) -> Dict[str, Any]:
        """
        Formats geocoding results from Nominatim.
        """
        try:
            address = location.raw.get("address", {})

            config = {
                GeocodingResponseSchema.name: address.get(
                    GeocodingResponseSchema.value, ""
                )
                for GeocodingResponseSchema in GeocodingResponseSchema.Default
            }
            extra_config = {}

            for column in GeocodingResponseSchema.Extra.Nominatim:
                if column.name in ["latitude", "longitude"]:
                    extra_config[column.name] = float(location.raw.get(column.value, 0))
                else:
                    extra_config[column.name] = location.raw.get(column.value)

            return {**config, **extra_config}
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error occurred retrieving Nominatim format configuration : {e}"
            )

    def _get_photon_format_config(self, location: str) -> Dict[str, Any]:
        """
        Formats geocoding results from Photon.
        """
        try:
            properties = location.raw.get("properties", {})
            geometry = location.raw.get("geometry", {})

            config = {
                GeocodingResponseSchema.name: properties.get(
                    GeocodingResponseSchema.value, ""
                )
                for GeocodingResponseSchema in GeocodingResponseSchema.Photon
            }
            extra_config = {}
            coordinates = geometry.get("coordinates", [0, 0])

            for column in GeocodingResponseSchema.Extra.Photon:
                if column.name == GeocodingResponseSchema.Output.longitude.name:
                    extra_config[column.name] = float(coordinates[0])
                elif column.name == GeocodingResponseSchema.Output.latitude.name:
                    extra_config[column.name] = float(coordinates[1])
                else:
                    extra_config[column.name] = properties.get(column.value)

            return {**config, **extra_config}
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error occurred retrieving Photon format configuration : {e}"
            )

    def _get_opencage_format_config(self, location: str) -> Dict[str, Any]:
        """
        Formats geocoding results from OpenCage.
        """
        try:
            components = location.raw.get("components", {})
            geometry = location.raw.get("geometry", {})

            config = {
                GeocodingResponseSchema.name: components.get(
                    GeocodingResponseSchema.value, ""
                )
                for GeocodingResponseSchema in GeocodingResponseSchema.Default
            }
            extra_config = {}

            for column in GeocodingResponseSchema.Extra.OpenCage:
                if column.name in ["latitude", "longitude"]:
                    extra_config[column.name] = float(geometry.get(column.value, 0))
                else:
                    extra_config[column.name] = components.get(column.value)

            return {**config, **extra_config}
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error occurred retrieving OpenCage format configuration : {e}"
            )

    def get_format_config(self, gs: GeocodingService, location: str) -> Dict[str, Any]:
        """
        Returns a formatted configuration for a geocoded location based on the specified geocoder.
        """
        try:
            if gs == GeocodingService.NOMINATIM:
                return self._get_nominatim_format_config(location)
            elif gs == GeocodingService.PHOTON:
                return self._get_photon_format_config(location)
            elif gs == GeocodingService.OPENCAGE:
                return self._get_opencage_format_config(location)
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error occurred retrieving format configuration : {e}"
            )

    def apply_format(self, gs: GeocodingService, address: str, **kwargs) -> None:
        """
        Applies the final formatting to the geocoded address data, including raw address and the geocoder's name.
        """
        try:
            final_config = {
                column.name: kwargs.get(column.name, "")
                for column in GeocodingResponseSchema.Output
            }
            final_config["raw_address"] = address
            final_config["encoder"] = gs.value
            return final_config
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error occurred applying format to the geocoded address data : {e}"
            )
