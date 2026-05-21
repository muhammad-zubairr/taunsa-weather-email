import requests
from datetime import datetime
import pytz
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ─────────────────────────────────────────────
SENDER_EMAIL    = os.environ.get("SENDER_EMAIL",    "")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")
RECEIVER_EMAIL  = os.environ.get("RECEIVER_EMAIL",  "")

LATITUDE  = 30.7042
LONGITUDE = 70.6520
CITY_NAME = "تونسہ، ڈیرہ غازی خان"

# ─────────────────────────────────────────────
def get_weather():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE, "longitude": LONGITUDE,
        "current": ["temperature_2m","relative_humidity_2m","apparent_temperature",
                    "weather_code","wind_speed_10m","precipitation","wind_gusts_10m"],
        "daily": ["weather_code","temperature_2m_max","temperature_2m_min",
                  "precipitation_sum","precipitation_probability_max",
                  "wind_speed_10m_max","wind_gusts_10m_max"],
        "hourly": ["temperature_2m","precipitation_probability","wind_speed_10m"],
        "timezone": "Asia/Karachi",
        "forecast_days": 4
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def weather_urdu(code):
    m = {
        0:("☀️","صاف آسمان"), 1:("🌤️","زیادہ تر صاف"), 2:("⛅","جزوی بادل"),
        3:("☁️","ابر آلود"), 45:("🌫️","دھند"), 48:("🌫️","شدید دھند"),
        51:("🌦️","ہلکی بوندا باندی"), 53:("🌦️","درمیانی بوندا باندی"),
        55:("🌧️","تیز بوندا باندی"), 61:("🌧️","ہلکی بارش"),
        63:("🌧️","درمیانی بارش"), 65:("🌧️","تیز بارش"),
        80:("🌦️","وقفے سے بارش"), 81:("🌧️","بارش کے جھٹکے"),
        82:("⛈️","تیز بارش کے جھٹکے"), 95:("⛈️","آندھی اور بجلی"),
        96:("⛈️","ژالہ باری"), 99:("⛈️","شدید ژالہ باری"),
    }
    return m.get(code, ("🌡️","موسم نامعلوم"))

def urdu_day(date_str):
    days = {"Monday":"پیر","Tuesday":"منگل","Wednesday":"بدھ",
            "Thursday":"جمعرات","Friday":"جمعہ","Saturday":"ہفتہ","Sunday":"اتوار"}
    return days[datetime.strptime(date_str,"%Y-%m-%d").strftime("%A")]

def urdu_date(date_str):
    dt = datetime.strptime(date_str,"%Y-%m-%d")
    months = {1:"جنوری",2:"فروری",3:"مارچ",4:"اپریل",5:"مئی",6:"جون",
              7:"جولائی",8:"اگست",9:"ستمبر",10:"اکتوبر",11:"نومبر",12:"دسمبر"}
    return f"{dt.day} {months[dt.month]} {dt.year}"

# ─────────────────────────────────────────────
# SMART WARNINGS LOGIC
# ─────────────────────────────────────────────
def generate_warnings(cur, daily):
    warnings = []
    temp     = round(cur["temperature_2m"])
    feels    = round(cur["apparent_temperature"])
    wind     = round(cur["wind_speed_10m"])
    gusts    = round(cur.get("wind_gusts_10m", 0))
    humidity = cur["relative_humidity_2m"]
    rain_prob= daily["precipitation_probability_max"][0]
    wcode    = cur["weather_code"]
    max_t    = round(daily["temperature_2m_max"][0])

    if max_t >= 44:
        warnings.append(("🔴","شدید گرمی کی وارننگ", f"زیادہ سے زیادہ درجہ حرارت {max_t}°C تک پہنچے گا — لو لگنے کا خطرہ ہے۔ دوپہر 12 سے 4 بجے گھر میں رہیں۔"))
    elif max_t >= 40:
        warnings.append(("🟠","گرمی کی تنبیہ", f"درجہ حرارت {max_t}°C رہے گا — زیادہ پانی پئیں اور دھوپ سے بچیں۔"))

    if gusts >= 60:
        warnings.append(("🔴","خطرناک آندھی کا خدشہ", f"ہوا کے جھونکے {gusts} km/h تک ہو سکتے ہیں — درخت اور کمزور ڈھانچے خطرے میں ہیں۔"))
    elif gusts >= 40 or wind >= 30:
        warnings.append(("🟠","تیز آندھی کا امکان", f"ہوا {wind} km/h اور جھونکے {gusts} km/h — باہر احتیاط کریں۔"))
    elif wind >= 20:
        warnings.append(("🟡","تیز ہوا", f"ہوا کی رفتار {wind} km/h — چھوٹی چیزیں محفوظ کر لیں۔"))

    if rain_prob >= 70 or wcode in [95,96,99]:
        warnings.append(("🔴","طوفانی بارش کا خدشہ", "آج شدید بارش اور آندھی آ سکتی ہے — گھر سے باہر نہ نکلیں۔"))
    elif rain_prob >= 50:
        warnings.append(("🟠","بارش کا امکان", f"آج {rain_prob}% بارش ہو سکتی ہے — چھتری ساتھ رکھیں۔"))
    elif rain_prob >= 30:
        warnings.append(("🟡","ہلکی بارش ممکن", f"بارش کا {rain_prob}% امکان ہے۔"))

    if humidity >= 80 and temp >= 35:
        warnings.append(("🟠","امس اور گھٹن", "نمی اور گرمی کا مجموعہ بہت تکلیف دہ ہوگا — AC یا پنکھا استعمال کریں۔"))

    # Taunsa special — sudden weather change warning
    if humidity >= 55 and wind >= 15 and rain_prob >= 20:
        warnings.append(("🟡","موسم اچانک بدل سکتا ہے", "تونسہ میں پہاڑی ہواؤں کی وجہ سے موسم بغیر اطلاع کے بدل سکتا ہے — تیار رہیں۔"))

    return warnings

# ─────────────────────────────────────────────
# SMART URDU SUMMARY GENERATOR
# ─────────────────────────────────────────────
def generate_summary(cur, daily):
    temp     = round(cur["temperature_2m"])
    feels    = round(cur["apparent_temperature"])
    wind     = round(cur["wind_speed_10m"])
    gusts    = round(cur.get("wind_gusts_10m", 0))
    humidity = cur["relative_humidity_2m"]
    rain_prob= daily["precipitation_probability_max"][0]
    max_t    = round(daily["temperature_2m_max"][0])
    min_t    = round(daily["temperature_2m_min"][0])
    wcode    = cur["weather_code"]
    emoji, desc = weather_urdu(wcode)

    # Today summary
    if max_t >= 44:
        today_feel = "آج موسم انتہائی گرم اور جھلسا دینے والا رہے گا"
    elif max_t >= 40:
        today_feel = "آج موسم بہت گرم اور خشک رہے گا"
    elif max_t >= 35:
        today_feel = "آج موسم گرم رہے گا"
    elif max_t >= 28:
        today_feel = "آج موسم معتدل اور خوشگوار رہے گا"
    else:
        today_feel = "آج موسم ٹھنڈا اور سردی والا رہے گا"

    rain_text = ""
    if rain_prob >= 70:
        rain_text = f" بارش کا {rain_prob} فیصد امکان ہے — آج شدید بارش متوقع ہے۔"
    elif rain_prob >= 40:
        rain_text = f" {rain_prob} فیصد بارش کا امکان ہے — چھتری ساتھ رکھیں۔"
    elif rain_prob >= 20:
        rain_text = f" ہلکی بارش کا معمولی امکان ({rain_prob}%) موجود ہے۔"
    else:
        rain_text = " بارش کا کوئی امکان نہیں۔"

    wind_text = ""
    if gusts >= 50:
        wind_text = f" ہوا کے خطرناک جھونکے ({gusts} km/h) آ سکتے ہیں۔"
    elif gusts >= 35:
        wind_text = f" تیز آندھی ({gusts} km/h جھونکے) کا امکان ہے۔"
    elif wind >= 20:
        wind_text = f" ہوا تیز ({wind} km/h) رہے گی۔"

    para1 = f"{today_feel}۔ درجہ حرارت <strong style='color:#ff6b6b;'>{max_t}°C</strong> تک پہنچے گا جبکہ کم سے کم <strong style='color:#4499ff;'>{min_t}°C</strong> رہے گا۔ گرمی کا احساس <strong style='color:#ff8844;'>{feels}°C</strong> ہوگا۔{rain_text}{wind_text}"

    # 3 day summary
    day_texts = []
    for i in range(1,4):
        d_day  = urdu_day(daily["time"][i])
        d_max  = round(daily["temperature_2m_max"][i])
        d_rain = daily["precipitation_probability_max"][i]
        d_emoji, d_desc = weather_urdu(daily["weather_code"][i])
        d_wind = round(daily["wind_speed_10m_max"][i])

        if d_rain >= 60:
            d_text = f"<strong style='color:#00ffcc;'>{d_day}</strong> کو {d_desc} اور {d_rain}% بارش متوقع ہے"
        elif d_rain >= 30:
            d_text = f"<strong style='color:#00ffcc;'>{d_day}</strong> کو {d_desc}، ہلکی بارش ممکن"
        else:
            d_text = f"<strong style='color:#00ffcc;'>{d_day}</strong> کو {d_desc}، درجہ حرارت {d_max}°C"
        day_texts.append(d_text)

    para2 = f"اگلے 3 دن: {day_texts[0]}؛ {day_texts[1]}؛ {day_texts[2]}۔"

    # Advice
    advice_items = []
    if max_t >= 40:
        advice_items.append("دوپہر کو گھر میں رہیں اور ٹھنڈا پانی پیتے رہیں")
    if rain_prob >= 40:
        advice_items.append("چھتری اور بارش کا کوٹ تیار رکھیں")
    if gusts >= 35 or wind >= 25:
        advice_items.append("چھوٹی چیزیں اور فصلیں محفوظ کر لیں")
    if humidity >= 70 and max_t >= 33:
        advice_items.append("امس کی وجہ سے AC یا پنکھا استعمال کریں")
    # Taunsa farmer advice
    next_rain = any(daily["precipitation_probability_max"][i] >= 40 for i in range(1,4))
    if next_rain:
        advice_items.append("اگلے دنوں بارش متوقع ہے — کسان فصل کی کٹائی ملتوی کریں")
    if not advice_items:
        advice_items.append("آج موسم معمول کے مطابق ہے — کوئی خاص احتیاط نہیں")

    advice_html = " | ".join([f"✅ {a}" for a in advice_items])

    return para1, para2, advice_html

# ─────────────────────────────────────────────
# BUILD HTML EMAIL
# ─────────────────────────────────────────────
def build_email(data):
    pk_tz = pytz.timezone("Asia/Karachi")
    now   = datetime.now(pk_tz)
    cur   = data["current"]
    daily = data["daily"]

    emoji, desc = weather_urdu(cur["weather_code"])
    cur_temp = round(cur["temperature_2m"])
    feels    = round(cur["apparent_temperature"])
    humidity = cur["relative_humidity_2m"]
    wind     = round(cur["wind_speed_10m"])
    gusts    = round(cur.get("wind_gusts_10m",0))
    rain_p   = daily["precipitation_probability_max"][0]
    max_t    = round(daily["temperature_2m_max"][0])
    min_t    = round(daily["temperature_2m_min"][0])
    today_str= daily["time"][0]

    warnings = generate_warnings(cur, daily)
    para1, para2, advice_html = generate_summary(cur, daily)

    report_time = now.strftime("%I:%M %p")

    def temp_color(t):
        if t>=44: return "#FF0000"
        if t>=40: return "#FF3300"
        if t>=35: return "#FF6600"
        if t>=30: return "#FF9900"
        if t>=20: return "#33AA00"
        return "#0099FF"

    # Forecast cards
    fc_html = ""
    for i in range(1,4):
        d_str  = daily["time"][i]
        fe, fd = weather_urdu(daily["weather_code"][i])
        dm = round(daily["temperature_2m_max"][i])
        dn = round(daily["temperature_2m_min"][i])
        dr = daily["precipitation_probability_max"][i]
        dw = round(daily["wind_speed_10m_max"][i])
        fc_html += f"""
        <div style="background:rgba(0,255,200,0.06);border:1px solid rgba(0,255,200,0.22);
                    border-radius:20px;padding:20px 12px;flex:1;">
          <div style="color:#00ffcc;font-size:14px;font-weight:700;margin-bottom:3px;">{urdu_day(d_str)}</div>
          <div style="color:#ffffff;font-size:11px;margin-bottom:10px;">{urdu_date(d_str)}</div>
          <div style="font-size:38px;margin-bottom:8px;">{fe}</div>
          <div style="color:#ffffff;font-size:12px;margin-bottom:10px;">{fd}</div>
          <div style="color:{temp_color(dm)};font-size:22px;font-weight:900;">{dm}°</div>
          <div style="color:#ffffff;font-size:12px;margin-bottom:8px;">{dn}°</div>
          <div style="height:1px;background:rgba(0,255,200,0.12);margin-bottom:8px;"></div>
          <div style="color:#00aaff;font-size:11px;">💧 {dr}%</div>
          <div style="color:#ffffff;font-size:11px;margin-top:3px;">💨 {dw} km/h</div>
        </div>"""

    # Warnings HTML
    warn_html = ""
    if warnings:
        warn_items = ""
        for wlevel, wtitle, wtext in warnings:
            color_map = {"🔴":"#ff3333","🟠":"#ff8800","🟡":"#ffcc00"}
            wcolor = color_map.get(wlevel,"#ffcc00")
            warn_items += f"""
            <div style="background:rgba(255,100,0,0.06);border-right:3px solid {wcolor};
                        border-radius:10px;padding:12px 15px;margin-bottom:10px;">
              <div style="color:{wcolor};font-size:14px;font-weight:700;margin-bottom:4px;">
                {wlevel} {wtitle}
              </div>
              <div style="color:#ffffff;font-size:13px;line-height:1.8;">{wtext}</div>
            </div>"""
        warn_html = f"""
        <div style="background:linear-gradient(135deg,#1a0808,#180c04);
                    border:1px solid rgba(255,100,0,0.25);
                    border-radius:22px;padding:24px;margin-bottom:18px;">
          <div style="color:#ff8800;font-size:16px;font-weight:700;margin-bottom:14px;">
            ⚠️ موسمی تنبیہات
          </div>
          {warn_items}
        </div>"""

    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="ur">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap" rel="stylesheet">
<style>
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{background:#020818;font-family:'Noto Nastaliq Urdu','Segoe UI',serif;direction:rtl;}}
  .wrap{{max-width:680px;margin:0 auto;padding:30px 20px;}}
  .glow{{height:2px;background:linear-gradient(90deg,transparent,#00ffcc,#7b2fff,#00ffcc,transparent);
         border-radius:2px;box-shadow:0 0 18px rgba(0,255,200,0.4);margin:16px 0;}}
  .card{{border-radius:22px;padding:26px;margin-bottom:16px;}}
</style>
</head>
<body>
<div class="wrap">

  <!-- HEADER -->
  <div class="card" style="background:linear-gradient(135deg,#020c1e,#041428);
       border:1px solid rgba(0,255,200,0.2);">
    <div style="font-size:60px;filter:drop-shadow(0 0 20px rgba(0,255,200,0.5));margin-bottom:8px;">{emoji}</div>
    <div style="color:#00ffcc;font-size:24px;font-weight:700;margin-bottom:6px;">روزانہ موسم رپورٹ</div>
    <div class="glow"></div>
    <div style="color:#00aaff;font-size:14px;margin-bottom:4px;">📍 {CITY_NAME}</div>
    <div style="color:#ffffff;font-size:13px;">📅 {urdu_day(today_str)} — {urdu_date(today_str)} &nbsp;|&nbsp; 🕕 {report_time}</div>
  </div>

  <!-- TEMP -->
  <div class="card" style="background:linear-gradient(135deg,#030f20,#050c18);
       border:1px solid rgba(0,180,255,0.15);">
    <div style="color:#556677;font-size:13px;margin-bottom:4px;">{desc}</div>
    <div style="font-size:95px;font-weight:900;line-height:1;
                background:linear-gradient(180deg,#00ffcc,#00aaff);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                filter:drop-shadow(0 0 25px rgba(0,220,200,0.3));">{cur_temp}°C</div>
    <div style="color:#ffffff;font-size:13px;margin-top:6px;">
      محسوس: <span style="color:#00ccaa;font-weight:700;">{feels}°C</span>
    </div>
    <div class="glow" style="margin:14px 50px;"></div>
    <div style="display:flex;justify-content:center;gap:30px;">
      <div>
        <div style="color:#ff5555;font-size:26px;font-weight:900;">{max_t}°C</div>
        <div style="color:#ffffff;font-size:11px;">زیادہ سے زیادہ</div>
      </div>
      <div style="width:1px;background:rgba(0,255,200,0.1);"></div>
      <div>
        <div style="color:#4499ff;font-size:26px;font-weight:900;">{min_t}°C</div>
        <div style="color:#ffffff;font-size:11px;">کم سے کم</div>
      </div>
    </div>
  </div>

  <!-- STATS -->
  <div style="background:#030f20;border:1px solid rgba(0,255,200,0.1);
              border-radius:20px;margin-bottom:16px;overflow:hidden;">
    <div style="display:flex;">
      <div style="flex:1;padding:18px 8px;border-left:1px solid rgba(0,255,200,0.08);">
        <div style="font-size:24px;margin-bottom:5px;">💧</div>
        <div style="color:#00ffcc;font-size:20px;font-weight:800;">{humidity}%</div>
        <div style="color:#ffffff;font-size:11px;margin-top:3px;">نمی</div>
      </div>
      <div style="flex:1;padding:18px 8px;border-left:1px solid rgba(0,255,200,0.08);">
        <div style="font-size:24px;margin-bottom:5px;">💨</div>
        <div style="color:#00ffcc;font-size:20px;font-weight:800;">{wind}</div>
        <div style="color:#ffffff;font-size:11px;margin-top:3px;">km/h ہوا</div>
      </div>
      <div style="flex:1;padding:18px 8px;border-left:1px solid rgba(0,255,200,0.08);">
        <div style="font-size:24px;margin-bottom:5px;">💨🌪️</div>
        <div style="color:#00ffcc;font-size:20px;font-weight:800;">{gusts}</div>
        <div style="color:#ffffff;font-size:11px;margin-top:3px;">km/h جھونکے</div>
      </div>
      <div style="flex:1;padding:18px 8px;">
        <div style="font-size:24px;margin-bottom:5px;">🌧️</div>
        <div style="color:#00ffcc;font-size:20px;font-weight:800;">{rain_p}%</div>
        <div style="color:#ffffff;font-size:11px;margin-top:3px;">بارش امکان</div>
      </div>
    </div>
  </div>

  <!-- WARNINGS -->
  {warn_html}

  <!-- FORECAST -->
  <div class="card" style="background:#030f20;border:1px solid rgba(0,255,200,0.1);">
    <div style="color:#00ffcc;font-size:16px;font-weight:700;margin-bottom:14px;">📆 اگلے 3 دنوں کا موسم</div>
    <div style="display:flex;gap:10px;">{fc_html}</div>
  </div>

  <!-- URDU SUMMARY -->
  <div style="background:linear-gradient(135deg,rgba(0,30,20,0.98),rgba(0,20,40,0.98));
              border:1px solid rgba(0,255,200,0.2);border-radius:22px;padding:26px;margin-bottom:16px;">
    <div style="color:#00ffcc;font-size:16px;font-weight:700;margin-bottom:4px;">🧠 موسمی خلاصہ</div>
    <div style="color:#ffffff;font-size:12px;margin-bottom:14px;">ماہرانہ تجزیہ بمطابق Open-Meteo موسمی ڈیٹا</div>
    <div class="glow" style="margin:0 0 16px 0;"></div>

    <p style="color:#ffffff;font-size:14px;line-height:2.4;margin-bottom:14px;">{para1}</p>
    <p style="color:#ffffff;font-size:14px;line-height:2.4;margin-bottom:16px;">{para2}</p>

    <div style="background:rgba(0,255,200,0.04);border:1px solid rgba(0,255,200,0.12);
                border-radius:14px;padding:14px 16px;">
      <div style="color:#00aaff;font-size:13px;font-weight:700;margin-bottom:10px;">📌 آج کے لیے مشورے</div>
      <div style="color:#ffffff;font-size:13px;line-height:2.2;">{advice_html}</div>
    </div>

    <div style="margin-top:16px;padding-top:12px;border-top:1px solid rgba(0,255,200,0.08);
                display:flex;justify-content:space-between;">
      <span style="color:#ffffff;font-size:11px;">📡 Open-Meteo موسمی سروس</span>
      <span style="color:#ffffff;font-size:11px;">🤖 خودکار رپورٹ</span>
    </div>
  </div>

</div>
</body></html>"""
    return html

# ─────────────────────────────────────────────
def send_email(html, today_date):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🌤️ موسم رپورٹ — تونسہ | {today_date}"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(SENDER_EMAIL, SENDER_PASSWORD)
        s.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
    print("✅ Email bhej di!")

if __name__ == "__main__":
    print("🌤️ Smart Weather Report generating...")
    try:
        data = get_weather()
        today_d = urdu_date(data["daily"]["time"][0])
        html = build_email(data)
        send_email(html, today_d)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
