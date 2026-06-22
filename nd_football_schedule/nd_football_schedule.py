import logging
from typing import Any, Dict, List, Tuple
from datetime import datetime

from plugins.base_plugin.base_plugin import BasePlugin
from utils.http_client import get_http_session

logger = logging.getLogger(__name__)

class NdFootballSchedule(BasePlugin):

    def generate_settings_template(self):
        params = super().generate_settings_template()
        params["style_settings"] = True
        return params

    def generate_image(self, settings: Dict[str, Any], device_config):
        # 1️⃣ Dynamically look up the local system timezone config from the Pi
        try:
            tz_name = device_config.get_config("timezone")
        except Exception:
            tz_name = None
            
        if not tz_name:
            tz_name = "America/Chicago" # Secure fallback rule

        season = (settings.get("season") or "2026").strip()
        
        # 2️⃣ Injected the tz parameter directly into the URL query chain
        url = f"https://nd-schedule.joshuamreynolds.workers.dev/?season={season}&tz={tz_name}"

        session = get_http_session()
        res = session.get(url, timeout=30)
        res.raise_for_status()
        data = res.json()

        games = data.get("games", [])
        team_info = data.get("team", {})

        dimensions = self._get_dimensions(settings, device_config)
        is_large = dimensions[0] >= 1400

        # Page window partitioning rules
        max_games = 7 if not is_large else 12
        display_games = games[:max_games]

        formatted_games = []
        for g in display_games:
            raw_date = g.get("date", "")
            date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%b %d").upper()

            time_str = g.get("time") or "TBD"

            opp = g.get("opponent", {})
            opp_name = opp.get("name", "UNKNOWN")
            
            # Formatting ranking data structures
            rank = opp.get("rank")
            rank_at_game = opp.get("rankAtGameTime")
            
            rank_str = ""
            if rank_at_game:
                rank_str = f"#{rank_at_game} "
            elif rank:
                rank_str = f"#{rank} "

            ha = g.get("homeAway", "home")
            prefix = "VS " if ha == "home" else "AT "
            if ha == "neutral":
                prefix = "NEU "

            opp_display = f"{prefix}{rank_str}{opp_name}".upper()
            opp_record = g.get("opponentRecord", "0-0")

            res_str = g.get("result") or time_str

            formatted_games.append({
                "date": formatted_date,
                "opponent": opp_display,
                "opp_record": opp_record,
                "result": res_str,
                "logo": opp.get("logo")
            })

        template_params = {
            "season": season,
            "team_record": team_info.get("record", "0-0"),
            "games": formatted_games,
            "is_large": is_large,
            "plugin_settings": settings,
        }

        return self.render_image(dimensions, "nd_football_schedule.html", "nd_football_schedule.css", template_params)

    def _get_dimensions(self, settings: Dict[str, Any], device_config) -> Tuple[int, int]:
        screen_size = (settings.get("screen_size") or "auto").strip().lower()
        if screen_size == "800x480":
            dims = (800, 480)
        elif screen_size == "1600x1200":
            dims = (1600, 1200)
        else:
            dims = device_config.get_resolution()

        if device_config.get_config("orientation") == "vertical":
            dims = dims[::-1]
        return dims
