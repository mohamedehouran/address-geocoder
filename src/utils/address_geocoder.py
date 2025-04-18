from typing import Tuple, Dict, Optional, Any
from geopy.extra.rate_limiter import RateLimiter
from geopy.exc import GeocoderAuthenticationFailure, GeocoderTimedOut
from src.config.address_geocoding import Geocoder, AddressGeocodingConfig
from src.utils.helpers import catch_exceptions


class AddressGeocoder:
    """
    Responsible for geocoding addresses into geographical coordinates.
    """

    def __init__(self, config: AddressGeocodingConfig) -> None:
        self.config = config
        self.gecoding_service = self.config.geocoding_service

    @catch_exceptions
    def _format_result(
        self, geocoder: Geocoder, location: str, address: str
    ) -> Optional[Dict[str, Any]]:
        """
        Formats the geocoding results for a given geocoder.
        """
        if location:
            format_config = self.config.get_format_config(geocoder, location)
            return self.config.apply_format(geocoder, address, **format_config)
        return None

    @catch_exceptions
    def geocode_address(
        self, address: str
    ) -> Optional[Tuple[str, Optional[str], Optional[Dict[str, Any]]]]:
        """
        Geocodes an address into geographical coordinates using multiple geocoding services, and returns a tuple containing the attempt, status, the error log and the geocoding result.
        """
        max_attempts = len(self.gecoding_service.geocoder)
        attempt = 1

        for gc in self.gecoding_service.geocoder:
            geocode = RateLimiter(
                getattr(self.gecoding_service, gc.value).geocode,
                min_delay_seconds=self.gecoding_service.default_delay,
            )

            try:
                # Special configuration for Nominatim
                if gc == self.gecoding_service.geocoder.NOMINATIM:
                    location = geocode(
                        address,
                        timeout=None,
                        addressdetails=True,
                        language="fr",
                        exactly_one=True,
                    )
                else:
                    location = geocode(
                        address, timeout=None, language="fr", exactly_one=True
                    )

                if location:
                    return (
                        f"{attempt}/{max_attempts}",
                        None,
                        self._format_result(gc, location, address),
                    )
                else:
                    attempt += 1

            except GeocoderAuthenticationFailure as e:
                return (
                    f"{attempt}/{max_attempts}",
                    f"Authentication failed : {e}",
                    None,
                )

            except GeocoderTimedOut as e:
                return (f"{attempt}/{max_attempts}", f"Timeout occurred : {e}", None)

            except Exception as e:
                return (
                    f"{attempt}/{max_attempts}",
                    f"Unexpected error occured : {e}",
                    None,
                )

            attempt += 1

        return None
