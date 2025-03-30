import os
import ssl
import geopy
import certifi
from enum import Enum, auto
from dotenv import load_dotenv
from typing import Dict, List, Any
from geopy.geocoders import Nominatim, Photon, OpenCage
from src.config.config_validator import (
    validate_required_vars,
    validate_geocoder_with_api_key,
)
from src.utils.helpers import catch_exceptions


ctx = ssl.create_default_context(cafile=certifi.where())
geopy.geocoders.options.default_ssl_context = ctx


load_dotenv()


class LocationColumn:
    """
    Structure of location-related columns for different geocoding services.
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


class GeocodingService:
    """
    Manages the initialization and usage of geocoding services.
    """

    def __init__(self):
        self.geocoder: Geocoder = Geocoder
        self.opencage_api_key: str = os.getenv("OPENCAGE_API_KEY")
        self.default_user_agent: str = "address-geocoder"
        self.default_delay: float = float(1)

        self.__post_init__()

    def __post_init__(self):
        validate_required_vars({"OPENCAGE_API_KEY": self.opencage_api_key})
        self._initialize_geocoders()
        validate_geocoder_with_api_key(self.geocoder.OPENCAGE.value, self.OpenCage)

    @catch_exceptions
    def _initialize_geocoders(self) -> None:
        """
        Initializes geocoding services.
        """
        self.Nominatim: geopy.Nominatim = Nominatim(user_agent=self.default_user_agent)
        self.Photon: geopy.Photon = Photon(user_agent=self.default_user_agent)
        self.OpenCage: geopy.OpenCage = OpenCage(api_key=self.opencage_api_key)


class AddressGeocodingConfig:
    """
    Configuration class for managing the formatting of geocoding results.
    """

    def __init__(self):
        self.geocoding_service: GeocodingService = GeocodingService()
        self.numeric_columns: List[str] = [
            LocationColumn.Output.latitude.name,
            LocationColumn.Output.longitude.name,
        ]

    @catch_exceptions
    def _get_nominatim_format_config(self, location: str) -> Dict[str, Any]:
        """
        Formats geocoding results from Nominatim.
        """
        address = location.raw.get("address", {})

        config = {
            LocationColumn.name: address.get(LocationColumn.value, "")
            for LocationColumn in LocationColumn.Default
        }
        extra_config = {}

        for column in LocationColumn.Extra.Nominatim:
            if column.name in self.numeric_columns:
                extra_config[column.name] = float(location.raw.get(column.value, 0))
            else:
                extra_config[column.name] = location.raw.get(column.value, None)

        return {**config, **extra_config}

    @catch_exceptions
    def _get_photon_format_config(self, location: str) -> Dict[str, Any]:
        """
        Formats geocoding results from Photon.
        """
        properties = location.raw.get("properties", {})
        geometry = location.raw.get("geometry", {})

        config = {
            LocationColumn.name: properties.get(LocationColumn.value, "")
            for LocationColumn in LocationColumn.Photon
        }
        extra_config = {}
        coordinates = geometry.get("coordinates", [0, 0])

        for column in LocationColumn.Extra.Photon:
            if column.name == LocationColumn.Output.longitude.name:
                extra_config[column.name] = float(coordinates[0])
            elif column.name == LocationColumn.Output.latitude.name:
                extra_config[column.name] = float(coordinates[1])
            else:
                extra_config[column.name] = properties.get(column.value, None)

        return {**config, **extra_config}

    @catch_exceptions
    def _get_opencage_format_config(self, location: str) -> Dict[str, Any]:
        """
        Formats geocoding results from OpenCage.
        """
        components = location.raw.get("components", {})
        geometry = location.raw.get("geometry", {})

        config = {
            LocationColumn.name: components.get(LocationColumn.value, "")
            for LocationColumn in LocationColumn.Default
        }
        extra_config = {}

        for column in LocationColumn.Extra.OpenCage:
            if column.name in self.numeric_columns:
                extra_config[column.name] = float(geometry.get(column.value, 0))
            else:
                extra_config[column.name] = components.get(column.value, None)

        return {**config, **extra_config}

    @catch_exceptions
    def get_format_config(self, geocoder: Geocoder, location: str) -> Dict[str, Any]:
        """
        Returns a formatted configuration for a geocoded location based on the specified geocoder.
        """
        if geocoder == Geocoder.NOMINATIM:
            return self._get_nominatim_format_config(location)
        elif geocoder == Geocoder.PHOTON:
            return self._get_photon_format_config(location)
        elif geocoder == Geocoder.OPENCAGE:
            return self._get_opencage_format_config(location)

    @catch_exceptions
    def apply_format(self, geocoder: Geocoder, address: str, **kwargs) -> None:
        """
        Applies the final formatting to the geocoded address data, including raw address and the geocoder's name.
        """
        final_config = {
            column.name: kwargs.get(column.name, "") for column in LocationColumn.Output
        }
        final_config["raw_address"] = address
        final_config["encoder"] = geocoder.value
        return final_config

    @catch_exceptions
    def get_encoder(self, formatted_location: Dict[str, Any]) -> None:
        """
        Returns the geocoder used for the formatted location result.
        """
        return formatted_location["encoder"]


address_geocoding_config = AddressGeocodingConfig()
