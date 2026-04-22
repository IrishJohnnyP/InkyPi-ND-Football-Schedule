import requests
from inky_pi.plugins.base import BasePlugin


class NDFootballSchedule(BasePlugin):
    WORKER_URL = "https://nd-football-schedule.pietrowicz.workers.dev"

    def fetch_data(self):
        season = self.plugin_settings.get("season", "")
        params = {"season": season} if season else {}

        try:
            r = requests.get(self.WORKER_URL, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception:
            return {
                "team": {"name": "Notre Dame", "nickname": "Fighting Irish", "record": "—"},
                "games": [],
                "season": season
            }

    def render(self):
        data = self.fetch_data()

        return self.render_template(
            "main.html",
            team=data.get("team", {}),
            games=data.get("games", []),
            season=data.get("season", "—"),
        )
