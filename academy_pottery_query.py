import requests
import json
from math import radians, sin, cos, sqrt, atan2
from PIL import Image
from io import BytesIO

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def get_academy_coordinates():
    with open('places.json', 'r') as f:
        places = json.load(f)
    
    for place in places:
        if place['name'] == 'Academy of Plato':
            lat = float(place['latitude'].replace(' N', ''))
            lon = float(place['longitude'].replace(' E', ''))
            return lat, lon
    raise ValueError("Academy of Plato not found in places.json")

def get_pottery_images():
    base_url = "https://arachne.dainst.org/data/search"
    headers = {
        "Accept": "application/json",
        "User-Agent": "Research Bot (Archaeological Data Collection)"
    }
    
    # Get Academy of Plato coordinates from places.json
    academy_lat, academy_lon = get_academy_coordinates()
    
    query = {
        "q": "(keramik OR vessel OR amphora OR vase OR hydria OR krater) AND thumbnailId:[* TO *]",
        "fq": "type:Einzelobjekte",
        "limit": 500,
        "offset": 0
    }
    
    print(f"Fetching pottery items near Academy of Plato...")
    try:
        response = requests.get(
            base_url,
            params=query,
            headers=headers,
            timeout=30
        )
        result = response.json()
        
        print(f"Total results: {result.get('size', 0)}")
        
        if result.get('size', 0) > 0:
            entities = result.get('entities', [])
            
            nearby_items = []
            
            for entity in entities:
                if entity.get('places'):
                    for item_place in entity['places']:
                        if item_place.get('location'):
                            item_lat = float(item_place['location']['lat'])
                            item_lon = float(item_place['location']['lon'])
                            
                            distance = haversine_distance(
                                academy_lat, academy_lon,
                                item_lat, item_lon
                            )
                            
                            if distance <= 10:  # Within 10km
                                nearby_items.append({
                                    'title': entity.get('title'),
                                    'id': entity.get('entityId'),
                                    'distance': distance,
                                    'place': item_place.get('name'),
                                    'relation': item_place.get('relation'),
                                    'thumbnail': entity.get('thumbnailId'),
                                    'subtitle': entity.get('subtitle')
                                })
            
            if nearby_items:
                print(f"Found {len(nearby_items)} nearby items:")
                for item in nearby_items:
                    print(f"\n- {item['title']}")
                    print(f"  ID: {item['id']}")
                    print(f"  Distance: {item['distance']:.2f}km")
                    print(f"  Location: {item['place']} ({item['relation']})")
                    if item['subtitle']:
                        print(f"  Details: {item['subtitle']}")
                    print(f"  Image: https://arachne.dainst.org/data/image/{item['thumbnail']}")
                    image_url = f"https://arachne.dainst.org/data/image/{item['thumbnail']}"
                    response = requests.get(image_url)
                    image = Image.open(BytesIO(response.content))
                    image.show()
            else:
                print("No nearby items found")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    get_pottery_images() 