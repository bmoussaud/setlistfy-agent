import spotipy.util as util
from pathlib import Path

import spotipy
from dotenv import find_dotenv, load_dotenv
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)


class SpotipyClient:
    def __init__(self):
        load_dotenv(find_dotenv())
        scope = [
            "user-library-read",
            "user-read-playback-state",
            "user-modify-playback-state",
            "user-read-currently-playing",
            "playlist-read-private",
            "playlist-modify-private",
            "playlist-modify-public",
            "playlist-read-collaborative",
            "user-read-recently-played",
            "user-top-read",
        ]
        cache_path = Path(Path.home(), ".spotify_mcp_cache")
        logging.info(f"Cache path: {cache_path}")
        logging.info(f"Auth mode: {os.environ.get('AUTH_MODE')}")
        if os.environ.get("AUTH_MODE") == "client_credentials":
            self.sp = spotipy.Spotify(
                auth_manager=SpotifyClientCredentials(
                    client_id=os.environ.get("SPOTIPY_CLIENT_ID"),
                    client_secret=os.environ.get("SPOTIPY_CLIENT_SECRET"),
                )
            )
        else:
            self.sp = spotipy.Spotify(
                auth_manager=SpotifyOAuth(
                    client_id=os.environ.get("SPOTIPY_CLIENT_ID"),
                    client_secret=os.environ.get("SPOTIPY_CLIENT_SECRET"),
                    redirect_uri=os.environ.get("SPOTIPY_REDIRECT_URI"),
                    scope=scope,
                    cache_path=cache_path,
                )
                # self.sp = spotipy.Spotify(
                #    auth_manager=SpotifyOAuth(scope=scope, cache_path=cache_path),
            )
        logging.info(f"Spotify client initialized: {self.sp}")

        # self.s    p.trace = True
        # self.sp.trace_out = True
        # results = self.sp.current_user_saved_tracks()
        # for idx, item in enumerate(results['items']):
        #    track = item['track']
        #    print(idx, track['artists'][0]['name'], " – ", track['name'])


client = SpotipyClient()
