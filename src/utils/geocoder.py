import pandas as pd
import geopandas as gpd
from typing import List
from dataclasses import dataclass
from shapely.geometry import Point
from typing import Dict, Optional, Any
from geopy.extra.rate_limiter import RateLimiter
from src.config.address_geocoding import (
    GeocodingService,
    GeocodingServiceManager,
    GeocodingResponseFormatter,
)
from src.config.iris_geocoding import (
    IrisGeoSchema,
    IrisSpatialReference,
    IrisGeoJsonLoader,
)
from src.utils.helpers import catch_exceptions


@dataclass
class AddressGeocodingResult:
    """
    Represents the result of a geocoding operation.
    """

    attempt: str
    status: str
    error: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    geocoder: Optional[str] = None


class AddressGeocoder:
    """
    Provides methods to geocode addresses using multiple geocoding services and formats the results accordingly.
    """

    def __init__(
        self,
        service_manager: GeocodingServiceManager,
        formatter: GeocodingResponseFormatter,
    ) -> None:
        self.service_manager = service_manager
        self.formatter = formatter

    @catch_exceptions
    def _format_result(
        self, gs: GeocodingService, location: str, address: str
    ) -> Optional[Dict[str, Any]]:
        """
        Formats the geocoding results for a given geocoder.
        """
        if location:
            format_config = self.formatter.get_format_config(gs, location)
            return self.formatter.apply_format(gs, address, **format_config)
        return None

    @catch_exceptions
    def geocode_address(self, address: str) -> AddressGeocodingResult:
        """
        Geocodes an address using multiple geocoding services in a sequential manner.
        """
        max_attempts = len(GeocodingService)
        error = None

        for i, gs in enumerate(GeocodingService, start=1):
            geocode = RateLimiter(
                getattr(self.service_manager, gs.value).geocode,
                min_delay_seconds=self.service_manager.default_delay,
            )

            try:
                # Special configuration for Nominatim
                if gs == GeocodingService.NOMINATIM:
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
                    return AddressGeocodingResult(
                        attempt=f"{i}/{max_attempts}",
                        status="success",
                        error=None,
                        location=self._format_result(gs, location, address),
                        geocoder=gs.value,
                    )

            except Exception as e:
                error = str(e)
                continue

        return AddressGeocodingResult(
            attempt=f"{max_attempts}/{max_attempts}",
            status="failed",
            error=error,
            location=None,
            geocoder=None,
        )


class IRISGeocoder:
    """
    Performs spatial joins between tabular data and geospatial IRIS data.
    """

    def __init__(self, loader: IrisGeoJsonLoader) -> None:
        self.loader = loader

    @catch_exceptions
    def _create_geometries(self, df: pd.DataFrame) -> gpd.GeoDataFrame:
        """
        Converts a DataFrame into a GeoDataFrame by creating a geometry column from latitude and longitude columns.
        """
        if "latitude" not in df.columns or "longitude" not in df.columns:
            raise ValueError("Missing required columns: 'latitude' and/or 'longitude'")

        df["geometry"] = df.apply(
            lambda col: Point(col["longitude"], col["latitude"]), axis=1
        )
        return gpd.GeoDataFrame(df, geometry="geometry")

    @catch_exceptions
    def _set_and_transform_crs(
        self, df: pd.DataFrame, iris_gdf: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Sets the coordinate reference system (CRS) for a GeoDataFrame and transforms it to match the target IRIS GeoDataFrame.
        """
        df.set_crs(epsg=IrisSpatialReference.EPSG, inplace=True)
        return df.to_crs(iris_gdf.crs)

    @catch_exceptions
    def _execute_spatial_join(
        self, gdf: gpd.GeoDataFrame, iris_gdf: gpd.GeoDataFrame
    ) -> gpd.GeoDataFrame:
        """
        Performs a spatial join between the input GeoDataFrame and the IRIS GeoDataFrame based on their spatial relationship.
        """
        return gpd.sjoin(gdf, iris_gdf, how="left", predicate="within")

    @catch_exceptions
    def _finalize_result(
        self, result_df: pd.DataFrame, old_columns: List[str]
    ) -> pd.DataFrame:
        """
        Finalizes the geocoding result by selecting relevant columns and renaming them based on the configuration.
        """
        result_df = result_df[old_columns + [col.name for col in IrisGeoSchema]]
        result_df = result_df.rename(
            columns={col.name: col.value for col in IrisGeoSchema}
        )
        return result_df

    @catch_exceptions
    def perform_iris_geocoding(
        self, df: gpd.GeoDataFrame, iris_gdf: gpd.GeoDataFrame
    ) -> pd.DataFrame:
        """
        Performs IRIS geocoding on a DataFrame.
        """
        old_columns = df.columns.to_list()
        gdf = self._create_geometries(df)
        gdf = self._set_and_transform_crs(gdf, iris_gdf)
        result_df = self._execute_spatial_join(gdf, iris_gdf)
        result_df = self._finalize_result(result_df, old_columns)
        return result_df
