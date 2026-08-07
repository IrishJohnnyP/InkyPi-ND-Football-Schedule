import logging
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    pass

from plugins.base_plugin.base_plugin import BasePlugin
from utils.http_client import get_http_session

logger = logging.getLogger(__name__)


class NDFootballSchedule(BasePlugin):

    def generate_settings_template(self):
        params = super().generate_settings_template()
        params["style_settings"] = True
        return params

    def _fetch_schedule(self, season, tz_name):
        session = get_http_session()

        # Construct the direct ESPN API URL using the season parameter
        espn_url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/87/schedule?season={season}"
        
        # Spoof a modern browser User-Agent to bypass WAF filtering
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = session.get(espn_url, headers=headers, timeout=15)
        
        try:
            response.raise_for_status()
        except Exception as e:
            logger.error(f"ESPN Fetch Error: {response.text}")
            raise e
            
        espn_data = response.json()
        
        # Extract Notre Dame's overall season record
        team_record = "0-0"
        team_data = espn_data.get("team", {})
        if team_data.get("recordItems") and len(team_data["recordItems"]) > 0:
            team_record = team_data["recordItems"][0].get("summary", "0-0")
        
        events = espn_data.get("events", [])
        games = []
        
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = None
            
        for ev in events:
            comps = ev.get("competitions", [])
            if not comps:
                continue
            comp = comps[0]
            
            competitors = comp.get("competitors", [])
            nd = next((c for c in competitors if str(c.get("team", {}).get("id")) == "87"), None)
            opp = next((c for c in competitors if str(c.get("team", {}).get("id")) != "87"), None)
            
            if not nd or not opp:
                continue
                
            game_date = None
            time_str = "TBD"
            comp_date = comp.get("date")
            
            if comp_date:
                game_date = comp_date[:10]
                # ESPN marks timeValid as False for TBD games
                if ev.get("timeValid") is not False:
                    try:
                        dt = datetime.fromisoformat(comp_date.replace("Z", "+00:00"))
                        if tz:
                            dt = dt.astimezone(tz)
                        # Format to Local Time (e.g., 2:30 PM)
                        time_str = dt.strftime("%I:%M %p").lstrip("0")
                    except Exception:
                        pass
                        
            home_away_status = "neutral"
            if not comp.get("neutralSite"):
                home_away_status = "home" if nd.get("homeAway") == "home" else "away"
                
            status = comp.get("status", {}).get("type", {})
            is_completed = status.get("completed", False)
            
            result = None
            if is_completed:
                # Safely extract scores whether they arrive as dictionaries or raw strings
                nd_score_str = str(nd.get("score", {}).get("value") if isinstance(nd.get("score"), dict) else nd.get("score") or "0")
                opp_score_str = str(opp.get("score", {}).get("value") if isinstance(opp.get("score"), dict) else opp.get("score") or "0")
                try:
                    nd_score = int(nd_score_str)
                    opp_score = int(opp_score_str)
                    if nd_score > opp_score:
                        result = f"W {nd_score}–{opp_score}"
                    elif nd_score < opp_score:
                        result = f"L {nd_score}–{opp_score}"
                    else:
                        result = f"T {nd_score}–{opp_score}"
                except ValueError:
                    pass
            
            opp_team = opp.get("team", {})
            curated_rank = opp.get("curatedRank", {}).get("current")
            opp_rank = curated_rank if curated_rank and curated_rank <= 25 else None
            
            opp_record = "0-0"
            if opp.get("record") and len(opp["record"]) > 0:
                opp_record = opp["record"][0].get("displayValue", "0-0")
                
            nd_record_display = team_record
            if nd.get("record") and len(nd["record"]) > 0:
                nd_record_display = nd["record"][0].get("displayValue", team_record)
                
            logo = None
            if opp_team.get("logos") and len(opp_team["logos"]) > 0:
                logo = opp_team["logos"][0].get("href")
                
            week_obj = ev.get("week", {})
                
            games.append({
                "date": game_date,
                "time": time_str,
                "week": week_obj.get("number", ""),
                "homeAway": home_away_status,
                "opponentRecord": opp_record,
                "opponent": {
                    "id": opp_team.get("id", "TBD"),
                    "name": opp_team.get("location") or opp_team.get("displayName") or "TBD",
                    "mascot": opp_team.get("name", ""),
                    "logo": logo,
                    "rank": opp_rank,
                    "rankAtGameTime": opp_rank,
                    "rankSource": "ESPN",
                    "rankPoll": "ESPN"
                },
                "ndRecord": nd_record_display,
                "result": result
            })
            
        # Attempt to pull ND's current rank from their most recently scheduled game
        nd_rank = None
        if events:
            latest_comp = events[-1].get("competitions", [{}])[0]
            latest_nd = next((c for c in latest_comp.get("competitors", []) if str(c.get("team", {}).get("id")) == "87"), None)
            if latest_nd:
                curated_rank = latest_nd.get("curatedRank", {}).get("current")
                if curated_rank and curated_rank <= 25:
                    nd_rank = curated_rank
                    
        return {
            "season": season,
            "timezone": tz_name,
            "source": "ESPN API (Direct Python)",
            "team": {
                "id": 87,
                "name": "Notre Dame",
                "nickname": "Fighting Irish",
                "rank": nd_rank,
                "record": team_record
            },
            "games": games
        }

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

        season = settings.get("season")
        if not season:
            try:
                season = str(datetime.now().year)
            except Exception:
                season = "2026"
        
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
