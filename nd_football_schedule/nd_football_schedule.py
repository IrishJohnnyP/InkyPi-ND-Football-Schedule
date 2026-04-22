from plugins.base_plugin.base_plugin import BasePlugin
from utils.http_client import get_http_session


WORKER_URL = "https://nd-football-schedule.pietrowicz.workers.dev"


class NDFootballSchedule(BasePlugin):

    def generate_settings_template(self):
        params = super().generate_settings_template()
        params["style_settings"] = True
        return params

    def _fetch_schedule(self, season):
        session = get_http_session()

        params = {}
        if season:
            params["season"] = season

        response = session.get(WORKER_URL, params=params, timeout=15)
        response.raise_for_status()
        return response.json()

    def generate_image(self, settings, device_config):
        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        season = settings.get("season") or ""
        data = self._fetch_schedule(season)

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
