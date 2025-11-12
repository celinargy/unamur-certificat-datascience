import geopandas as gpd


def populate_unknown_borough(df):
    """
        This function populates the borough name based on the latitude and longitude of the entry
        requires: df with lat and long fields (numeric)
    """
    BOROUGHTS_BOUNDARIES = gpd.read_file("../data/raw/Borough_Boundaries_20251110.geojson")

    gdf_unknown = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.long, df.lat),
        crs="EPSG:4326"
    ) 

    joined = gpd.sjoin(gdf_unknown, BOROUGHTS_BOUNDARIES, how="left", predicate="within")

    joined = joined.rename(columns={'boroname': 'BOROUGH NAME'})

    borough_info = joined[['BOROUGH NAME']].copy()
    borough_info.index = joined.index

    return borough_info

    
