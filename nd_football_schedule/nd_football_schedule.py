import base64
import logging
import os
import re
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

    def _find_logo_dir(self):
        """Locate static/logos directory across system service paths."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        candidate_dirs = [
            "/home/john/InkyPi/src/static/logos",
            "/home/john/InkyPi/static/logos",
            os.path.abspath(os.path.join(current_dir, "../../static/logos")),
            "/usr/local/inkypi/src/static/logos",
        ]
        for d in candidate_dirs:
            if os.path.isdir(d):
                return d
        return candidate_dirs[0]

    def _get_local_logo_b64(self, school_name, logo_dir):
        if not school_name:
            return None

        safe_name = school_name.lower().replace('&', 'and')
        safe_name = re.sub(r'[^a-z0-9]', '_', safe_name)
        safe_name = re.sub(r'_+', '_', safe_name).strip('_')

        for ext in ["png", "jpg", "svg"]:
            full_path = os.path.join(logo_dir, f"{safe_name}.{ext}")
            if os.path.exists(full_path):
                try:
                    with open(full_path, "rb") as img_f:
                        encoded = base64.b64encode(img_f.read()).decode("utf-8")
                        mime = "svg+xml" if ext == "svg" else "png"
                        return f"data:image/{mime};base64,{encoded}"
                except Exception as img_err:
                    logger.warning(f"[{self.name}] Error reading logo {full_path}: {img_err}")
        return None

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
        
        if not data:
            return None

        logo_dir = self._find_logo_dir()

        # Inject local Notre Dame logo for header
        team_data = data.get("team", {})
        team_data["logo"] = self._get_local_logo_b64("Notre Dame", logo_dir)

        # Inject local opponent logos for schedule rows
        games_data = data.get("games", [])
        for game in games_data:
            opp = game.get("opponent", {})
            opp_name = opp.get("name") or opp.get("id")
            opp["logo"] = self._get_local_logo_b64(opp_name, logo_dir)

        image = self.render_image(
            dimensions,
            "nd_football_schedule.html",
            "nd_football_schedule.css",
            {
                "team": team_data,
                "games": games_data,
                "season": data.get("season"),
                "plugin_settings": settings
            }
        )

        if image is None:
            return None

        return image
