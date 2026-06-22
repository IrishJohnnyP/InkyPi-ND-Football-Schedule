from plugins.base_plugin.base_plugin import BasePlugin
from utils.http_client import get_http_session


WORKER_URL = "https://ndschedule.butternut.cloud"


class NDFootballSchedule(BasePlugin):

    def generate_settings_template(self):
        params = super().generate_settings_template()
        params["style_settings"] = True
        return params

    def _fetch_schedule(self, season, tz_name):
        session = get_http_session()

        params = {}
        if season:
            params["season"] = season
        if tz_name:
            params["tz"] = tz_name  # 🕒 Pass timezone to the Cloudflare Worker

        response = session.get(WORKER_URL, params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    def generate_image(self, settings, device_config):
        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        # 1️⃣ Dynamically extract the timezone from the Raspberry Pi system configuration
        try:
            tz_name = device_config.get_config("timezone")
        except Exception:
            tz_name = None
            
        if not tz_name:
            tz_name = "America/Chicago"  # Safe default fallback

        season = settings.get("season") or ""
        
        # 2️⃣ Pass both the season and timezone into the fetch method
        data = self._fetch_schedule(season, tz_name)

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
