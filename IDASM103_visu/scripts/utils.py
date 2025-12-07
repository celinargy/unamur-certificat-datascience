import numpy as np
import geopandas as gpd
import pandas as pd
from shapely import wkt
from pathlib import Path

# Création de variable de dossier pour retrouver les chemins
PROJECT_ROOT=Path(__file__).resolve().parent.parent
DATA_DIR=PROJECT_ROOT/"data"
PROCESSED_DIR=DATA_DIR/"processed"
RAW_DIR=DATA_DIR/"raw"



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


def populate_neighbourhood(df, nta_csv_path="../data/raw/2020_Neighborhood_Tabulation_Areas_(NTAs)_20251117.csv"):
    """
    Ajoute le quartier (NTA) correspondant à chaque point (longitude, latitude)
    à partir du fichier CSV des NTAs contenant une colonne WKT 'the_geom'.

    Paramètres
    ----------
    df : pandas.DataFrame
        Doit contenir 'longitude' et 'latitude'.
    nta_csv_path : str
        Fichier CSV contenant les polygones NTA au format WKT.

    Return
    ------
    pandas.DataFrame
        Colonnes ajoutées : NTA2020, NTAName, NTAAbbrev
    """

    # Charger le CSV NTA
    nta_df = pd.read_csv(nta_csv_path)

    # Convertir la géométrie WKT → objet shapely
    nta_df["geometry"] = nta_df["the_geom"].apply(wkt.loads)

    # Construire GeoDataFrame des NTA
    gdf_nta = gpd.GeoDataFrame(nta_df, geometry="geometry", crs="EPSG:4326")

    # Construire GeoDataFrame des points (df initial)
    gdf_points = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.longitude, df.latitude),
        crs="EPSG:4326"
    )

    # Jointure spatiale
    joined = gpd.sjoin(gdf_points, gdf_nta, how="left", predicate="within")

    # Colonnes à extraire
    neighbourhood_info = joined[["NTA2020", "NTAName", "NTAAbbrev"]].copy()
    neighbourhood_info.index = df.index  # conserver index original

    return neighbourhood_info

def load_airbnb_as_points(airbnb_csv_path):
    '''
    On transforme les lat/long des airbnb en points géométrique afin de pouvoir replacer 
    les remettre de façon propre dans les bons neighborhoods
    '''
    airbnb_csv_path=airbnb_csv_path
    df = pd.read_csv(airbnb_csv_path)

    # Dans ton fichier : colonnes 'lat' et 'long'
    gdf_airbnb = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["long"], df["lat"]),
        crs="EPSG:4326"
    )
    return gdf_airbnb


def assign_nta_to_airbnb(
    airbnb_csv_path:Path=PROCESSED_DIR/"Airbnb.csv",
    nta_csv_path:Path=RAW_DIR/"2020_Neighborhood_Tabulation_Areas_(NTAs)_20251117.csv",
    predicate="within" 
):
    '''
    On fait le lien entre les airbnb et les neighborhoods afin de replacer les premiers correctement dans le second
    Cela évite d'avoir des noms de neighborhood trop génériques (ex Upper West Side => Upper West Side -> Lincoln)
    '''
    airbnb_csv_path=Path(airbnb_csv_path)
    nta_csv_path=Path(nta_csv_path)
 
    # Charger
    gdf_airbnb = load_airbnb_as_points(airbnb_csv_path)
    nta_df = pd.read_csv(nta_csv_path)
    nta_df["geometry"] = nta_df["the_geom"].apply(wkt.loads)

    gdf_nta = gpd.GeoDataFrame(
        nta_df,
        geometry="geometry",
        crs="EPSG:4326"
    )

    # On garde les colonnes intéressantes
    gdf_nta = gdf_nta[["NTA2020", "NTAName", "NTAAbbrev", "BoroName", "geometry"]]
    # Jointure spatiale point-dans-polygone
    joined = gpd.sjoin(
        gdf_airbnb,
        gdf_nta,
        how="left",
        predicate=predicate,
        lsuffix="",
        rsuffix="_nta"
    )

    # Renommer les colonnes NTA pour ne pas écraser si besoin
    joined = joined.rename(columns={
        "NTA2020": "NTA2020_geom",
        "NTAName": "NTAName_geom",
        "NTAAbbrev": "NTAAbbrev_geom",
        "BoroName": "BoroName_geom",
    })

    # Nettoyage colonne technique
    if "index_right" in joined.columns:
        joined = joined.drop(columns=["index_right"])

    # # Sauvegarde éventuelle
    # if output_path is not None:
    #     # Si tu ne veux pas garder la géométrie, tu peux faire :
    #     joined.drop(columns=["geometry"]).to_csv(output_path, index=False)
    return joined


def add_fake_reviews(df, seed=42):
    np.random.seed(seed)

    n_reviews = np.random.lognormal(mean=1.5, sigma=1.0, size=len(df)).astype(int)

    score_choices = [1, 2, 3, 4, 5]
    probabilities = [0.05, 0.10, 0.20, 0.35, 0.30]

    base_scores = np.random.choice(score_choices, size=len(df), p=probabilities)

    # 3. Ajustement : plus il y a de reviews, plus le score se stabilise vers 4–5
    adjusted_scores = []
    for score, n in zip(base_scores, n_reviews):
        if n < 5:
            # très variable
            s = np.random.randint(1, 6)
        elif n < 50:
            # légèrement biaisé vers le base_score
            s = int(np.clip(np.random.normal(loc=score, scale=0.7), 1, 5))
        else:
            # gros nombre de reviews → score élevé
            s = int(np.clip(np.random.normal(loc=max(score, 4), scale=0.4), 1, 5))
        adjusted_scores.append(s)

    df["Number_of_reviews"] = n_reviews
    df["Review_score"] = adjusted_scores
    return df
