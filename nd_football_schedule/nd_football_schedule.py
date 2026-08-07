import logging
from plugins.base_plugin.base_plugin import BasePlugin
from utils.http_client import get_http_session

logger = logging.getLogger(__name__)

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
            params["tz"] = tz_name

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        response = session.get(WORKER_URL, params=params, headers=headers, timeout=15)

        try:
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Error Body: {response.text}")
            raise e

        return response.json()

    def generate_image(self, settings, device_config):
        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        try:
            tz_name = device_config.get_config("timezone")
        except Exception:
            tz_name = None

        if not tz_name:
            tz_name = "America/Chicago"

        season = settings.get("season") or ""

        data = self._fetch_schedule(season, tz_name)

        return self.render_image(
            dimensions,
            "nd_football_schedule.html",
            "nd_football_schedule.css",
            {
                "team": data.get("team", {}),
                "games": data.get("games", []),
                "season": data.get("season"),
                "plugin_settings": settings,
            },
        )
