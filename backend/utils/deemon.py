import subprocess
import threading
from collections import defaultdict
import os
from datetime import datetime
from flask_socketio import SocketIO
import logging
from utils.deezer import search_deezer_artist, get_artist_info
from difflib import SequenceMatcher
import unidecode

logging.basicConfig(level=logging.INFO)

download_status = defaultdict(lambda: {"status": "Pendente", "message": ""})

def normalize_name(name):
    if not name:
        return ""
    return unidecode.unidecode(name.strip().lower())

def update_metadata(artist_name, download_path="/downloads"):
    try:
        artist_dir = os.path.join(download_path, artist_name)
        if not os.path.exists(artist_dir):
            print(f"Diretório de artista não encontrado: {artist_dir}")
            return

        for file in os.listdir(artist_dir):
            file_path = os.path.join(artist_dir, file)
            if file.endswith(('.mp3', '.flac', '.m4a')):
                print(f"Aplicando metadados em: {file_path}")
                try:
                    from mutagen.easyid3 import EasyID3
                    from mutagen.id3 import ID3, TALB, TPE1, TPE2
                    from mutagen import File
                    audio = File(file_path, easy=True)
                    if audio is None:
                        print(f"Formato não suportado ou erro ao carregar: {file_path}")
                        continue
                    if hasattr(audio, 'tags'):
                        if 'albumartist' in audio:
                            audio['albumartist'] = [artist_name]
                        else:
                            audio.add(TPE2(encoding=3, text=[artist_name]))
                        if 'artist' in audio:
                            audio['artist'] = [artist_name]
                        else:
                            audio.add(TPE1(encoding=3, text=[artist_name]))
                        audio.save()
                        print(f"Metadados atualizados para {file_path}")
                    else:
                        audio.add(TPE2(encoding=3, text=[artist_name]))
                        audio.add(TPE1(encoding=3, text=[artist_name]))
                        audio.save()
                        print(f"Metadados criados para {file_path}")
                except Exception as e:
                    print(f"Erro ao atualizar metadados para {file_path}: {e}")
    except Exception as e:
        print(f"Erro ao atualizar metadados para {artist_name}: {e}")

def monitor_with_progress(artist_name, socketio: SocketIO):
    normalized_name = normalize_name(artist_name)
    download_path = "/downloads"
    socketio.emit('progress', {'artist': artist_name, 'status': 'Iniciando monitoramento...'})
    download_status[artist_name]["status"] = "Em andamento"
    
    artist_dir = os.path.join(download_path, artist_name)
    os.makedirs(artist_dir, exist_ok=True)

    deezer_artists = search_deezer_artist(artist_name)
    if not deezer_artists:
        socketio.emit('progress', {'artist': artist_name, 'status': 'Erro: Artista não encontrado na API Deezer'})
        download_status[artist_name]["status"] = "Erro"
        logging.error(f"Artista {artist_name} não encontrado na API Deezer")
        return

    best_match = max(deezer_artists, key=lambda x: SequenceMatcher(None, normalized_name, normalize_name(x['name'])).ratio(), default=None)
    if not best_match:
        socketio.emit('progress', {'artist': artist_name, 'status': 'Erro: Nenhum match encontrado na API Deezer'})
        download_status[artist_name]["status"] = "Erro"
        logging.error(f"Nenhum match encontrado na API Deezer para {artist_name}")
        return

    validated_name = best_match['name']
    logging.info(f"Usando nome validado para download: {validated_name}")

    cmd = ["deemon", "monitor", validated_name, "-D"]
    logging.info(f"Executando comando: {' '.join(cmd)}")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    socketio.emit('progress', {'artist': artist_name, 'status': 'Baixando músicas do artista...'})
    
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            status = output.strip()
            socketio.emit('progress', {'artist': artist_name, 'status': f'Progresso: {status}'})
    
    stdout, stderr = process.communicate()
    if process.returncode == 0:
        download_status[artist_name]["status"] = "Concluído"
        socketio.emit('progress', {'artist': artist_name, 'status': 'Concluído'})
        metadata_thread = threading.Thread(target=update_metadata, args=(artist_name,))
        metadata_thread.start()
    else:
        download_status[artist_name]["status"] = "Erro"
        socketio.emit('progress', {'artist': artist_name, 'status': f'Erro: {stderr}'})
        logging.error(f"Erro ao monitorar e baixar artista {artist_name}: {stderr}")

def get_monitored_artists(sort_by='name', page=1, per_page=14, device_type='mobile'):
    download_path = "/downloads"
    if not os.path.exists(download_path):
        logging.warning(f"Diretório /downloads não encontrado. Nenhum artista monitorado ainda.")
        return [], 0

    monitored = []
    for artist_name in os.listdir(download_path):
        artist_dir = os.path.join(download_path, artist_name)
        if os.path.isdir(artist_dir):
            normalized_name = normalize_name(artist_name)
            deezer_artists = search_deezer_artist(artist_name, device_type)
            if deezer_artists:
                best_match = max(deezer_artists, key=lambda x: SequenceMatcher(None, normalized_name, normalize_name(x['name'])).ratio(), default=None)
                if best_match:
                    artist_info = get_artist_info(best_match['id'], device_type)
                    monitored.append({
                        "name": artist_name,
                        "picture": artist_info["picture"],
                        "date": datetime.now().isoformat()
                    })
                else:
                    logging.warning(f"Nenhum match encontrado na API Deezer para {artist_name}. Usando imagem padrão.")
                    monitored.append({
                        "name": artist_name,
                        "picture": "",
                        "date": datetime.now().isoformat()
                    })
            else:
                logging.warning(f"Nenhum artista encontrado na API Deezer para {artist_name}. Usando imagem padrão.")
                monitored.append({
                    "name": artist_name,
                    "picture": "",
                    "date": datetime.now().isoformat()
                })

    if sort_by == 'name':
        monitored.sort(key=lambda x: x['name'].lower())
    elif sort_by == 'date':
        monitored.sort(key=lambda x: x['date'], reverse=True)

    start = (page - 1) * per_page
    end = start + per_page
    return monitored[start:end], len(monitored)

def get_artist_details(artist_name):
    artist_path = os.path.join("/downloads", artist_name)
    if not os.path.exists(artist_path) or not os.path.isdir(artist_path):
        return {"exists": False}
    return {"exists": True}