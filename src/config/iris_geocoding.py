import glob
import pandas as pd
import geopandas as gpd
from enum import Enum
from typing import List
from pathlib import Path
from dataclasses import dataclass
from src.config.app import AppConfig
from src.config.config_validator import validate_dir_exists


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
class IrisSpatialReference:
    """
    Spatial reference for IRIS GeoJSON data.
    """

    CRS: str = "EPSG:4326"
    EPSG: int = 4326


class IrisGeoJsonLoader:
    """
    Loads and processes IRIS GeoJSON files into a GeoDataFrame.
    """

    def __init__(self, app_config: AppConfig) -> None:
        self.app_config = app_config

        self.__post_init__()

    def __post_init__(self):
        self.dir_manager = self.app_config.directory_manager
        self.geojson_dir = self._get_geojson_dir()

        validate_dir_exists(self.geojson_dir)

    def _get_geojson_dir(self) -> Path:
        """
        Retrieves the directory path for IRIS GeoJSON files.
        """
        return (
            self.dir_manager.get_directory_path(self.dir_manager.directories.CONFIG)
            / "iris_geojson"
        )

    def _load_geojson_files(self) -> List[gpd.GeoDataFrame]:
        """
        Loads all GeoJSON files from the directory and converts them into GeoDataFrames.
        """
        try:
            geojson_dir = self._get_geojson_dir()
            file_paths = glob.glob(f"{geojson_dir}/*")
            geojson_list = []

            for file_path in file_paths:
                gdf = gpd.read_file(file_path)

                if gdf.crs != IrisSpatialReference.CRS:
                    gdf = gdf.to_crs(IrisSpatialReference.CRS)

                geojson_list.append(gdf)
            return geojson_list
        except Exception as e:
            raise RuntimeError(f"Unexpected error occurred loading GeoJSON files : {e}")

    def _combine_geojson_to_gdf(
        self, geojson_list: List[gpd.GeoDataFrame]
    ) -> gpd.GeoDataFrame:
        """
        Merges multiple GeoDataFrames into a single GeoDataFrame.
        """
        try:
            return gpd.GeoDataFrame(
                pd.concat(geojson_list, ignore_index=True),
                crs=IrisSpatialReference.CRS,
            )
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error occurred combining GeoJSON files to GeoDataFrame : {e}"
            )

    def get_iris_gdf(self) -> gpd.GeoDataFrame:
        """
        Returns a combined GeoDataFrame of all IRIS GeoJSON files.
        """
        try:
            geojson_list = self._load_geojson_files()
            return self._combine_geojson_to_gdf(geojson_list)
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error occurred retrieving IRIS GeoDataFrame : {e}"
            )
