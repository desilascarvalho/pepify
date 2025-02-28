import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_socketio import SocketIO, emit
import threading
import os
import logging
from difflib import SequenceMatcher
from utils.config import load_deemon_config, load_deemix_config, save_config
from utils.deezer import search_deezer_artist, get_artist_info
from utils.deemon import monitor_with_progress, download_status, get_monitored_artists, get_artist_details

logging.basicConfig(level=logging.INFO)

app = Flask(__name__, template_folder="frontend/templates", static_folder="frontend/static")
socketio = SocketIO(app, async_mode='eventlet')

@app.route('/static/images/<path:filename>')
def serve_cached_image(filename):
    return send_from_directory(os.path.join(app.root_path, 'frontend', 'static', 'images'), filename)

def initialize_scripts():
    pass

@app.route("/", methods=["GET", "POST"])
def index():
    artists = []
    message = ""
    device_type = 'mobile'  # Simulado
    if request.method == "POST":
        logging.info(f"Recebida solicitação POST: {request.form}")
        query = request.form.get("query")
        action = request.form.get("action")
        if action == "monitor":
            artist_name = request.form.get("artist_name")
            thread = threading.Thread(target=monitor_with_progress, args=(artist_name, socketio))
            thread.start()
            message = f"Monitoramento iniciado para '{artist_name}'"
        elif query:
            logging.info(f"Buscando artista: {query}")
            artists = search_deezer_artist(query, device_type)
            logging.info(f"Resultados da busca: {artists}")
    else:
        query = request.args.get("query")
        if query:
            logging.info(f"Busca GET para: {query}")
            artists = search_deezer_artist(query, device_type)
            logging.info(f"Resultados da busca GET: {artists}")
    return render_template("index.html", artists=artists, message=message, download_status=download_status)

@app.route("/artists")
def artists():
    sort_by = request.args.get('sort', 'name')
    page = int(request.args.get('page', 1))
    per_page = 14
    device_type = 'mobile'  # Simulado
    monitored_artists, total_artists = get_monitored_artists(sort_by, page, per_page, device_type)
    total_pages = (total_artists + per_page - 1) // per_page
    return render_template("artists.html", monitored_artists=monitored_artists, page=page, total_pages=total_pages, sort_by=sort_by, download_status=download_status)

@app.route("/artist/<artist_name>")
def artist_detail(artist_name):
    details = get_artist_details(artist_name)
    if not details.get("exists", False):
        return "Artista não encontrado", 404
    device_type = 'mobile'  # Simulado
    deezer_artists = search_deezer_artist(artist_name, device_type)
    if not deezer_artists:
        logging.warning(f"Nenhum artista encontrado na API Deezer para {artist_name}")
        return "Artista não encontrado na API Deezer", 404
    best_match = max(deezer_artists, key=lambda x: SequenceMatcher(None, artist_name.lower(), x['name'].lower()).ratio(), default=None)
    if not best_match:
        logging.warning(f"Nenhum match encontrado na API Deezer para {artist_name}")
        return "Artista não encontrado na API Deezer", 404
    artist_id = best_match['id']
    artist_info = get_artist_info(artist_id, device_type)
    logging.info(f"### Informações do artista para {artist_name} (ID: {artist_id}, Nome na API: {best_match['name']}): {artist_info}")
    return render_template("artist_detail.html", artist_name=artist_name, artist_info=artist_info)

@app.route("/config", methods=["GET", "POST"])
def config():
    deemon_config = load_deemon_config()
    deemix_config = load_deemix_config()
    dark_mode = deemon_config.get("global", {}).get("dark_mode", False)
    if request.method == "POST":
        logging.info(f"Recebida solicitação POST para configuração: {request.form}")
        arl = request.form.get("arl", "")
        bitrate = request.form.get("bitrate", "128")
        dark_mode = bool(request.form.get("darkMode"))
        deemon_config["deemix"]["arl"] = arl
        deemix_config["arl"] = arl
        deemon_config["global"]["bitrate"] = bitrate
        deemon_config["global"]["dark_mode"] = dark_mode
        deemix_config["maxBitrate"] = {"128": "1", "320": "3", "FLAC": "9"}.get(bitrate, "1")
        save_config(deemon_config, deemix_config)
        return redirect(url_for("index"))
    return render_template("config.html", deemon_config=deemon_config, deemix_config=deemix_config, dark_mode=dark_mode)

@socketio.on('connect')
def handle_connect():
    emit('progress', {'message': 'Conectado ao servidor'})

if __name__ == "__main__":
    initialize_scripts()
    socketio.run(app, host="0.0.0.0", port=8813)