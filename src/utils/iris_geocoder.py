import pandas as pd
import geopandas as gpd
from typing import List
from shapely.geometry import Point
from src.config.iris_geocoding import IRISGeocodingConfig
from src.utils.helpers import catch_exceptions


class IRISGeocoder:
    """
    Responsible for performing spatial joins between tabular data and geospatial IRIS data.
    """

    def __init__(self, config: IRISGeocodingConfig) -> None:
        self.config = config

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
        df.set_crs(epsg=self.config.spatial_reference.epsg, inplace=True)
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
        result_df = result_df[
            old_columns + [col.name for col in self.config.geo_schema]
        ]
        result_df = result_df.rename(
            columns={col.name: col.value for col in self.config.geo_schema}
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
