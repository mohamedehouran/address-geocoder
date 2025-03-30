import glob
import pandas as pd
import geopandas as gpd
from enum import Enum
from typing import List
from pathlib import Path
from dataclasses import dataclass
from src.config.app import AppConfig, app_config
from src.config.config_validator import validate_dir_exists
from src.utils.helpers import catch_exceptions


class IrisGeoSchema(Enum):
    """
    Schema used in IRIS GeoJSON data.
    """

    CODE_IRIS = "iris_code"
    INSEE_COM = "municipality_code"
    NOM_COM = "municipality_name"
    IRIS = "iris"
    NOM_IRIS = "iris_name"
    TYP_IRIS = "iris_type"


@dataclass(frozen=True)
class SpatialReference:
    """
    Defines the default spatial reference system.
    """

    crs: str = "EPSG:4326"
    epsg: int = 4326


class IRISGeocodingConfig:
    """
    Configuration class for IRIS geocoding.
    """

    def __init__(self, app_config: AppConfig):
        self.app_dir = app_config.directory_manager
        self.geo_schema: IrisGeoSchema = IrisGeoSchema
        self.spatial_reference: SpatialReference = SpatialReference
        self.geojson_dir: Path = self._get_geojson_dir()

        self.__post_init__()

    def __post_init__(self):
        validate_dir_exists(self.geojson_dir)

    @catch_exceptions
    def _get_geojson_dir(self) -> Path:
        """
        Retrieves the directory path for IRIS GeoJSON files.
        """
        return (
            self.app_dir.get_directory_path(self.app_dir.directory.CONFIG)
            / "iris_geojson"
        )

    @catch_exceptions
    def _load_geojson_files(self) -> List[gpd.GeoDataFrame]:
        """
        Loads all GeoJSON files from the directory and converts them into GeoDataFrames.
        """
        geojson_dir = self._get_geojson_dir()
        file_paths = glob.glob(f"{geojson_dir}/*")
        geojson_list = []

        for file_path in file_paths:
            gdf = gpd.read_file(file_path)

            if gdf.crs != self.spatial_reference.crs:
                gdf = gdf.to_crs(self.spatial_reference.crs)

            geojson_list.append(gdf)
        return geojson_list

    @catch_exceptions
    def _combine_geojson_to_gdf(
        self, geojson_list: List[gpd.GeoDataFrame]
    ) -> gpd.GeoDataFrame:
        """
        Merges multiple GeoDataFrames into a single GeoDataFrame.
        """
        return gpd.GeoDataFrame(
            pd.concat(geojson_list, ignore_index=True), crs=self.spatial_reference.crs
        )

    @catch_exceptions
    def get_iris_gdf(self) -> gpd.GeoDataFrame:
        """
        Returns a combined GeoDataFrame of all IRIS GeoJSON files.
        """
        geojson_list = self._load_geojson_files()
        return self._combine_geojson_to_gdf(geojson_list)


iris_geocoding_config = IRISGeocodingConfig(app_config=app_config)
