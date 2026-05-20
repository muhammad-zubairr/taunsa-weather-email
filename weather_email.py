import requests
from datetime import datetime
import pytz
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ─────────────────────────────────────────────
#  SETTINGS — GitHub Secrets se aata hai
# ─────────────────────────────────────────────
SENDER_EMAIL    = os.environ.get("SENDER_EMAIL",    "")   # Aapka Gmail
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")   # App Password (16 digits)
RECEIVER_EMAIL  = os.environ.get("RECEIVER_EMAIL",  "")   # Jis email par aaye (same ya alag)

# Taunsa, Dera Ghazi Khan
LATITUDE  = 30.7042
LONGITUDE = 70.6520
CITY_NAME = "ٹونسہ، ڈیرہ غازی خان"

# ─────────────────────────────────────────────
#  WEATHER DATA
# ─────────────────────────────────────────────
def get_weather():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": [
            "temperature_2m", "relative_humidity_2m",
            "apparent_temperature", "weather_code",
            "wind_speed_10m", "precipitation"
        ],
        "daily": [
            "weather_code", "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "precipitation_probability_max", "wind_speed_10m_max"
        ],
        "timezone": "Asia/Karachi",
        "forecast_days": 4
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

# ─────────────────────────────────────────────
#  WEATHER CODE → URDU + EMOJI
# ─────────────────────────────────────────────
def weather_urdu(code):
    mapping = {
        0:  ("☀️", "صاف آسمان",         "#FF8C00"),
        1:  ("🌤️", "زیادہ تر صاف",      "#FFA500"),
        2:  ("⛅",  "جزوی بادل",         "#778899"),
        3:  ("☁️", "ابر آلود",           "#696969"),
        45: ("🌫️", "دھند",              "#B0C4DE"),
        48: ("🌫️", "شدید دھند",         "#A9A9A9"),
        51: ("🌦️", "ہلکی بوندا باندی",  "#4682B4"),
        53: ("🌦️", "درمیانی بوندا باندی","#4169E1"),
        55: ("🌧️", "تیز بوندا باندی",   "#00008B"),
        61: ("🌧️", "ہلکی بارش",         "#4682B4"),
        63: ("🌧️", "درمیانی بارش",      "#4169E1"),
        65: ("🌧️", "تیز بارش",          "#00008B"),
        71: ("🌨️", "ہلکی برفباری",      "#87CEEB"),
        73: ("🌨️", "درمیانی برفباری",   "#B0E0E6"),
        75: ("❄️", "تیز برفباری",        "#E0F0FF"),
        80: ("🌦️", "وقفے وقفے سے بارش", "#5F9EA0"),
        81: ("🌧️", "بارش کے جھٹکے",    "#4169E1"),
        82: ("⛈️", "تیز بارش کے جھٹکے","#191970"),
        95: ("⛈️", "آندھی اور بجلی",    "#8B0000"),
        96: ("⛈️", "ژالہ باری",          "#800000"),
        99: ("⛈️", "شدید ژالہ باری",    "#4B0000"),
    }
    return mapping.get(code, ("🌡️", "موسم نامعلوم", "#555555"))

def urdu_day(date_str):
    days = {"Monday":"پیر","Tuesday":"منگل","Wednesday":"بدھ",
            "Thursday":"جمعرات","Friday":"جمعہ","Saturday":"ہفتہ","Sunday":"اتوار"}
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return days[dt.strftime("%A")]

def urdu_date(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    months = {1:"جنوری",2:"فروری",3:"مارچ",4:"اپریل",5:"مئی",6:"جون",
              7:"جولائی",8:"اگست",9:"ستمبر",10:"اکتوبر",11:"نومبر",12:"دسمبر"}
    return f"{dt.day} {months[dt.month]} {dt.year}"

# ─────────────────────────────────────────────
#  BUILD BEAUTIFUL HTML EMAIL
# ─────────────────────────────────────────────
def build_html_email(data):
    pk_tz = pytz.timezone("Asia/Karachi")
    now   = datetime.now(pk_tz)

    cur  = data["current"]
    daily = data["daily"]

    cur_emoji, cur_desc, cur_color = weather_urdu(cur["weather_code"])
    cur_temp   = round(cur["temperature_2m"])
    feels_like = round(cur["apparent_temperature"])
    humidity   = cur["relative_humidity_2m"]
    wind       = round(cur["wind_speed_10m"])
    precip     = cur["precipitation"]

    today_str  = daily["time"][0]
    today_day  = urdu_day(today_str)
    today_date = urdu_date(today_str)
    today_max  = round(daily["temperature_2m_max"][0])
    today_min  = round(daily["temperature_2m_min"][0])
    today_rain = daily["precipitation_probability_max"][0]

    report_time = now.strftime("%I:%M %p")

    # Temperature color
    def temp_color(t):
        if t >= 40: return "#FF2200"
        if t >= 35: return "#FF6600"
        if t >= 30: return "#FF9900"
        if t >= 20: return "#33AA00"
        if t >= 10: return "#0099FF"
        return "#0055FF"

    # 3 din cards
    forecast_cards = ""
    for i in range(1, 4):
        d_str  = daily["time"][i]
        d_emoji, d_desc, d_color = weather_urdu(daily["weather_code"][i])
        d_max  = round(daily["temperature_2m_max"][i])
        d_min  = round(daily["temperature_2m_min"][i])
        d_rain = daily["precipitation_probability_max"][i]
        d_wind = round(daily["wind_speed_10m_max"][i])
        forecast_cards += f"""
        <div style="background:{d_color}18; border:2px solid {d_color}44;
                    border-radius:16px; padding:18px; text-align:center; flex:1; min-width:150px;">
          <div style="font-size:13px; color:#888; margin-bottom:4px;">{urdu_day(d_str)}</div>
          <div style="font-size:12px; color:#aaa; margin-bottom:10px;">{urdu_date(d_str)}</div>
          <div style="font-size:36px;">{d_emoji}</div>
          <div style="font-size:13px; color:#ddd; margin:8px 0;">{d_desc}</div>
          <div style="font-size:18px; font-weight:bold; color:{temp_color(d_max)};">{d_max}°C</div>
          <div style="font-size:13px; color:#aaa;">{d_min}°C</div>
          <div style="margin-top:10px; font-size:12px; color:#88aaff;">💧 {d_rain}%</div>
          <div style="font-size:12px; color:#aaa;">💨 {d_wind} km/h</div>
        </div>"""

    precip_row = ""
    if precip > 0:
        precip_row = f"""
        <tr>
          <td style="padding:10px 0; border-bottom:1px solid #333; color:#aaa; font-size:15px;">☔ ابھی بارش</td>
          <td style="padding:10px 0; border-bottom:1px solid #333; color:#fff; font-size:15px; font-weight:bold; text-align:left;">{precip} mm</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ur">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>موسم رپورٹ — ٹونسہ</title>
</head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:'Segoe UI',Tahoma,Arial,sans-serif;direction:rtl;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0f;padding:30px 10px;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

  <!-- HEADER -->
  <tr><td style="background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);
                 border-radius:24px 24px 0 0; padding:35px 30px; text-align:center;">
    <div style="font-size:48px; margin-bottom:10px;">{cur_emoji}</div>
    <h1 style="margin:0;color:#fff;font-size:26px;font-weight:700;">روزانہ موسم رپورٹ</h1>
    <p style="margin:8px 0 0;color:#8ab4f8;font-size:16px;">📍 {CITY_NAME}</p>
    <p style="margin:5px 0 0;color:#aaa;font-size:14px;">📅 {today_day} — {today_date} &nbsp;|&nbsp; 🕕 {report_time}</p>
  </td></tr>

  <!-- TODAY MAIN -->
  <tr><td style="background:#111827; padding:30px;">
    <div style="background:{cur_color}15; border:2px solid {cur_color}40;
                border-radius:18px; padding:25px; text-align:center; margin-bottom:25px;">
      <div style="font-size:15px; color:#aaa; margin-bottom:5px;">آج کا موسم</div>
      <div style="font-size:18px; color:#ddd; margin-bottom:15px;">{cur_desc}</div>
      <div style="font-size:72px; font-weight:900; color:{temp_color(cur_temp)};
                  line-height:1;">{cur_temp}°C</div>
      <div style="font-size:14px; color:#888; margin-top:8px;">محسوس ہو رہا ہے: {feels_like}°C</div>
      <div style="display:flex; justify-content:center; gap:20px; margin-top:15px;
                  font-size:15px; color:#ccc;">
        <span>🔺 {today_max}°C</span>
        <span style="color:#555;">|</span>
        <span>🔻 {today_min}°C</span>
      </div>
    </div>

    <!-- STATS TABLE -->
    <table width="100%" cellpadding="0" cellspacing="0"
           style="background:#1f2937; border-radius:14px; padding:5px 20px; margin-bottom:25px;">
      <tr>
        <td style="padding:12px 0; border-bottom:1px solid #333; color:#aaa; font-size:15px;">💧 نمی</td>
        <td style="padding:12px 0; border-bottom:1px solid #333; color:#fff; font-size:15px; font-weight:bold; text-align:left;">{humidity}%</td>
      </tr>
      <tr>
        <td style="padding:12px 0; border-bottom:1px solid #333; color:#aaa; font-size:15px;">💨 ہوا کی رفتار</td>
        <td style="padding:12px 0; border-bottom:1px solid #333; color:#fff; font-size:15px; font-weight:bold; text-align:left;">{wind} km/h</td>
      </tr>
      <tr>
        <td style="padding:12px 0; border-bottom:1px solid #333; color:#aaa; font-size:15px;">🌧️ بارش کا امکان</td>
        <td style="padding:12px 0; border-bottom:1px solid #333; color:#fff; font-size:15px; font-weight:bold; text-align:left;">{today_rain}%</td>
      </tr>
      {precip_row}
    </table>

    <!-- 3 DAY FORECAST -->
    <div style="color:#fff; font-size:17px; font-weight:bold; margin-bottom:15px;">
      📆 اگلے 3 دنوں کا موسم
    </div>
    <div style="display:flex; gap:12px; flex-wrap:wrap;">
      {forecast_cards}
    </div>

  </td></tr>

  <!-- FOOTER -->
  <tr><td style="background:#0d1117; border-radius:0 0 24px 24px;
                 padding:20px; text-align:center; border-top:1px solid #222;">
    <p style="margin:0; color:#555; font-size:12px;">
      🤖 یہ رپورٹ خودکار طریقے سے تیار کی گئی ہے
    </p>
    <p style="margin:5px 0 0; color:#555; font-size:12px;">
      📡 ماخذ: Open-Meteo موسمی سروس
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""
    return html

# ─────────────────────────────────────────────
#  SEND EMAIL VIA GMAIL SMTP
# ─────────────────────────────────────────────
def send_email(html_content, today_date):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🌤️ موسم رپورٹ — ٹونسہ | {today_date}"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
    print("✅ Email kamyabi se bhej di gayi!")

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("🌤️ Taunsa DG Khan — Weather Email generating...")
    try:
        data    = get_weather()
        today_d = urdu_date(data["daily"]["time"][0])
        html    = build_html_email(data)
        send_email(html, today_d)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
