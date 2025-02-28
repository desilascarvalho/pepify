import requests
import logging
import os
from PIL import Image
from io import BytesIO
import unidecode

logging.basicConfig(level=logging.INFO)

def get_image_size(device_type):
    sizes = {
        'mobile': (120, 120),
        'tablet': (200, 200),
        'desktop': (300, 300)
    }
    return sizes.get(device_type, sizes['mobile'])

def search_deezer_artist(query, device_type='mobile'):
    url = f"https://api.deezer.com/search/artist?q={query}&limit=10"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        data = response.json().get('data', [])
        logging.info(f"Resultados da busca para {query}: {data}")
        exact_match = next((artist for artist in data if artist['name'].lower() == query.lower()), None)
        if exact_match:
            return [{"id": exact_match["id"], "name": exact_match["name"], "picture": cache_image(exact_match["picture_big"], exact_match["name"], device_type)}]
        return [{"id": artist["id"], "name": artist["name"], "picture": cache_image(artist["picture_big"], artist["name"], device_type)} for artist in data if artist]
    logging.error(f"Erro ao buscar artista na API Deezer (status {response.status_code}): {response.text}")
    return []

def get_artist_info(artist_id, device_type='mobile'):
    url = f"https://api.deezer.com/artist/{artist_id}"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        data = response.json()
        logging.info(f"Informações do artista {artist_id}: {data}")
        picture = data.get("picture_big", "")
        if picture:
            picture = cache_image(picture, data.get("name", ""), device_type)
        return {
            "picture": picture,
            "name": data.get("name", "")
        }
    logging.error(f"Erro ao obter info do artista {artist_id} na API Deezer (status {response.status_code}): {response.text}")
    return {"picture": "https://via.placeholder.com/150", "name": ""}

def cache_image(url, artist_name, device_type):
    cache_dir = os.path.join("/app", "frontend", "static", "images")
    os.makedirs(cache_dir, exist_ok=True)
    width, height = get_image_size(device_type)
    filename = f"{normalize_name(artist_name)}_{width}x{height}.webp"
    cache_path = os.path.join(cache_dir, filename)
    
    if not os.path.exists(cache_path):
        try:
            logging.info(f"Tentando baixar imagem de {url} para {cache_path}")
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
            new_img = Image.new('RGB', (width, height), (255, 255, 255))
            paste_position = ((width - img.width) // 2, (height - img.height) // 2)
            new_img.paste(img, paste_position)
            new_img.save(cache_path, "WEBP", quality=85, optimize=True)
            logging.info(f"Imagem cached com sucesso para {artist_name} ({width}x{height}) em {cache_path}")
        except (requests.RequestException, IOError, TimeoutError) as e:
            logging.error(f"Falha ao cachear imagem para {artist_name} de {url}: {str(e)}")
            return f"https://via.placeholder.com/{width}x{height}"

    return f"/static/images/{filename}"

def normalize_name(name):
    if not name:
        return ""
    return unidecode.unidecode(name.strip().lower()).replace(" ", "_")