import logging
import requests
from PIL import Image, ImageDraw, ImageFont
from plugins.base_plugin.base_plugin import BasePlugin
from utils.http_client import get_http_session
from io import BytesIO

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

        # Create base image canvas (white background matching CSS container)
        image = Image.new("RGB", dimensions, color="white")
        draw = ImageDraw.Draw(image)

        is_small = dimensions[0] <= 800
        
        # Typography scaling corresponding to CSS variables
        header_font_size = 26 if is_small else 64
        meta_font_size = 18 if is_small else 40
        row_font_size = 18 if is_small else 42
        
        try:
            font_header = ImageFont.truetype("static/fonts/Inter-Black.ttf", header_font_size)
            font_meta = ImageFont.truetype("static/fonts/Inter-Bold.ttf", meta_font_size)
            font_row = ImageFont.truetype("static/fonts/Inter-Bold.ttf", row_font_size)
        except IOError:
            font_header = ImageFont.load_default()
            font_meta = ImageFont.load_default()
            font_row = ImageFont.load_default()

        # Layout Padding & Coordinates matching CSS container variables
        pad = 8 if is_small else 20
        width, height = dimensions
        
        # --- HEADER SECTION ---
        team_info = data.get("team", {})
        season_year = data.get("season", "")
        record_str = f"Record: {team_info.get('record', '0-0')}"
        
        draw.text((pad, pad), f"Notre Dame Football {season_year}", fill="black", font=font_header)
        
        # Right-align record text matching CSS .nd-header-right
        record_bbox = font_header.getbbox(record_str)
        record_width = record_bbox[2] - record_bbox[0]
        draw.text((width - pad - record_width, pad), record_str, fill="black", font=font_header)
        
        # Header Bottom Border (8px solid black matching CSS)
        header_line_y = pad + header_font_size + (8 if is_small else 15)
        border_width = 4 if is_small else 8
        draw.line([(pad, header_line_y), (width - pad, header_line_y)], fill="black", width=border_width)

        # --- TABLE HEADERS ---
        head_y = header_line_y + (10 if is_small else 20)
        col_date_x = pad
        col_time_x = pad + (65 if is_small else 140)
        col_opp_x  = col_time_x + (85 if is_small else 240)
        col_site_x = width - pad - (140 if is_small else 300)
        col_res_x  = width - pad - (85 if is_small else 180)

        draw.text((col_date_x, head_y), "Date", fill="black", font=font_meta)
        draw.text((col_time_x, head_y), "Time", fill="black", font=font_meta)
        draw.text((col_opp_x, head_y), "Opponent", fill="black", font=font_meta)
        draw.text((col_site_x, head_y), "Site", fill="black", font=font_meta)
        draw.text((col_res_x, head_y), "Result", fill="black", font=font_meta)

        # Head underline (4px solid black matching CSS .nd-head)
        head_line_y = head_y + meta_font_size + (6 if is_small else 12)
        draw.line([(pad, head_line_y), (width - pad, head_line_y)], fill="black", width=2 if is_small else 4)

        # --- ROWS ---
        games = data.get("games", [])
        current_y = head_line_y + (10 if is_small else 20)
        row_height = 26 if is_small else 55

        for game in games[:12]:
            date_raw = game.get("date")
            date_str = date_raw[-5:] if date_raw else "—"
            time_str = game.get("time") or "TBD"
            
            opp_data = game.get("opponent", {})
            opp_name = opp_data.get("name", "TBD")
            opp_rank = opp_data.get("rankAtGameTime")
            display_opp = f"#{opp_rank} {opp_name}" if opp_rank else opp_name

            home_away = game.get("homeAway", "away")
            site_str = "Home" if home_away == "home" else ("Neutral" if home_away == "neutral" else "Away")
            
            result_str = game.get("result") or "—"
            is_loss = "L" in result_str

            # Draw columns matching grid alignment
            draw.text((col_date_x, current_y), date_str, fill="black", font=font_row)
            draw.text((col_time_x, current_y), time_str, fill="black", font=font_row)
            draw.text((col_opp_x, current_y), display_opp, fill="black", font=font_row)
            draw.text((col_site_x, current_y), site_str, fill="black", font=font_row)
            
            # Result color formatting (Red for losses matching CSS .loss)
            res_color = "#FF0000" if is_loss else "black"
            draw.text((col_res_x, current_y), result_str, fill=res_color, font=font_row)

            # Row divider line matching CSS border-bottom
            divider_y = current_y + row_height - (4 if is_small else 8)
            draw.line([(pad, divider_y), (width - pad, divider_y)], fill="#CCCCCC" if is_small else "#000000", width=1)

            current_y += row_height

        # Pass through the adaptive image loader to apply Spectra 6 calibration profiles
        processed_image = self.image_loader.from_bytesio(
            BytesIO(_image_to_bytes(image)), 
            dimensions, 
            resize=False
        )

        return processed_image

def _image_to_bytes(img):
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
