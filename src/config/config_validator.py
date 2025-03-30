from pathlib import Path
from typing import Dict, List, Any
from geopy.geocoders.base import Geocoder
from geopy.exc import GeocoderAuthenticationFailure, GeocoderServiceError


def validate_required_vars(required_vars: Dict[str, Any]) -> None:
    """
    Validates that all required variables are not None or empty.
    """
    missing_vars = [key for key, val in required_vars.items() if not val]
    if missing_vars:
        raise ValueError(f"Missing required variable(s) : {', '.join(missing_vars)}")


def validate_value_is_allowed(value: str, allowed_values: List[str]) -> None:
    """
    Validates that a variable value is within a list of allowed values.
    """
    if value not in allowed_values:
        raise ValueError(
            f"Invalid value : {value}. Must be {' or '.join(allowed_values)}"
        )


def validate_positive_value(vars_dict: Dict[str, int]) -> None:
    """
    Validates that a variable value is greater than 0.
    """
    for key, val in vars_dict.items():
        if not isinstance(val, int):
            raise ValueError(f"Invalid value for {key}={val}. Must be integer")
        if val <= 0:
            raise ValueError(f"Invalid value for {key}={val}. Must be greater than 0")


def validate_file_exists(file_path: Path) -> None:
    """
    Validates that a file exists at the given path.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Input file '{file_path}' does not exist")
    if not file_path.is_file():
        raise FileNotFoundError(f"Input file '{file_path}' is not a file")


def validate_dir_exists(directory_path: Path) -> None:
    """
    Validates that a directory exists at the given path.
    """
    if not directory_path.exists():
        raise FileNotFoundError(f"Input directory '{directory_path}' does not exist")
    if not directory_path.is_dir():
        raise FileNotFoundError(
            f"Input directory '{directory_path}' is not a directory"
        )


def validate_geocoder_with_api_key(
    geocoder_name: str, geocoder: Geocoder, address: str = "Tour Eiffel, Paris, France"
) -> None:
    """
    Validate the API key of a geocoder by attempting to geocode a test address.
    """
    try:
        location = geocoder.geocode(address)
        if not location:
            raise GeocoderServiceError(
                f"Test attempt with {geocoder_name} failed : Empty response"
            )
    except GeocoderAuthenticationFailure as e:
        raise GeocoderAuthenticationFailure(
            f"Test attempt with {geocoder_name} failed : API Key not valid ({str(e)})"
        )
    except GeocoderServiceError as e:
        raise GeocoderServiceError(
            f"Test attempt with {geocoder_name} failed : Service error ({str(e)})"
        )
    except Exception as e:
        raise Exception(f"Test attempt with {geocoder_name} failed : {str(e)}")
