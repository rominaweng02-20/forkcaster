"""The tools the harness can run, and the JSON that describes them to the model."""

import json

import requests

import math

# Open-Meteo, Nominatim and Overpass is free and needs no API key.
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "dont-know-what-to-eat-project/0.1 (rw2748@columbia.edu)"}


# Maps the category the model picks to an OpenStreetMap tag.
CATEGORY_TAGS = {
    "cafe": ("amenity", "cafe"),
    "restaurant": ("amenity", "restaurant"),
    "bar": [("amenity", "bar"), ("amenity", "pub")],
    "bakery": ("shop", "bakery"),
    "pub": ("amenity", "pub"),
    "fast_food": ("amenity", "fast_food"),
    "dessert_shop": [
        ("shop", "pastry"),
        ("shop", "confectionery"),
        ("amenity", "ice_cream"),
        ("shop", "chocolate"),
    ],
    "tea_shop": [("shop", "tea"), ("cuisine", "bubble_tea")],
    "library": ("amenity", "library"),
    "park": ("leisure", "park"),
    "cinema": ("amenity", "cinema"),
    "bookstore": ("shop", "books"),
    "work_spot": [
        ("amenity", "library"),
        ("office", "coworking"),
        ("amenity", "coworking_space"),
    ],
    "water_fountain": ("amenity", "drinking_water"),
    "food_court": ("amenity", "food_court"), 
}

CUISINE_ALIASES = {
    "italian": ["italian", "pizza", "pasta"],
    "pizza": ["pizza"],
    "chinese": ["chinese", "dim_sum", "noodle"],
    "japanese": ["japanese", "sushi", "ramen"],
    "sushi": ["sushi"],
    "ramen": ["ramen"],
    "korean": ["korean"],
    "thai": ["thai"],
    "vietnamese": ["vietnamese", "pho"],
    "indian": ["indian"],
    "mexican": ["mexican", "tacos"],
    "mediterranean": ["mediterranean", "greek", "turkish", "lebanese"],
    "american": ["american", "burger", "steak_house"],
    "burger": ["burger"],
    "french": ["french"],
    "seafood": ["seafood", "fish"],
    "vegetarian": ["vegetarian", "vegan"],
    "coffee": ["coffee_shop", "coffee"],
    "bakery": ["bakery", "pastry", "cake"],
}

CRITERION_HELP = {
    "kind_fits": "Type of place suits the occasion",
    "walkable": "Within walking distance (stricter when rainy)",
    "wifi": "Has Wi-Fi",
    "outdoor_seating": "Has outdoor seating",
    "indoor": "Is an indoor venue (matters when rainy)",
    "wheelchair": "Wheelchair accessible",
    "large_party": "Capacity fits the group (rarely tagged, so often unknown)",
    "reservations": "Takes reservations (important for celebrations)",

}

OCCASION_PROFILES = {
    "date_night": {
        "criteria": {"kind_fits": 4, "walkable": 2, "outdoor_seating": 2},
        "kinds": ["cafe", "bar", "pub", "restaurant", "ice_cream"],
        "categories": ["cafe", "bar", "dessert_shop"],
    },
    "work_session": {
        "criteria": {"wifi": 4, "kind_fits": 3, "walkable": 1},
        "kinds": ["cafe", "library", "coworking"],
        "categories": ["cafe", "work_spot"],
    },
    "group_meal": {
        "criteria": {"large_party": 4, "kind_fits": 3, "wheelchair": 1, "walkable": 1},
        "kinds": ["restaurant", "pub", "bar", "fast_food"],
        "categories": ["restaurant", "bar"],
    },
    "rainy_day": {
        "criteria": {"indoor": 4, "walkable": 3, "kind_fits": 1},
        "kinds": ["cafe", "library", "restaurant", "bakery", "cinema", "books"],
        "categories": ["cafe", "work_spot", "bakery"],
    },
    "family": {
        "criteria": {"kind_fits": 3, "walkable": 2, "wheelchair": 2, "outdoor_seating": 1},
        "kinds": ["restaurant", "ice_cream", "cafe", "park"],
        "categories": ["restaurant", "dessert_shop", "park"],
    },
    "anniversary": {
        "criteria": {"kind_fits": 4, "reservations": 3, "outdoor_seating": 1, "walkable": 1},
        "kinds": ["restaurant", "bar", "cafe"],
        "categories": ["restaurant", "bar", "dessert_shop"],
    },
    "birthday": {
        "criteria": {"kind_fits": 3, "reservations": 2, "large_party": 3, "wheelchair": 1, "walkable": 1},
        "kinds": ["restaurant", "pub", "bar", "ice_cream"],
        "categories": ["restaurant", "bar", "bakery", "dessert_shop"],
    },
    "milestone": {
        "criteria": {"kind_fits": 3, "reservations": 3, "large_party": 3, "wheelchair": 1},
        "kinds": ["restaurant", "bar", "pub"],
        "categories": ["restaurant", "bar"],
    },
}


def _distance_m(lat1, lon1, lat2, lon2) -> int:
    """Straight-line distance in meters (haversine)."""
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)))

def geocode_location(place_name: str) -> str:
    """Converts a place name or address into map coordinates."""
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": place_name, "format": "json", "limit": 1},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
    except (requests.RequestException, ValueError) as e:
        return json.dumps({"error": f"Geocoding service failed: {e}",
                           "hint": "Try again in a few minutes."})

    if not results:
        return json.dumps({
            "error": f"Could not find '{place_name}'.",
            "hint": "Try adding a specific city or state, e.g. 'Columbia University, New York'.",
        })

    top = results[0]
    return json.dumps({
        "name": top["display_name"],
        "lat": float(top["lat"]),
        "lon": float(top["lon"]),
    })


def search_places(lat: float, lon: float, category: str, radius_m: int = 800, cuisine: str | None= None) -> str:
    """Find nearby places of one category or cuisine type using OpenStreetMap data."""
    if category not in CATEGORY_TAGS:
        return json.dumps({
            "error": f"Unknown category '{category}'.",
            "hint": f"Use one of: {list(CATEGORY_TAGS)}",
        })

    radius_m = max(100, min(int(radius_m), 3000))  # keep queries small and fast
    cuisine_filter = ""
    if cuisine:
        cuisine_key = cuisine.strip().lower().replace(" ", "_")
        values = CUISINE_ALIASES.get(cuisine_key)
        if not values:
            return json.dumps({
                "error": f"Unknown cuisine '{cuisine}'.",
                "hint": f"Use one of: {list(CUISINE_ALIASES)}, or omit cuisine to search all.",
            })
        # Matches "italian" and also "italian;pizza", but not "non_italian".
        cuisine_filter = f'["cuisine"~"(^|;)({"|".join(values)})(;|$)"]'

# Works with one (key, value) tuple or a list of them.
    tag_pairs = CATEGORY_TAGS[category]
    if isinstance(tag_pairs, tuple):
        tag_pairs = [tag_pairs]

    # One line per tag; Overpass returns the union of all of them.
    tag_lines = "\n".join(
        f'  nwr["{key}"="{value}"]{cuisine_filter}(around:{radius_m},{lat},{lon});'
        for key, value in tag_pairs
    )    
    query = f"""
        [out:json][timeout:20];
        (
        {tag_lines}
        );
        out center tags 60;
    """
    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        elements = resp.json().get("elements", [])
    except (requests.RequestException, ValueError) as e:
        return json.dumps({
            "error": f"Place search failed: {e}",
            "hint": "Retry again by usinga smaller radius_m.",
        })

    places = []
    for el in elements:
        tags = el.get("tags", {})
        if "name" not in tags:
            continue  # skip unnamed places, they're useless to the user
        # Nodes have lat/lon directly; ways and relations have a "center".
        p_lat = el.get("lat") or el.get("center", {}).get("lat")
        p_lon = el.get("lon") or el.get("center", {}).get("lon")
        if p_lat is None or p_lon is None:
            continue
        places.append({
            "name": tags["name"],
            "distance_m": _distance_m(lat, lon, p_lat, p_lon),
            "lat": p_lat,
            "lon": p_lon,
            "address": " ".join(filter(None, [tags.get("addr:housenumber"), tags.get("addr:street")])) or None,
            "opening_hours": tags.get("opening_hours"),
            "outdoor_seating": tags.get("outdoor_seating"),
            "internet_access": tags.get("internet_access"),
            "wheelchair": tags.get("wheelchair"),
            "cuisine": tags.get("cuisine"),
        "reservation": tags.get("reservation"),
        "capacity": tags.get("capacity"),
        "kind": tags.get("amenity") or tags.get("shop") or tags.get("leisure") or tags.get("office"),
     })
    if not places:
        extra = f" with cuisine '{cuisine}'" if cuisine else ""
        return json.dumps({
            "error": f"No {category} places found within {radius_m} m{extra}.",
            "hint": "Try a larger radius_m (up to 3000), a different category, or drop the cuisine filter. "
                    "Cuisine tags are incomplete in OpenStreetMap, so a place may exist but be untagged.",
        })

    places.sort(key=lambda p: p["distance_m"])
    # Drop empty fields and cap the list so the model gets a short, clean result.
    trimmed = [{k: v for k, v in p.items() if v is not None} for p in places[:8]]
    return json.dumps({"category": category, "count": len(trimmed), "places": trimmed})

def get_weather(location: str) -> str:
    """Get the current weather for a location."""
    try:
        places = requests.get(GEOCODE_URL, params={"name": location, "count": 1}, timeout=10).json()
        if not places.get("results"):
            return json.dumps({"error": f"City '{location}' was not found."})
        place = places["results"][0]

        current = requests.get(
            FORECAST_URL,
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
            },
            timeout=10,
        ).json()["current"]
    except requests.RequestException as e:
        # The model cannot see an exception. Return something it can reason about.
        return json.dumps({"error": f"Weather service failed: {e}"})

    return json.dumps({
        "location": place["name"],
        "temp_f": current["temperature_2m"],
        "humidity": current["relative_humidity_2m"],
        "wind_mph": current["wind_speed_10m"],
    })

def _to_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_occasions(occasions):
    """Converts the ocassions into LIST format"""
    if isinstance(occasions, str):
        occasions = [occasions]
    if not isinstance(occasions, list) or not occasions:
        return None, "occasions must be a non-empty list."
    cleaned = [str(o).strip().lower().replace(" ", "_").replace("-", "_") for o in occasions]
    bad = [o for o in cleaned if o not in OCCASION_PROFILES]
    if bad:
        return None, f"Unknown occasion(s): {bad}."
    return cleaned, None


def _build_profile(occasions, party_size, duration_hours, is_rainy):
    """Merge one or more occasions into a single weighted profile."""
    criteria, kinds, categories = {}, set(), []
    for occ in occasions:
        p = OCCASION_PROFILES[occ]
        for name, weight in p["criteria"].items():
            criteria[name] = max(criteria.get(name, 0), weight)  # compound occasions: keep the stronger weight
        kinds |= set(p["kinds"])
        for category in p["categories"]:
            if category in CATEGORY_TAGS and category not in categories:  # only suggest categories search_places supports
                categories.append(category)

    rainy = bool(is_rainy) or "rainy_day" in occasions
    if party_size >= 5:
        criteria["large_party"] = max(criteria.get("large_party", 0), 4)
    if duration_hours >= 1.5 and "wifi" in criteria:
        criteria["wifi"] += 1  # long sessions care more about Wi-Fi
    if rainy:
        criteria.pop("outdoor_seating", None)
        criteria["indoor"] = max(criteria.get("indoor", 0), 3)

    return {
        "occasions": occasions,
        "party_size": party_size,
        "duration_hours": duration_hours,
        "rainy": rainy,
        "criteria": criteria,
        "kinds": sorted(kinds),
        "suggested_categories": categories,
        "max_walk_m": 500 if rainy else 800,
    }


def _eval_criterion(name, place, profile):
    """True = met, False = not met, None = unknown (the data is missing)."""
    if name == "kind_fits":
        kind = place.get("kind")
        return None if kind is None else kind in profile["kinds"]
    if name == "walkable":
        d = place.get("distance_m")
        return None if d is None else d <= profile["max_walk_m"]
    if name == "wifi":
        v = place.get("internet_access")
        return None if v is None else v in ("wlan", "yes", "wired")
    if name == "outdoor_seating":
        v = place.get("outdoor_seating")
        return None if v is None else v == "yes"
    if name == "indoor":
        kind = place.get("kind")
        return None if kind is None else kind not in ("park", "garden")
    if name == "wheelchair":
        v = place.get("wheelchair")
        return None if v is None else v == "yes"
    if name == "large_party":
        cap = _to_int(place.get("capacity"), None)
        return None if cap is None else cap >= profile["party_size"]
    if name == "reservations":
        v = place.get("reservation")
        if v is None:
            return None
        return v in ("yes", "required", "recommended")
    return None

def get_occasion_profile(occasions, party_size: int = 2, duration_hours: float = 2, is_rainy: bool = False) -> str:
    """Translate an occasion into weighted place criteria and suggested search categories."""
    occs, err = _normalize_occasions(occasions)
    if err:
        return json.dumps({"error": err, "hint": f"Valid occasions: {list(OCCASION_PROFILES)}"})
    profile = _build_profile(occs, _to_int(party_size, 2), float(duration_hours or 2), is_rainy)
    profile["criteria"] = {
        name: {"weight": w, "meaning": CRITERION_HELP[name]} for name, w in profile["criteria"].items()
    }
    return json.dumps(profile)



def score_places_for_occasion(places, occasions, party_size: int = 2, duration_hours: float = 2,
                              is_rainy: bool = False) -> str:
    """Score places from search_places (0-100) for an occasion and rank them."""
    occs, err = _normalize_occasions(occasions)
    if err:
        return json.dumps({"error": err, "hint": f"Valid occasions: {list(OCCASION_PROFILES)}"})
    if not isinstance(places, list) or not places or not all(isinstance(p, dict) for p in places):
        return json.dumps({"error": "places must be a non-empty list of place objects.",
                           "hint": "Pass the places returned by search_places."})

    profile = _build_profile(occs, _to_int(party_size, 2), float(duration_hours or 2), is_rainy)
    total_weight = sum(profile["criteria"].values())

    results = []
    for place in places:
        points, known_weight = 0.0, 0
        matched, missed, unknown = [], [], []
        for name, weight in profile["criteria"].items():
            outcome = _eval_criterion(name, place, profile)
            if outcome is None:
                unknown.append(name)
                points += 0.5 * weight          # unknown data counts as half credit
            elif outcome:
                matched.append(name)
                points += weight
                known_weight += weight
            else:
                missed.append(name)
                known_weight += weight
        results.append({
            "name": place.get("name", "(unnamed)"),
            "score": round(100 * points / total_weight),
            "confidence": round(known_weight / total_weight, 2),  # share of criteria we had data for
            "matched": matched,
            "missed": missed,
            "unknown": unknown,
            "distance_m": place.get("distance_m"),
        })

    results.sort(key=lambda r: (-r["score"], -r["confidence"], r["distance_m"] or 0))
    return json.dumps({
        "occasions": occs,
        "rainy": profile["rainy"],
        "note": "score = matched weight + half credit for unknown criteria, out of 100. Low confidence means little data.",
        "ranked": results[:8],
    })

# What the model sees: the "set notes" in the screenplay.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather (temperature, humidity, wind) for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name, e.g. 'New York'"},
                },
                "required": ["location"],
            },
        }
    },
{
        "type": "function",
        "function": {
            "name": "geocode_location",
            "description": (
                "Convert a place name or address into latitude/longitude. "
                "Call this first whenever the user mentions a location, "
                "before search_places. Returns name, lat, lon."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "place_name": {
                        "type": "string",
                        "description": "Place or address, with city if possible, e.g. 'Columbia University, New York'",
                    },
                },
                "required": ["place_name"],
            },
        },
    },
{
        "type": "function",
        "function": {
            "name": "search_places",
            "description": (
                "Find cafes, restaurants, bars, or bakeries near coordinates, sorted by distance. "
                "Returns up to 6 named places with distance in meters and optional details "
                "(opening_hours, outdoor_seating, internet_access, wheelchair, cuisine). "
                "Missing fields mean the data is unknown, not that the feature is absent. "
                "Get lat/lon from geocode_location first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude, e.g. 40.8075"},
                    "lon": {"type": "number", "description": "Longitude, e.g. -73.9626"},
                    "category": {
                        "type": "string",
                        "enum": ["cafe", "restaurant", "bar", "bakery"],
                        "description": "Type of place to search for",
                    },
                    "radius_m": {
                        "type": "integer",
                        "description": "Search radius in meters (100-3000). Default 800, roughly a 10-minute walk.",
                    },
                    "cuisine": {
                        "type": "string",
                        "enum": list(CUISINE_ALIASES),
                        "description": "Optional. Only return places serving this cuisine. Omit if not requested.",
                    },
                },
                "required": ["lat", "lon", "category"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_occasion_profile",
            "description": (
                "Explain what matters for an occasion (e.g. first date, work session) and get "
                "suggested search categories for search_places. Supports several occasions "
                "combined, such as ['group_meal', 'rainy_day']. Call this before searching "
                "when the user describes an occasion, to decide which categories to search."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "occasions": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(OCCASION_PROFILES)},
                        "description": "One or more occasions that apply",
                    },
                    "party_size": {"type": "integer", "description": "Number of people. Default 2."},
                    "duration_hours": {"type": "number", "description": "How long they will stay. Default 2."},
                    "is_rainy": {"type": "boolean", "description": "True if rain is forecast or the user mentions rain."},
                },
                "required": ["occasions"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "score_places_for_occasion",
            "description": (
                "Score and rank places for an occasion on a 0-100 scale, with which criteria "
                "matched, missed, or were unknown. Call it once with the places returned by "
                "search_places (copy the place objects as-is, including any rating fields from "
                "get_place_details). Unknown means missing data, not a failure. Use the ranked "
                "result to explain recommendations; do not invent details it does not contain."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "places": {
                        "type": "array",
                        "description": "Place objects from search_places",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "distance_m": {"type": "number"},
                                "kind": {"type": "string"},
                                "internet_access": {"type": "string"},
                                "outdoor_seating": {"type": "string"},
                                "wheelchair": {"type": "string"},
                                "capacity": {"type": "string"},
                            },
                            "required": ["name"],
                        },
                    },
                    "occasions": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(OCCASION_PROFILES)},
                        "description": "One or more occasions that apply",
                    },
                    "party_size": {"type": "integer", "description": "Number of people. Default 2."},
                    "duration_hours": {"type": "number", "description": "How long they will stay. Default 2."},
                    "is_rainy": {"type": "boolean", "description": "True if rain is forecast or the user mentions rain."},
                },
                "required": ["places", "occasions"],
            },
        },
    },
]

# What the harness runs: tool name -> Python function.
TOOL_MAP = {"get_weather": get_weather,
    "search_places": search_places,
    "geocode_location": geocode_location,
        "get_occasion_profile": get_occasion_profile,
        "score_places_for_occasion": score_places_for_occasion,
}

def run_tool(name: str, args: dict) -> str:
    """Run one tool call. Models invent tool names and arguments; never let that crash the loop."""
    if name not in TOOL_MAP:
        return json.dumps({"error": f"Unknown tool '{name}'. Available: {list(TOOL_MAP)}"})
    try:
        return TOOL_MAP[name](**args)
    except Exception as e:
        return json.dumps({"error": f"Tool {name} failed: {type(e).__name__}: {e}",
                           "hint": "Check the arguments and try again, or continue without this tool."})
