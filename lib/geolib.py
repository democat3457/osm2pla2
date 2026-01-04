import geopandas as gpd

class Projections:
    WGS84 = 'EPSG:4326'
    GMAPS = 'EPSG:3857'
    UTM_15N = 'EPSG:26915'

class CoordsUtil:
    @staticmethod
    def _to_projected_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        if not gdf.crs.is_projected:
            gdf = gdf.to_crs(gdf.estimate_utm_crs())
        return gdf

    @staticmethod
    def buffer_points(distance_meters: float, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        old_crs = gdf.crs
        gdf = CoordsUtil._to_projected_crs(gdf)
        proj_geoseries: gpd.GeoSeries = gdf.buffer(distance_meters)
        if old_crs:
            proj_geoseries = proj_geoseries.to_crs(old_crs)
        return gpd.GeoDataFrame(geometry=proj_geoseries)

    @staticmethod
    def coord_distance(gdf1: gpd.GeoDataFrame, gdf2: gpd.GeoDataFrame) -> float:
        gdf1 = CoordsUtil._to_projected_crs(gdf1)
        gdf2 = CoordsUtil._to_projected_crs(gdf2)
        return gdf1.distance(gdf2, align=False).iloc[0]