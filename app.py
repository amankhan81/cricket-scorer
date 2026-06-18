import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
import json
import time
import random
import string

# --- DB CONNECTION ---
URL = "https://pnuyhhbvdzfursvnngwq.supabase.co"
KEY = "sb_publishable_Lmh7sO4LnBkSWgmSjanplg_9qgT7svQ"
supabase = create_client(URL, KEY)

def generate_match_id(length=6):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

def team_abbrev(name):
    words = name.strip().split()
    if len(words) > 1:
        return "".join(w[0].upper() for w in words)
    return name[:3].upper()

def get_match(match_id):
    res = supabase.table("matches").select("*").eq("match_id", match_id).execute()
    if res.data and len(res.data) > 0:
        d = res.data[0]
        if not d.get("history"):       d["history"]       = "[]"
        if not d.get("innings"):       d["innings"]       = 1
        if not d.get("innings1_runs"): d["innings1_runs"] = 0
        if not d.get("team1_name"):    d["team1_name"]    = "Team 1"
        if not d.get("team2_name"):    d["team2_name"]    = "Team 2"
        if not d.get("batting_first"): d["batting_first"] = 1
        return d
    return None

def get_wickets(history_str):
    try:
        hist = json.loads(history_str or "[]")
        return sum(1 for ball in hist if isinstance(ball, dict) and ball.get("w") == 1)
    except Exception:
        return 0

def create_match(match_id, match_overs, team1_name="Team 1", team2_name="Team 2", batting_first=1):
    res = supabase.table("matches").insert({
        "match_id":      match_id,
        "match_overs":   match_overs,
        "runs":          0,
        "balls":         0,
        "history":       "[]",
        "innings":       1,
        "innings1_runs": 0,
        "team1_name":    team1_name,
        "team2_name":    team2_name,
        "batting_first": batting_first
    }).execute()
    return res

def update_score(match_id, runs_inc, balls_inc, is_wicket=False, is_undo=False):
    d = get_match(match_id)
    if not d:
        return
    history = json.loads(d["history"])
    if is_undo:
        if len(history) > 0:
            last = history.pop()
            supabase.table("matches").update({
                "runs":    max(0, d["runs"]  - last.get("r", 0)),
                "balls":   max(0, d["balls"] - last.get("b", 0)),
                "history": json.dumps(history)
            }).eq("match_id", match_id).execute()
    else:
        history.append({"r": runs_inc, "b": balls_inc, "w": 1 if is_wicket else 0})
        supabase.table("matches").update({
            "runs":    d["runs"]  + runs_inc,
            "balls":   d["balls"] + balls_inc,
            "history": json.dumps(history)
        }).eq("match_id", match_id).execute()

def reset_match(match_id):
    supabase.table("matches").update({
        "runs": 0, "balls": 0, "history": "[]",
        "innings": 1, "innings1_runs": 0
    }).eq("match_id", match_id).execute()

def start_second_innings(match_id, innings1_score):
    supabase.table("matches").update({
        "innings": 2, "innings1_runs": innings1_score,
        "runs": 0, "balls": 0, "history": "[]"
    }).eq("match_id", match_id).execute()

def render_html(html_str):
    """Flattens HTML strings to prevent markdown indented-code block bugs in Streamlit."""
    cleaned = " ".join(line.strip() for line in html_str.split("\n"))
    st.markdown(cleaned, unsafe_allow_html=True)

# --- HELPER SVG FOR PREMIUM LOGO ---
SVG_LOGO_MARKUP = """
<svg viewBox="0 0 110 90" width="46" height="40" style="filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.5));">
    <g transform="rotate(-32 50 45)">
        <rect x="47" y="5" width="6" height="22" rx="2" fill="url(#gripGrad)" />
        <line x1="47" y1="10" x2="53" y2="10" stroke="rgba(255,255,255,0.2)" stroke-width="0.8"/>
        <line x1="47" y1="15" x2="53" y2="15" stroke="rgba(255,255,255,0.2)" stroke-width="0.8"/>
        <line x1="47" y1="20" x2="53" y2="20" stroke="rgba(255,255,255,0.2)" stroke-width="0.8"/>
        <path d="M44,27 L56,27 L57,32 L43,32 Z" fill="#b07f3c" />
        <rect x="43" y="32" width="14" height="48" rx="2" fill="url(#woodGrad)" />
    </g>
    <circle cx="75" cy="62" r="11" fill="url(#ballGrad)" />
    <path d="M66,62 Q75,54 84,62" fill="none" stroke="#ffffff" stroke-width="1.8" stroke-dasharray="1.5, 1" />
    <defs>
        <linearGradient id="gripGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#6930c3" />
            <stop offset="100%" stop-color="#3f1c73" />
        </linearGradient>
        <linearGradient id="woodGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#e2b170" />
            <stop offset="50%" stop-color="#bc8646" />
            <stop offset="100%" stop-color="#8c581a" />
        </linearGradient>
        <linearGradient id="ballGrad" x1="30%" y1="30%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#ff4444" />
            <stop offset="60%" stop-color="#bd0000" />
            <stop offset="100%" stop-color="#540000" />
        </linearGradient>
    </defs>
</svg>
"""

def render_main(match_id):
    # Injection of custom styling optimized for zero scrolling and a premium metallic theme
    render_html("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Roboto+Condensed:wght@400;700&display=swap');
            header, footer, #MainMenu { display: none !important; }
            
            /* Radial Dark Metallic theme */
            .stApp { 
                background: radial-gradient(circle at top, #141c2c 0%, #080a10 100%) !important; 
                min-height: 100vh; 
            }
            
            /* Tight container spacing to fit active viewport */
            .block-container { 
                padding: 10px 8px 12px 8px !important; 
                max-width: 440px !important; 
                margin: 0 auto !important; 
            }

            /* Innings badge redesigned into a premium golden-beveled dark-metallic capsule */
            .innings-badge { text-align: center; margin-bottom: 10px; }
            .innings-badge span {
                background: linear-gradient(180deg, #1d283f 0%, #0b111c 100%) !important;
                color: #f3c64f !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                letter-spacing: 1.5px !important;
                text-transform: uppercase !important;
                padding: 6px 22px !important;
                border-radius: 20px !important;
                border: 2px solid #bda064 !important;
                display: inline-block !important;
                box-shadow: inset 0 1.5px 3px rgba(255,255,255,0.15), inset 0 -2px 4px rgba(0,0,0,0.5), 0 4px 10px rgba(0,0,0,0.4) !important;
                text-shadow: 0 1px 2px rgba(0,0,0,0.6) !important;
            }
            
            /* Share scoring link redesigned into a premium glossy 3D green-beveled button */
            .share-pill-wrapper { text-align: center; margin-bottom: 14px; }
            a.share-pill {
                display: inline-flex !important; 
                align-items: center !important;
                justify-content: center !important;
                gap: 6px !important; 
                background: linear-gradient(180deg, #103822 0%, #081d11 100%) !important;
                color: #52d273 !important; 
                font-family: 'Oswald', sans-serif !important;
                font-size: 12px !important; 
                font-weight: 700 !important;
                letter-spacing: 1.5px !important;
                text-transform: uppercase !important; 
                padding: 6px 18px !important;
                border-radius: 20px !important; 
                border: 2.5px solid #52d273 !important;
                text-decoration: none !important;
                border-bottom: none !important;
                box-shadow: inset 0 1.5px 3px rgba(255,255,255,0.15), inset 0 -2px 4px rgba(0,0,0,0.5), 0 4px 8px rgba(0,0,0,0.3) !important;
                text-shadow: 0 1px 2px rgba(0,0,0,0.6) !important;
                transition: transform 0.1s ease !important;
            }
            a.share-pill:hover, a.share-pill:active, a.share-pill:focus {
                text-decoration: none !important;
                color: #52d273 !important;
                border-bottom: none !important;
                transform: scale(0.96) !important;
                outline: none !important;
            }

            /* PREMIUM OVERLAY STYLE TICKER BAR */
            .broadcast-ticker {
                display: flex; align-items: center; justify-content: space-between;
                background: linear-gradient(180deg, #24282c 0%, #0f1113 100%);
                border: 1.5px solid #3c4045; border-radius: 14px;
                padding: 6px 10px; margin-bottom: 12px;
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.1), 0 10px 20px rgba(0,0,0,0.6);
                position: relative; overflow: hidden; width: 100%;
                font-family: 'Roboto Condensed', sans-serif;
            }
            .ticker-gold-bar {
                position: absolute; left: 0; top: 0; bottom: 0; width: 5px;
                background: linear-gradient(180deg, #ffb700, #c38400);
                box-shadow: 0 0 6px rgba(255, 183, 0, 0.5);
            }
            .ticker-logo-box {
                margin-left: 4px; margin-right: 6px;
                display: flex; align-items: center; justify-content: center;
            }
            .ticker-divider {
                width: 3px; height: 36px;
                background: linear-gradient(180deg, #7f8285, #3a3c3e, #7f8285);
                border-left: 1px solid #111; border-right: 1px solid #555;
                margin: 0 4px; opacity: 0.8;
            }
            .ticker-section {
                display: flex; flex-direction: column; align-items: center; justify-content: center;
                text-align: center;
            }
            .batting-sec { flex: 1.1; }
            .ticker-lbl {
                color: #ffffff; font-size: 10px; font-weight: 700;
                letter-spacing: 1px; text-transform: uppercase; margin-bottom: 1px;
            }
            .ticker-team-box {
                border: 1.5px solid #c3a469; border-radius: 4px;
                padding: 1px 8px; background: rgba(195, 164, 105, 0.08);
                color: #ffcc00; font-family: 'Oswald', sans-serif;
                font-size: 14px; font-weight: 700; text-shadow: 0 0 4px rgba(255, 204, 0, 0.4);
                line-height: 1.1;
            }
            .score-sec { flex: 1.6; }
            .ticker-val-score {
                color: #ffffff; font-family: 'Oswald', sans-serif;
                font-size: 38px; font-weight: 700; line-height: 1; letter-spacing: -1px;
            }
            .overs-sec { flex: 1.4; position: relative; }
            .overs-arch-wrap { display: flex; flex-direction: column; align-items: center; position: relative; }
            .overs-arch {
                position: absolute; top: -4px; width: 28px; height: 4px;
                border-top: 1.5px solid rgba(255, 255, 255, 0.35);
                border-radius: 50% 50% 0 0;
            }
            .ticker-val-overs {
                color: #ffd700; font-family: 'Oswald', sans-serif;
                font-size: 24px; font-weight: 700; line-height: 1;
                text-shadow: 0 0 8px rgba(255, 215, 0, 0.5), 0 0 15px rgba(255, 215, 0, 0.2);
            }
            .max-sec { flex: 1; }
            .ticker-max-box {
                border: 1px solid #5c6065; border-radius: 4px;
                padding: 1px 8px; background: rgba(255,255,255,0.05);
                color: #ffffff; font-family: 'Oswald', sans-serif;
                font-size: 14px; font-weight: 700; line-height: 1.1;
            }

            [data-testid="stHorizontalBlock"] { gap: 6px !important; flex-wrap: nowrap !important; }
            [data-testid="stColumn"] { padding: 0 !important; min-width: 0 !important; }
            [data-testid="stVerticalBlockBorderWrapper"] { gap: 0 !important; }
            [data-testid="stVerticalBlock"] > * { margin-bottom: 0 !important; }
            div[data-testid="stVerticalBlock"] > div { gap: 0 !important; }
            [data-testid="element-container"] { margin: 0 !important; padding: 0 !important; }
            .stButton { margin: 0 !important; padding: 0 !important; }

            /* SCORING BUTTONS GLOW OVERHAUL (glowy neon yellow/gold like overs label) */
            .glossy-btn-container button {
                background: linear-gradient(135deg, rgba(20, 38, 77, 0.8) 0%, rgba(10, 20, 41, 0.95) 100%) !important;
                border: 2px solid rgba(195, 164, 105, 0.6) !important;
                border-radius: 18px !important;
                box-shadow: inset 0 1.5px 3px rgba(255,255,255,0.15), inset 0 -3px 6px rgba(0,0,0,0.5), 0 5px 12px rgba(0,0,0,0.4) !important;
                color: #ffd700 !important; /* Glowy yellow color matching overs section */
                font-family: 'Oswald', sans-serif !important;
                font-size: 28px !important;
                font-weight: 700 !important;
                height: 70px !important;
                width: 100% !important;
                text-shadow: 0 0 8px rgba(255, 215, 0, 0.7), 0 0 15px rgba(255, 215, 0, 0.3) !important; /* Neon golden glow shadow */
                transition: transform 0.08s ease, box-shadow 0.08s ease !important;
            }
            .glossy-btn-container button:active {
                transform: scale(0.95) !important;
                box-shadow: inset 0 2px 4px rgba(0,0,0,0.7) !important;
            }
            
            /* Preserving unique button color behaviors with complementary glows */
            .btn-four button { color: #f3c64f !important; text-shadow: 0 0 8px rgba(243, 198, 79, 0.7), 0 0 15px rgba(243, 198, 79, 0.3) !important; }
            .btn-six button { color: #52d273 !important; text-shadow: 0 0 8px rgba(82, 210, 115, 0.7), 0 0 15px rgba(82, 210, 115, 0.3) !important; }
            .btn-out button { color: #ec4849 !important; font-size: 22px !important; text-shadow: 0 0 8px rgba(236, 72, 73, 0.7), 0 0 15px rgba(236, 72, 73, 0.3) !important; }
            .btn-undo button { color: #4da6ff !important; font-size: 18px !important; text-shadow: 0 0 8px rgba(77, 166, 255, 0.7), 0 0 15px rgba(77, 166, 255, 0.3) !important; }

            .add-extras-btn button {
                background: linear-gradient(180deg, #182e54 0%, #0b1528 100%) !important;
                border: 2px solid #bda064 !important;
                border-radius: 24px !important;
                box-shadow: inset 0 2px 4px rgba(255,255,255,0.15), inset 0 -2px 4px rgba(0,0,0,0.4), 0 6px 12px rgba(0,0,0,0.5) !important;
                color: #ffffff !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 20px !important;
                font-weight: 700 !important;
                height: 54px !important;
                width: 100% !important;
                letter-spacing: 1px;
                text-shadow: 0 1px 3px rgba(0,0,0,0.6) !important;
                margin: 10px 0 !important;
            }
            .add-extras-btn button:active {
                transform: scale(0.97) !important;
            }

            .extras-modal {
                background: #11203b !important;
                border: 2px solid #bda064 !important;
                border-radius: 20px !important;
                overflow: hidden !important;
                box-shadow: inset 0 2px 3px rgba(255,255,255,0.1), 0 12px 28px rgba(0,0,0,0.6) !important;
                margin: 6px 0 !important;
            }
            .extras-header {
                background: linear-gradient(180deg, #9b814a 0%, #766236 100%) !important;
                color: #ffffff !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 18px !important;
                font-weight: 700 !important;
                text-align: center !important;
                padding: 10px 0 !important;
                letter-spacing: 2px !important;
                text-shadow: 0 1.5px 3px rgba(0,0,0,0.6) !important;
                text-transform: uppercase !important;
                border-bottom: 2px solid #bda064 !important;
            }
            .extras-body {
                padding: 16px 12px !important;
            }

            .extra-wide-btn button {
                background: linear-gradient(180deg, #1b2e50 0%, #0d1729 100%) !important;
                border: 2px solid #bda064 !important;
                border-radius: 16px !important;
                box-shadow: inset 0 2px 3px rgba(255,255,255,0.1), inset 0 -3px 5px rgba(0,0,0,0.5), 0 4px 10px rgba(0,0,0,0.4) !important;
                color: #ffffff !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 24px !important;
                font-weight: 700 !important;
                height: 64px !important;
                width: 100% !important;
                text-shadow: 0 1.5px 2px rgba(0,0,0,0.6) !important;
            }
            
            .extra-no-btn button {
                background: linear-gradient(180deg, #1b2e50 0%, #0d1729 100%) !important;
                border: 1.5px solid #bda064 !important;
                border-radius: 14px !important;
                box-shadow: inset 0 1.5px 2.5px rgba(255,255,255,0.1), inset 0 -2.5px 4px rgba(0,0,0,0.5), 0 3px 8px rgba(0,0,0,0.4) !important;
                color: #ffffff !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 16px !important;
                font-weight: 700 !important;
                height: 46px !important;
                width: 100% !important;
                padding: 0 !important;
                text-shadow: 0 1px 2px rgba(0,0,0,0.5) !important;
            }

            .extra-cancel-btn button {
                background: transparent !important;
                border: 2px solid #bda064 !important;
                border-radius: 20px !important;
                color: #ff5252 !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 15px !important;
                font-weight: 700 !important;
                height: 38px !important;
                width: 130px !important;
                margin: 15px auto 4px auto !important;
                display: block !important;
                text-shadow: 0 1px 2px rgba(0,0,0,0.5) !important;
                text-transform: uppercase !important;
                letter-spacing: 1.5px !important;
            }

            .premium-reset-btn button {
                background: linear-gradient(180deg, #321010 0%, #190808 100%) !important;
                border: 2px solid #ff5252 !important;
                border-radius: 16px !important;
                box-shadow: inset 0 1.5px 2px rgba(255,255,255,0.1), inset 0 -3px 6px rgba(0,0,0,0.5), 0 4px 10px rgba(0,0,0,0.4) !important;
                color: #ff5252 !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                height: 44px !important;
                letter-spacing: 1px !important;
                text-shadow: 0 1px 2px rgba(0,0,0,0.5) !important;
                text-transform: uppercase !important;
                width: 100% !important;
            }
            .premium-theme-btn button {
                background: linear-gradient(180deg, #1b2e50 0%, #0d1729 100%) !important;
                border: 2px solid #bda064 !important;
                border-radius: 16px !important;
                box-shadow: inset 0 1.5px 2px rgba(255,255,255,0.1), inset 0 -3px 6px rgba(0,0,0,0.5), 0 4px 10px rgba(0,0,0,0.4) !important;
                color: #f3c64f !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                height: 44px !important;
                letter-spacing: 1px !important;
                text-shadow: 0 1px 2px rgba(0,0,0,0.5) !important;
                text-transform: uppercase !important;
                width: 100% !important;
            }

            .target-bar {
                background: rgba(195, 164, 105, 0.08); border: 1.5px solid rgba(195, 164, 105, 0.3);
                border-radius: 10px; padding: 6px 12px; text-align: center; margin-bottom: 10px;
                font-family: 'Roboto Condensed', sans-serif; color: #e5c185; font-size: 13px; font-weight: 700; letter-spacing: 0.5px;
            }
            .credit { text-align: center; margin-top: 12px; padding-top: 8px; border-top: 1.5px solid rgba(255,255,255,0.05); }
            .credit span { font-family: 'Roboto Condensed', sans-serif; font-size: 9px; letter-spacing: 1.5px; color: rgba(255,255,255,0.2); text-transform: uppercase; }
            .credit strong { color: rgba(195, 164, 105, 0.5); font-weight: 700; }
        </style>
    """)

    # Specific theme override for Light Mode
    if st.session_state.get("light_mode"):
        render_html("""
            <style>
                .stApp { background: radial-gradient(circle at top, #f0f4fa 0%, #d4dfec 100%) !important; }
                .broadcast-ticker { background: linear-gradient(180deg, #ffffff 0%, #eef3fb 100%) !important; border-color: rgba(0,0,0,0.15) !important; box-shadow: 0 6px 15px rgba(0,0,0,0.08); }
                .ticker-val-score { color: #141c2c !important; }
                .ticker-lbl { color: #555555 !important; }
                .ticker-max-box { border-color: rgba(0,0,0,0.2) !important; background: rgba(0,0,0,0.03) !important; color: #141c2c !important; }
                .glossy-btn-container button {
                    background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(230,238,248,0.95) 100%) !important;
                    color: #ffd700 !important; border-color: #bda064 !important;
                    box-shadow: inset 0 1.5px 3px rgba(255,255,255,1), 0 4px 8px rgba(0,0,0,0.08) !important;
                }
                .add-extras-btn button {
                    background: linear-gradient(180deg, #ffffff 0%, #eef3fb 100%) !important;
                    color: #141c2c !important; border-color: #bda064 !important;
                }
                .extras-modal { background: #f0f4fa !important; border-color: #9b814a !important; }
                .extra-wide-btn button, .extra-no-btn button {
                    background: linear-gradient(180deg, #ffffff 0%, #eef3fb 100%) !important;
                    color: #141c2c !important; border-color: #9b814a !important;
                }
                .extra-cancel-btn button { background: rgba(0,0,0,0.02) !important; border-color: #bda064 !important; }
                .target-bar { background: rgba(0,0,0,0.03) !important; color: #8c581a !important; border-color: rgba(140,88,26,0.2) !important; }
                .credit span { color: rgba(0,0,0,0.4) !important; }
            </style>
        """)

    # --- DEFINE OVERLAY LINK ---
    base_url = st.context.url if hasattr(st, 'context') and hasattr(st.context, 'url') else "https://your-app.streamlit.app"
    if "?" in base_url:
        base_url = base_url.split("?")[0]
    overlay_url = base_url + "?mode=overlay&match=" + match_id

    # Create / Setup state
    if not match_id:
        st.markdown("<div style='color:white;text-align:center;font-family:Oswald;font-size:30px;margin-top:35px;margin-bottom:4px;'>🏏 Smart Cricket Scorer</div>", unsafe_allow_html=True)
        st.markdown("<div style='color:rgba(255,255,255,0.4);text-align:center;font-family:Roboto Condensed;font-size:11px;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:24px;'>MATCH SETUP</div>", unsafe_allow_html=True)

        team1_in = st.text_input("TEAM 1 NAME", value="Team 1", placeholder="e.g. Desert Lions")
        team2_in = st.text_input("TEAM 2 NAME", value="Team 2", placeholder="e.g. Pak Eagles")
        batting_first_sel = st.selectbox("WHO IS BATTING FIRST?", options=[team1_in, team2_in])
        ov_in = st.number_input("MATCH OVERS", min_value=1, max_value=50, value=10)

        st.markdown('<div class="add-extras-btn">', unsafe_allow_html=True)
        if st.button("CREATE MATCH", use_container_width=True):
            new_id = generate_match_id()
            batting_first_num = 1 if batting_first_sel == team1_in else 2
            try:
                create_match(new_id, ov_in, team1_in, team2_in, batting_first_num)
                st.query_params["match"] = new_id
                st.rerun()
            except Exception as e:
                st.error(f"Failed to create match: {e}")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="credit"><span>Created by <strong>Amanullah Khan</strong></span></div>', unsafe_allow_html=True)
        return

    # Load parameters
    d = get_match(match_id)
    if not d:
        st.error("Match not found: " + match_id)
        st.markdown('<div class="add-extras-btn">', unsafe_allow_html=True)
        if st.button("CREATE NEW MATCH", use_container_width=True):
            st.query_params.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    max_balls     = int(d['match_overs']) * 6
    innings       = int(d.get('innings') or 1)
    innings1_runs = int(d.get('innings1_runs') or 0)
    current_balls = int(d['balls'])
    current_runs  = int(d['runs'])
    innings_over  = current_balls >= max_balls
    wickets       = get_wickets(d.get("history"))

    team1_name    = d.get("team1_name") or "Team 1"
    team2_name    = d.get("team2_name") or "Team 2"
    batting_first = int(d.get("batting_first") or 1)
    
    if innings == 1:
        batting_team = team1_name if batting_first == 1 else team2_name
        bowling_team = team2_name if batting_first == 1 else team1_name
    else:
        batting_team = team2_name if batting_first == 1 else team1_name
        bowling_team = team1_name if batting_first == 1 else team2_name

    # Check innings boundaries
    if innings == 1 and innings_over:
        render_html(f"""
            <div style="background:rgba(20,31,58,0.5); border:1.5px solid rgba(255,255,255,0.08); border-radius:20px; padding:24px 10px; text-align:center; margin:15px 0;">
                <h2 style="font-family:'Oswald',sans-serif; color:#f0c040; font-size:24px; margin-bottom:8px;">Innings Over</h2>
                <div style="font-family:'Oswald',sans-serif; color:white; font-size:52px; font-weight:700; line-height:1; margin-bottom:4px;">{current_runs}/{wickets}</div>
                <div style="font-family:'Roboto Condensed',sans-serif; color:rgba(255,255,255,0.45); font-size:11px; letter-spacing:2.5px; text-transform:uppercase; margin-bottom:15px;">{batting_team} — 1st Innings Score</div>
                <p style="font-family:'Roboto Condensed',sans-serif; color:rgba(255,255,255,0.6); font-size:14px;">{bowling_team} to chase. Start 2nd innings.</p>
            </div>
        """)
        st.markdown('<div class="add-extras-btn">', unsafe_allow_html=True)
        if st.button("START 2ND INNINGS", use_container_width=True):
            start_second_innings(match_id, current_runs)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        _render_overlay_box(overlay_url, match_id=match_id, confirm_key="confirm_reset_mid", reset_key="reset_mid", show_reset=True)
        return

    if innings == 2 and innings_over:
        team_inn1 = team1_name if batting_first == 1 else team2_name
        team_inn2 = team2_name if batting_first == 1 else team1_name
        if current_runs > innings1_runs:
            result = team_inn2 + " wins by " + str(current_runs - innings1_runs) + " runs! 🎉"
        elif current_runs < innings1_runs:
            result = team_inn1 + " wins by " + str(innings1_runs - current_runs) + " runs! 🎉"
        else:
            result = "It's a tie! 🤝"
        render_html(f"""
            <div style="background:rgba(195,164,105,0.1); border:1.5px solid rgba(195,164,105,0.3); border-radius:20px; padding:26px 15px; text-align:center; margin:15px 0;">
                <h2 style="font-family:'Oswald',sans-serif; color:#f0c040; font-size:28px; margin-bottom:8px;">Match Over</h2>
                <p style="font-family:'Roboto Condensed',sans-serif; color:rgba(255,255,255,0.7); font-size:16px; margin-bottom:18px;">{result}</p>
                <div style="font-family:'Roboto Condensed',sans-serif; color:rgba(255,255,255,0.5); font-size:12px; letter-spacing:1.5px;">
                    {team_inn1}: {innings1_runs} &nbsp;|&nbsp; {team_inn2}: {current_runs}/{wickets}
                </div>
            </div>
        """)
        st.markdown('<div class="add-extras-btn">', unsafe_allow_html=True)
        if st.button("NEW MATCH", use_container_width=True):
            st.query_params.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # Redesigned Innings Badge & Share Pill layout rendered cleanly via flattened HTML blocks
    render_html(f"""
        <div class="innings-badge">
            <span>{batting_team} &mdash; {"1st" if innings == 1 else "2nd"} Innings</span>
        </div>
    """)
    
    whatsapp_share_url = "https://easyscoring.streamlit.app/?match=" + match_id
    whatsapp_link = "https://wa.me/?text=" + whatsapp_share_url
    
    render_html(f"""
        <div class="share-pill-wrapper">
            <a class="share-pill" href="{whatsapp_link}" target="_blank">📲 Share Scoring</a>
        </div>
    """)

    # Render Premium Scoreboard Overhaul Ticker at the top
    batting_abbrev = team_abbrev(batting_team)
    overs_val = f"{current_balls//6}.{current_balls%6}"
    max_overs_val = str(d['match_overs'])
    
    render_html(f"""
        <div class="broadcast-ticker">
            <div class="ticker-gold-bar"></div>
            <div class="ticker-logo-box">
                {SVG_LOGO_MARKUP}
            </div>
            <div class="ticker-section batting-sec">
                <span class="ticker-lbl">BATTING</span>
                <div class="ticker-team-box">{batting_abbrev}</div>
            </div>
            <div class="ticker-divider"></div>
            <div class="ticker-section score-sec">
                <span class="ticker-val-score">{current_runs}/{wickets}</span>
            </div>
            <div class="ticker-divider"></div>
            <div class="ticker-section overs-sec">
                <div class="overs-arch-wrap">
                    <div class="overs-arch"></div>
                    <span class="ticker-lbl">OVERS</span>
                </div>
                <span class="ticker-val-overs">{overs_val}</span>
            </div>
            <div class="ticker-divider"></div>
            <div class="ticker-section max-sec">
                <span class="ticker-lbl">MAX</span>
                <div class="ticker-max-box">{max_overs_val}</div>
            </div>
        </div>
    """)

    if innings == 2:
        needed     = innings1_runs - current_runs + 1
        balls_left = max_balls - current_balls
        overs_left = str(balls_left // 6) + "." + str(balls_left % 6)
        if needed > 0:
            st.markdown('<div class="target-bar">🎯 Need ' + str(needed) + ' runs in ' + overs_left + ' overs</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="target-bar">✅ Target achieved!</div>', unsafe_allow_html=True)

    # POPUP EXTRAS MODAL FLOW (Mapped exactly to image_f0409d.png parameters)
    if st.session_state.get("show_extras", False):
        st.markdown('<div class="extras-modal">', unsafe_allow_html=True)
        st.markdown('<div class="extras-header">ADD EXTRAS</div>', unsafe_allow_html=True)
        st.markdown('<div class="extras-body">', unsafe_allow_html=True)
        
        # Row 1 (Wides): W+0 (adds 1), W+1 (2), W+2 (3), W+3 (4), W+4 (5)
        st.markdown('<div style="margin-bottom: 5px; text-align: center; color: rgba(255,255,255,0.4); font-family:\'Roboto Condensed\', sans-serif; font-size:10px; font-weight:700; letter-spacing:1px; text-transform:uppercase;">Wide Balls</div>', unsafe_allow_html=True)
        wcols = st.columns(5)
        for idx, val in enumerate([0, 1, 2, 3, 4]):
            with wcols[idx]:
                st.markdown('<div class="extra-wide-btn">', unsafe_allow_html=True)
                if st.button(f"W+{val}", key=f"popup_w_{val}", use_container_width=True):
                    # Adds val + 1 runs as wide (extra ball is not counted, so balls_inc = 0)
                    update_score(match_id, val + 1, 0)
                    st.session_state.show_extras = False
                    st.session_state.continue_after_target = False
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div style="height: 12px;"></div>', unsafe_allow_html=True)
        
        # Row 2 (No Balls): N+0 (adds 1), N+1 (2), N+2 (3), N+3 (4), N+4 (5), N+6 (7)
        st.markdown('<div style="margin-bottom: 5px; text-align: center; color: rgba(255,255,255,0.4); font-family:\'Roboto Condensed\', sans-serif; font-size:10px; font-weight:700; letter-spacing:1px; text-transform:uppercase;">No Balls</div>', unsafe_allow_html=True)
        ncols = st.columns(6)
        for idx, val in enumerate([0, 1, 2, 3, 4, 6]):
            with ncols[idx]:
                st.markdown('<div class="extra-no-btn">', unsafe_allow_html=True)
                if st.button(f"N+{val}", key=f"popup_n_{val}", use_container_width=True):
                    # Adds val + 1 runs as no ball (extra ball is not counted, so balls_inc = 0)
                    update_score(match_id, val + 1, 0)
                    st.session_state.show_extras = False
                    st.session_state.continue_after_target = False
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
                
        # Cancel Outline Button (Bevel Gold/Red Capsule)
        st.markdown('<div class="extra-cancel-btn">', unsafe_allow_html=True)
        if st.button("Cancel", key="cancel_extras_popup", use_container_width=True):
            st.session_state.show_extras = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    else:
        # MAIN SCORING CONTROLS AREA
        # Row 1: 0, 1, 2, 3 (Glassy deep blue look with yellow glowing labels)
        c0, c1, c2, c3 = st.columns(4)
        for idx, val in enumerate(["0", "1", "2", "3"]):
            col_target = [c0, c1, c2, c3][idx]
            with col_target:
                st.markdown('<div class="glossy-btn-container">', unsafe_allow_html=True)
                if st.button(val, key=f"g{val}", use_container_width=True):
                    update_score(match_id, int(val), 1)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # Row 2: 4, 6, OUT, UNDO
        c4, c5, cout, cundo = st.columns(4)
        with c4:
            st.markdown('<div class="glossy-btn-container btn-four">', unsafe_allow_html=True)
            if st.button("4", key="g4", use_container_width=True):
                update_score(match_id, 4, 1)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c5:
            st.markdown('<div class="glossy-btn-container btn-six">', unsafe_allow_html=True)
            if st.button("6", key="g6", use_container_width=True):
                update_score(match_id, 6, 1)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with cout:
            st.markdown('<div class="glossy-btn-container btn-out">', unsafe_allow_html=True)
            if st.button("OUT", key="gout", use_container_width=True):
                update_score(match_id, 0, 1, is_wicket=True)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with cundo:
            st.markdown('<div class="glossy-btn-container btn-undo">', unsafe_allow_html=True)
            if st.button("UNDO", key="gundo", use_container_width=True):
                update_score(match_id, 0, 0, is_undo=True)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # Huge Premium Pill Style 'ADD EXTRAS' Button directly below
        st.markdown('<div class="add-extras-btn">', unsafe_allow_html=True)
        if st.button("ADD EXTRAS", key="trigger_extras_popup", use_container_width=True):
            st.session_state.show_extras = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Bottom Settings section
    if st.session_state.get("confirm_reset_active"):
        render_html("""
            <div style="background:rgba(235,87,87,0.12); border:1.5px solid rgba(235,87,87,0.35); border-radius:14px; padding:12px; margin-top:10px; text-align:center;">
                <p style="font-family:'Roboto Condensed',sans-serif; color:white; font-size:14px; font-weight:700; margin-bottom:10px;">⚠️ Confirm Reset Match?</p>
            </div>
        """)
        cy, cn = st.columns(2)
        with cy:
            st.markdown('<div class="premium-reset-btn">', unsafe_allow_html=True)
            if st.button("YES, RESET", key="confirm_yes_active", use_container_width=True):
                reset_match(match_id)
                st.session_state.confirm_reset_active = False
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with cn:
            st.markdown('<div class="premium-theme-btn">', unsafe_allow_html=True)
            if st.button("CANCEL", key="confirm_no_active", use_container_width=True):
                st.session_state.confirm_reset_active = False
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        _render_overlay_box(overlay_url, match_id=match_id, confirm_key="confirm_reset_active", reset_key="reset", show_reset=True)

    st.markdown('<div class="credit"><span>Created by <strong>Amanullah Khan</strong></span></div>', unsafe_allow_html=True)

def _render_overlay_box(overlay_url, match_id=None, confirm_key=None, reset_key=None, show_reset=False):
    """Renders the OBS Link Copy action and premium redesigned control layout."""
    components.html(f"""
        <style>
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            body {{ background:transparent; font-family:'Roboto Condensed',sans-serif; }}
            .wrap {{ display:flex; flex-direction:column; gap:5px; margin-bottom:10px; }}
            .copy-btn {{
                width:100%; height:38px; cursor:pointer;
                background:rgba(195, 164, 105, 0.15); color:#c3a469;
                font-size:12px; font-weight:700; letter-spacing:1.5px;
                border:1.5px solid rgba(195, 164, 105, 0.4); border-radius:10px;
                text-transform:uppercase; transition: background 0.2s;
            }}
            .copy-btn:hover {{ background:rgba(195, 164, 105, 0.25); }}
            .url-box {{
                background:rgba(0,0,0,0.35); border:1px solid rgba(195,164,105,0.25);
                border-radius:8px; padding:6px 10px;
                display:flex; align-items:center; gap:8px;
            }}
            .url-text {{ font-size:10px; color:#c3a469; word-break:break-all; flex:1; }}
            .hint {{ font-size:9px; color:rgba(255,255,255,0.3); letter-spacing:1px; text-transform:uppercase; text-align:center; }}
        </style>
        <div class="wrap">
            <button class="copy-btn" onclick="
                navigator.clipboard.writeText('{overlay_url}').then(function(){{
                    this.innerText='✅ Copied!';
                    var s=this; setTimeout(function(){{s.innerText='📋 Copy Overlay Link';}},2000);
                }}.bind(this)).catch(function(){{
                    this.innerText='⚠️ Failed';
                    var s=this; setTimeout(function(){{s.innerText='📋 Copy Overlay Link';}},2000);
                }}.bind(this));">📋 Copy Overlay Link</button>
            <div class="url-box"><span>🔗</span><span class="url-text">{overlay_url}</span></div>
            <div class="hint">Add as browser source in OBS / CameraFi / PrismLive</div>
        </div>
    """, height=100)

    if show_reset:
        is_light = st.session_state.get("light_mode", False)
        theme_label = "☀️ LIGHT MODE" if not is_light else "🌙 DARK MODE"
        col_reset, col_theme = st.columns(2)
        with col_reset:
            st.markdown('<div class="premium-reset-btn">', unsafe_allow_html=True)
            if st.button("🔄 RESET MATCH", key=reset_key, use_container_width=True):
                st.session_state[confirm_key] = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with col_theme:
            st.markdown('<div class="premium-theme-btn">', unsafe_allow_html=True)
            if st.button(theme_label, key="theme_toggle_" + reset_key, use_container_width=True):
                st.session_state["light_mode"] = not is_light
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
#  PREMIUM OVERLAY BROADCAST TICKER MODE (OBS & STREAMS)
# ════════════════════════════════════════════════════════
def render_overlay(match_id):
    render_html("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@700&family=Roboto+Condensed:wght@700&display=swap');
            
            /* FORCE ALL STREAMLIT WRAPPER BACKGROUNDS TO TRANSPARENT */
            html, body, .stApp, 
            [data-testid="stAppViewContainer"], 
            [data-testid="stMainBlockContainer"],
            [data-testid="stAppViewBlockContainer"],
            [data-testid="stVerticalBlock"],
            .main, .block-container,
            section.main,
            div.stMain,
            div.stMainBlockContainer,
            div.stAppHeader,
            div.stAppViewContainer,
            div.stAppViewBlockContainer {
                background: transparent !important;
                background-color: transparent !important;
                background-image: none !important;
                border: none !important;
                box-shadow: none !important;
            }
            
            /* Hide distracting UI panels completely */
            [data-testid="stHeader"], 
            [data-testid="stSidebar"], 
            [data-testid="stToolbar"], 
            [data-testid="stDecoration"], 
            [data-testid="stStatusWidget"], 
            footer {
                display: none !important;
                height: 0 !important;
                width: 0 !important;
                opacity: 0 !important;
            }

            .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
            
            /* Premium Broadcast ticker layout exactly matching Screenshot 2026-06-18 120122.png */
            .ticker-overlay-container {
                position: fixed; bottom: 14px; left: 14px;
                display: inline-flex; align-items: center;
                background: linear-gradient(180deg, #24282c 0%, #0f1113 100%);
                border: 2px solid #3c4045; border-radius: 16px;
                padding: 8px 16px;
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.15), 0 12px 24px rgba(0,0,0,0.6);
                overflow: hidden; font-family: 'Roboto Condensed', sans-serif;
            }
            .ticker-accent-bar {
                position: absolute; left: 0; top: 0; bottom: 0; width: 6px;
                background: linear-gradient(180deg, #ffb700, #c38400);
                box-shadow: 0 0 8px rgba(255, 183, 0, 0.6);
            }
            .ticker-logo-cell {
                margin-left: 8px; margin-right: 12px;
                display: flex; align-items: center; justify-content: center;
            }
            .ticker-vertical-divider {
                width: 3px; height: 42px;
                background: linear-gradient(180deg, #7f8285, #3a3c3e, #7f8285);
                border-left: 1px solid #111; border-right: 1px solid #555;
                margin: 0 12px; opacity: 0.8;
            }
            .ticker-cell {
                display: flex; flex-direction: column; align-items: center; justify-content: center;
                text-align: center;
            }
            .ticker-label-text {
                color: #ffffff; font-size: 11px; font-weight: 700;
                letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 2px;
            }
            .ticker-box-gold {
                border: 1.5px solid #c3a469; border-radius: 4px;
                padding: 1px 12px; background: rgba(195, 164, 105, 0.08);
                color: #ffcc00; font-family: 'Oswald', sans-serif;
                font-size: 16px; font-weight: 700; text-shadow: 0 0 4px rgba(255, 204, 0, 0.5);
                line-height: 1.2;
            }
            .ticker-score-giant {
                color: #ffffff; font-family: 'Oswald', sans-serif;
                font-size: 46px; font-weight: 700; line-height: 1; letter-spacing: -1px;
            }
            .ticker-overs-giant {
                color: #ffd700; font-family: 'Oswald', sans-serif;
                font-size: 28px; font-weight: 700; line-height: 1;
                text-shadow: 0 0 10px rgba(255, 215, 0, 0.6), 0 0 20px rgba(255, 215, 0, 0.3);
            }
            .ticker-box-silver {
                border: 1.5px solid #5c6065; border-radius: 4px;
                padding: 1px 12px; background: rgba(255,255,255,0.06);
                color: #ffffff; font-family: 'Oswald', sans-serif;
                font-size: 16px; font-weight: 700; line-height: 1.2;
            }
            .ticker-winner {
                font-family: 'Roboto Condensed', sans-serif; font-size: 12px; font-weight: 700;
                letter-spacing: 2px; color: #4ade80; text-transform: uppercase;
                padding: 4px 10px; background: rgba(74,222,128,0.15);
                border: 1px solid rgba(74,222,128,0.35); border-radius: 6px; white-space: nowrap;
            }
        </style>
    """)

    d = get_match(match_id)
    if not d:
        st.markdown("<div style='color:red;font-family:monospace;padding:10px;'>Match not found: " + match_id + "</div>", unsafe_allow_html=True)
        return

    innings       = int(d.get("innings") or 1)
    max_balls     = int(d['match_overs']) * 6
    current_balls = int(d['balls'])
    overs_str     = str(current_balls // 6) + "." + str(current_balls % 6)
    max_overs     = int(d['match_overs'])
    innings1_runs = int(d.get("innings1_runs") or 0)
    current_runs  = int(d["runs"])
    needed        = innings1_runs - current_runs + 1
    target_val    = innings1_runs + 1
    need_val      = max(0, needed)
    balls_left    = max(0, max_balls - current_balls)
    need_color    = "#ff6b6b" if needed > 0 else "#6fcf97"
    innings_over  = current_balls >= max_balls
    wickets       = get_wickets(d.get("history"))

    team1_name    = d.get("team1_name") or "Team 1"
    team2_name    = d.get("team2_name") or "Team 2"
    batting_first = int(d.get("batting_first") or 1)
    team_inn1     = team1_name if batting_first == 1 else team2_name
    team_inn2     = team2_name if batting_first == 1 else team1_name
    
    if innings == 1:
        batting_team = team_inn1
    else:
        batting_team = team_inn2
    batting_abbrev = team_abbrev(batting_team)

    match_over = innings == 2 and innings_over
    if match_over:
        if current_runs > innings1_runs:
            winner_text = team_inn2 + " WON"
        elif current_runs < innings1_runs:
            winner_text = team_inn1 + " WON"
        else:
            winner_text = "TIE"
    else:
        winner_text = ""

    # Recreate the premium markup overlay seamlessly
    t = f'<div class="ticker-overlay-container">'
    t += '  <div class="ticker-accent-bar"></div>'
    t += f'  <div class="ticker-logo-cell">{SVG_LOGO_MARKUP}</div>'
    
    t += '  <div class="ticker-cell" style="width: 70px;">'
    t += '    <span class="ticker-label-text">BATTING</span>'
    t += f'    <div class="ticker-box-gold">{batting_abbrev}</div>'
    t += '  </div>'
    
    t += '  <div class="ticker-vertical-divider"></div>'
    
    t += '  <div class="ticker-cell" style="min-width: 90px;">'
    t += f'    <span class="ticker-label-text" style="opacity: 0.7;">LIVE SCORE</span>'
    t += f'    <span class="ticker-score-giant">{current_runs}/{wickets}</span>'
    t += '  </div>'
    
    t += '  <div class="ticker-vertical-divider"></div>'
    
    t += '  <div class="ticker-cell" style="width: 75px; position: relative;">'
    t += '    <div style="position: absolute; top:-2px; width:30px; height:4px; border-top:2px solid rgba(255,255,255,0.4); border-radius:50% 50% 0 0;"></div>'
    t += '    <span class="ticker-label-text">OVERS</span>'
    t += f'    <span class="ticker-overs-giant">{overs_str}</span>'
    t += '  </div>'
    
    t += '  <div class="ticker-vertical-divider"></div>'
    
    t += '  <div class="ticker-cell" style="width: 65px;">'
    t += '    <span class="ticker-label-text">MAX</span>'
    t += f'    <div class="ticker-box-silver">{max_overs}</div>'
    t += '  </div>'

    if match_over:
        t += '  <div class="ticker-vertical-divider"></div>'
        t += f'  <div class="ticker-cell"><div class="ticker-winner">🏆 {winner_text}</div></div>'
    elif innings == 2:
        t += '  <div class="ticker-vertical-divider"></div>'
        t += '  <div class="ticker-cell" style="padding: 0 4px;">'
        t += '    <span class="ticker-label-text" style="color:#ffd700;">CHASE</span>'
        t += f'    <span style="font-family:\'Oswald\'; font-weight:700; font-size:18px; color:{need_color};">{need_val} off {balls_left}</span>'
        t += '  </div>'

    t += '</div>'

    st.markdown(t, unsafe_allow_html=True)
    time.sleep(2)
    st.rerun()

# ════════════════════════════════════════════════════════
#  ROUTING INITIATOR
# ════════════════════════════════════════════════════════
params   = st.query_params
mode     = params.get("mode", "")
match_id = params.get("match", "").strip().upper()

if mode == "overlay":
    render_overlay(match_id)
else:
    render_main(match_id)
