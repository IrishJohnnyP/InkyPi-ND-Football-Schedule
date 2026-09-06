import logging
import requests
from plugins.base_plugin.base_plugin import BasePlugin
from utils.http_client import get_http_session

logger = logging.getLogger(__name__)

WORKER_URL = "https://ndschedule.butternut.cloud"

class NDFootballSchedule(BasePlugin):

    def generate_settings_template(self):
        params = super().generate_settings_template()
        params["style_settings"] = True
        return params

    def _fetch_schedule(self, season, tz_name, device_config):
        session = get_http_session()

        params = {}
        if season:
            params["season"] = season
        if tz_name:
            params["tz"] = tz_name

        app_key = device_config.load_env_key("app_key")
        if app_key:
            params["app_key"] = app_key

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            # Splitting the timeout into a (connect, read) tuple allows the system to fail fast on unreachable servers.
            response = session.get(WORKER_URL, params=params, headers=headers, timeout=(3.05, 15))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"[{self.name}] Failed to fetch schedule data: {e}")
            return None

    def generate_image(self, settings, device_config):
        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        try:
            tz_name = device_config.get_config("timezone")
        except Exception:
            tz_name = None
            
        if not tz_name:
            tz_name = "America/New_York" 

        season = settings.get("season") or ""
        
        data = self._fetch_schedule(season, tz_name, device_config)
        
        # Stop execution immediately if the API fetch failed
        if not data:
            return None

        image = self.render_image(
            dimensions,
            "nd_football_schedule.html",
            "nd_football_schedule.css",
            {
                "team": data.get("team", {}),
                "games": data.get("games", []),
                "season": data.get("season"),
                "plugin_settings": settings
            }
        )

        # Prevent Pillow operations on a null object if Chromium timed out
        if image is None:
            return None

        # Safe to perform image.convert('RGB') or other Pillow manipulations here
        return image
