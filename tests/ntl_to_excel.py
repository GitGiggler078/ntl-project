# ntlproject-493423
import pandas as pd
from geopy.geocoders import Nominatim
from tqdm import tqdm
import time
import json
import os
import logging
import runpy
from pathlib import Path
import concurrent.futures
import threading
from functools import partial

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# ======================
# CONFIG
# ======================
def load_env():
    env_path = Path(".env")
    if load_dotenv and env_path.exists():
        load_dotenv(dotenv_path=env_path)

    global PROJECT_ID, CACHE_FILE, OUTPUT_FILE, ERROR_LOG, GEOPY_USER_AGENT, START_DATE, END_DATE, CITIES_FILE

    PROJECT_ID = os.getenv("GEE_PROJECT_ID")
    if not PROJECT_ID:
        raise RuntimeError("GEE_PROJECT_ID is required. Please set it in your environment or .env file.")

    CACHE_FILE = os.getenv("CACHE_FILE", "city_coords_cache.json")
    OUTPUT_FILE = os.getenv("OUTPUT_FILE", "city_ntl_2026.csv")
    ERROR_LOG = os.getenv("ERROR_LOG", "error.log")
    GEOPY_USER_AGENT = os.getenv("GEOPY_USER_AGENT", "ntl_extractor")
    START_DATE = os.getenv("START_DATE")
    END_DATE = os.getenv("END_DATE")

    if not START_DATE or not END_DATE:
        raise RuntimeError("START_DATE and END_DATE are required. Please set them in your environment or .env file.")

    CITIES_FILE = os.getenv("CITIES_FILE", "cities.py")

# ======================
# INIT
# ======================
def init_gee():
    ee.Initialize(project=PROJECT_ID)

# ======================
# LOGGING
# ======================
def setup_logging():
    logging.basicConfig(
        filename=ERROR_LOG,
        filemode="a",
        format="%(asctime)s | %(levelname)s | %(message)s",
        level=logging.ERROR
    )

# ======================
# CITY LIST
# ======================

def load_cities(file_path):
    if not os.path.exists(file_path):
        raise RuntimeError(
            f"CITIES_FILE not found: {file_path}. "
            "Create this file as a Python module defining `cities = [...]`."
        )

    if not file_path.endswith(".py"):
        raise RuntimeError(
            f"CITIES_FILE must be a Python file ending in .py, got {file_path}."
        )

    try:
        module_vars = runpy.run_path(file_path)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load cities from {file_path}: {exc}"
        ) from exc

    cities_list = module_vars.get("cities")
    if cities_list is None:
        raise RuntimeError(
            f"{file_path} must define a top-level variable named `cities`."
        )

    if not isinstance(cities_list, list) or not all(isinstance(city, str) for city in cities_list):
        raise RuntimeError(
            f"{file_path} must define `cities` as a list of strings."
        )

    cities_list = [city.strip() for city in cities_list if city.strip()]
    if not cities_list:
        raise RuntimeError(
            f"No cities found in {file_path}. Add string entries to the `cities` list."
        )

    return cities_list

if __name__ == "__main__":
    import ee
    load_env()
    init_gee()
    setup_logging()

    cities = load_cities(CITIES_FILE)

    # ======================
    # LOAD CACHE
    # ======================
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                city_coords = json.load(f)
        except (json.JSONDecodeError, IOError):
            city_coords = {}
            logging.warning(f"Could not load cache file {CACHE_FILE}, starting fresh")
    else:
        city_coords = {}

    geolocator = Nominatim(user_agent=GEOPY_USER_AGENT)

    # ======================
    # GEOCODING
    # ======================
    cached_count = sum(1 for city in cities if city in city_coords and city_coords[city] is not None)
    print(f"Geocoding cities... ({cached_count}/{len(cities)} cached)")

    # Thread-safe rate limiter
    rate_limiter = threading.Semaphore(1)  # Allow 1 request per second

    def geocode_city(city, geolocator):
        with rate_limiter:
            try:
                location = geolocator.geocode(f"{city}, India")
                time.sleep(1)  # Rate limit
                if location:
                    return city, [location.longitude, location.latitude]
                else:
                    logging.error(f"Geocoding failed: {city}")
                    return city, None
            except Exception as e:
                logging.error(f"Geocoding exception: {city} | {str(e)}")
                return city, None

    # Geocode only missing cities
    missing_cities = [city for city in cities if city not in city_coords]

    if missing_cities:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            geocode_partial = partial(geocode_city, geolocator=geolocator)
            results = list(tqdm(executor.map(geocode_partial, missing_cities), total=len(missing_cities)))
            
            for city, coords in results:
                city_coords[city] = coords

    # Save cache
    with open(CACHE_FILE, "w") as f:
        json.dump(city_coords, f, indent=2)

    # ======================
    # LOAD NTL DATA
    # ======================
    ntl = ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG") \
        .filterDate(START_DATE, END_DATE)

    # Correct band + yearly mean
    mean_img = ntl.select("avg_rad").mean()

    # Remove extreme outliers
    mean_img = mean_img.updateMask(mean_img.lt(100))

    # ======================
    # CREATE FEATURES (BUFFER FIX)
    # ======================
    features = []

    for city in cities:
        coords = city_coords.get(city)

        if coords:
            geom = ee.Geometry.Point(coords).buffer(7000)  # 7 km buffer
            features.append(ee.Feature(geom, {"city": city}))
        else:
            logging.error(f"Missing coords: {city}")

    fc = ee.FeatureCollection(features)

    # ======================
    # EXTRACT NTL
    # ======================
    print("Extracting NTL data...")

    try:
        result = mean_img.reduceRegions(
            collection=fc,
            reducer=ee.Reducer.mean(),
            scale=500
        ).getInfo()
    except Exception as e:
        logging.error(f"GEE failure: {str(e)}")
        result = None

    # ======================
    # PARSE RESULTS
    # ======================
    results = {}

    if result:
        for f in result["features"]:
            city = f["properties"]["city"]
            val = f["properties"].get("mean")
            if val is None:
                logging.error(f"No value: {city}")

            results[city] = val

    # ======================
    # OUTPUT
    # ======================
    output = pd.DataFrame({
        "City": cities,
        "NTL_2026_mean": [results.get(city) for city in cities]
    })

    output = output.dropna(subset=["NTL_2026_mean"])
    output["NTL_2026_mean"] = output["NTL_2026_mean"].round(2)

    output.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved NTL output to {OUTPUT_FILE}")

    # Save both formats
    output.to_csv("city_ntl_2026.csv", index=False)
    output.to_excel("city_ntl_2026.xlsx", index=False)

    print("Done")
    print("Files created: city_ntl_2026.csv, city_ntl_2026.xlsx")
    print("Check error.log if needed")