import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
SITES_DIR = os.path.join(DATA_DIR, "sites")
ARTIFACTS_DIR = os.path.join(DATA_DIR, "artifacts")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
SEGMENTS_DIR = os.path.join(DATA_DIR, "segments")
SVGS_DIR = os.path.join(DATA_DIR, "svgs")
EMBEDDINGS_DIR = os.path.join(DATA_DIR, "embeddings")
SIMILARITY_DIR = os.path.join(DATA_DIR, "similarity")
CLUSTERS_DIR = os.path.join(DATA_DIR, "clusters")
MANIFESTS_DIR = os.path.join(DATA_DIR, "manifests")
EXPORT_DIR = os.path.join(PROJECT_ROOT, "web", "public", "data")
RAW_PLACES = os.path.join(RAW_DIR, "places.json")

PIPELINE_MODE = os.environ.get("PIPELINE_MODE", "dev")

WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_USER_AGENT = "AncientLocsBot/1.0 (https://github.com/ebrinz/ancient-locs)"
WIKIDATA_QUERY_TIMEOUT = 60

MET_MUSEUM_API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
MET_MUSEUM_RATE_LIMIT = 1.0

BM_SPARQL_ENDPOINT = "https://collection.britishmuseum.org/sparql"
BM_RATE_LIMIT = 2.0

HARVARD_API_BASE = "https://api.harvardartmuseums.org"
HARVARD_API_KEY = os.environ.get("HARVARD_API_KEY", "")
HARVARD_DAILY_LIMIT = 2500

WIKIMEDIA_API_BASE = "https://commons.wikimedia.org/w/api.php"
WIKIMEDIA_USER_AGENT = WIKIDATA_USER_AGENT

SITE_MATCH_RADIUS_KM = 5.0
SITE_NAME_FUZZY_THRESHOLD = 3

CLIPSEG_PROMPTS = [
    "decorative motif", "carved pattern", "painted design",
    "geometric decoration", "engraved symbol",
]
SEGMENT_MIN_AREA_RATIO = 0.03
SEGMENT_MAX_AREA_RATIO = 0.40
SEGMENT_MIN_COMPLEXITY = 10.0
SEGMENT_MAX_ASPECT_RATIO = 5.0

CLIP_MODEL = "openai/clip-vit-base-patch32"
CLIPSEG_MODEL = "CIDAS/clipseg-rd64-refined"

SVG_MIN_PATHS = 5
SVG_MAX_PATHS = 5000

SIMILARITY_TOP_N = 20
SIMILARITY_EMBEDDING_WEIGHT = 0.7
SIMILARITY_TAG_WEIGHT = 0.3

HDBSCAN_MIN_CLUSTER_SIZES = [5, 15, 30, 50]

EXPORT_SIZE_BUDGET_MB = 50
SIMILARITY_EXPORT_TOP_N = 10

DEV_MAX_SITES = 100
DEV_MAX_ARTIFACTS_PER_SITE = 10
