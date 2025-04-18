import ssl
import geopy
import certifi
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from geopy.geocoders import Nominatim, Photon, OpenCage
from src.config.app import AppConfig
from src.config.config_validator import (
    validate_required_vars,
    validate_geocoder_with_api_key,
)

# Set SSL context
ctx = ssl.create_default_context(cafile=certifi.where())
geopy.geocoders.options.default_ssl_context = ctx


class GeocodingSchema:
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
            latitude = None
            longitude = None
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


class Geocoder(Enum):
    """
    Available geocoding services.
    """

    NOMINATIM = "Nominatim"
    PHOTON = "Photon"
    OPENCAGE = "OpenCage"


@dataclass
class GeocodingService:
    """
    Manages the initialization and usage of geocoding services.
    """

    app_config: AppConfig
    geocoder: Geocoder = Geocoder
    default_user_agent: str = "address-geocoder"
    default_delay: float = float(1)
    opencage_api_key: str = field(init=False)

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
        validate_geocoder_with_api_key(self.geocoder.OPENCAGE, self.OpenCage)


@dataclass
class AddressGeocodingConfig:
    """
    Configuration class for managing the formatting of geocoding results.
    """

    geocoding_service: GeocodingService
    numeric_columns: List[str] = field(
        default_factory=lambda: [
            GeocodingSchema.Output.latitude.name,
            GeocodingSchema.Output.longitude.name,
        ]
    )

    def _get_nominatim_format_config(self, location: str) -> Dict[str, Any]:
        """
        Formats geocoding results from Nominatim.
        """
        try:
            address = location.raw.get("address", {})

            config = {
                GeocodingSchema.name: address.get(GeocodingSchema.value, "")
                for GeocodingSchema in GeocodingSchema.Default
            }
            extra_config = {}

            for column in GeocodingSchema.Extra.Nominatim:
                if column.name in self.numeric_columns:
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
                GeocodingSchema.name: properties.get(GeocodingSchema.value, "")
                for GeocodingSchema in GeocodingSchema.Photon
            }
            extra_config = {}
            coordinates = geometry.get("coordinates", [0, 0])

            for column in GeocodingSchema.Extra.Photon:
                if column.name == GeocodingSchema.Output.longitude.name:
                    extra_config[column.name] = float(coordinates[0])
                elif column.name == GeocodingSchema.Output.latitude.name:
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
                GeocodingSchema.name: components.get(GeocodingSchema.value, "")
                for GeocodingSchema in GeocodingSchema.Default
            }
            extra_config = {}

            for column in GeocodingSchema.Extra.OpenCage:
                if column.name in self.numeric_columns:
                    extra_config[column.name] = float(geometry.get(column.value, 0))
                else:
                    extra_config[column.name] = components.get(column.value)

            return {**config, **extra_config}
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error occurred retrieving OpenCage format configuration : {e}"
            )

    def get_format_config(self, geocoder: Geocoder, location: str) -> Dict[str, Any]:
        """
        Returns a formatted configuration for a geocoded location based on the specified geocoder.
        """
        try:
            if geocoder == Geocoder.NOMINATIM:
                return self._get_nominatim_format_config(location)
            elif geocoder == Geocoder.PHOTON:
                return self._get_photon_format_config(location)
            elif geocoder == Geocoder.OPENCAGE:
                return self._get_opencage_format_config(location)
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error occurred retrieving format configuration : {e}"
            )

    def apply_format(self, geocoder: Geocoder, address: str, **kwargs) -> None:
        """
        Applies the final formatting to the geocoded address data, including raw address and the geocoder's name.
        """
        try:
            final_config = {
                column.name: kwargs.get(column.name, "")
                for column in GeocodingSchema.Output
            }
            final_config["raw_address"] = address
            final_config["encoder"] = geocoder.value
            return final_config
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error occurred applying format to the geocoded address data : {e}"
            )

    def get_encoder(self, formatted_location: Dict[str, Any]) -> Optional[str]:
        """
        Returns the geocoder used for the formatted location result.
        """
        return formatted_location.get("encoder")
