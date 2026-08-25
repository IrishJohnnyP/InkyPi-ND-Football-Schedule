from plugins.base_plugin.base_plugin import BasePlugin
from utils.http_client import get_http_session

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

        # --- SECURITY FIX ---
        # Retrieve the app_key from InkyPi's environment and include it in query params
        app_key = device_config.load_env_key("app_key")
        if app_key:
            params["app_key"] = app_key
        # --------------------

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = session.get(WORKER_URL, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()

    def generate_image(self, settings, device_config):
        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        # --- TIMEZONE FIX ---
        try:
            tz_name = device_config.get_config("timezone")
        except Exception:
            tz_name = None
            
        if not tz_name:
            # Defaulting to Eastern Time to match the worker
            tz_name = "America/New_York" 
        # --------------------

        season = settings.get("season") or ""
        
        data = self._fetch_schedule(season, tz_name, device_config)

        return self.render_image(
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
