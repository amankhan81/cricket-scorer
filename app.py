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

# --- HELPER SVG FOR PREMIUM LOGO (BAT & BALL SECTIONS REMOVED FOR CLEAN SPACE) ---
SVG_LOGO_MARKUP = """
<svg viewBox="0 0 110 90" width="46" height="40" style="filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.5));">
    <circle cx="55" cy="45" r="22" fill="url(#ballGrad)" />
    <path d="M37,45 Q55,29 73,45" fill="none" stroke="#ffffff" stroke-width="3" stroke-dasharray="3, 2" />
    <defs>
        <linearGradient id="ballGrad" x1="30%" y1="30%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#ff4444" />
            <stop offset="60%" stop-color="#bd0000" />
            <stop offset="100%" stop-color="#540000" />
        </linearGradient>
    </defs>
</svg>
"""

# --- INJECTABLE SCRIPT TO PREVENT SCREEN SLEEP, DISMISS BUTTON HIGHLIGHTS & INJECT STABLE CSS CLASSES ---
WAKE_LOCK_AND_DOM_STYLER_SCRIPT = """
<script>
(function() {
    /* 1. Prevent Screen sleep */
    let wakeLock = null;
    async function requestWakeLock() {
        try {
            if ('wakeLock' in navigator) {
                wakeLock = await navigator.wakeLock.request('screen');
                console.log('Screen Wake Lock is active!');
            }
        } catch (err) {
            console.warn('Wake Lock request failed:', err.name, err.message);
        }
    }
    
    requestWakeLock();
    
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            requestWakeLock();
        }
    });
    
    /* 2. Remove sticky pressed state */
    const blurActiveElement = () => {
        setTimeout(() => {
            const activeEl = document.activeElement;
            if (activeEl && activeEl.tagName === 'BUTTON') {
                activeEl.blur();
            }
        }, 50);
    };
    document.addEventListener('mouseup', blurActiveElement);
    document.addEventListener('touchend', blurActiveElement);

    /* 3. Resilient Client-Side Styler that targets native buttons by their plain text label */
    const styleAppButtons = () => {
        const buttons = document.querySelectorAll('button');
        buttons.forEach(btn => {
            const text = btn.textContent.trim();
            if (text === '0' || text === '1' || text === '2' || text === '3') {
                btn.className = 'custom-score-btn';
            } else if (text === '4') {
                btn.className = 'custom-score-btn btn-four';
            } else if (text === '6') {
                btn.className = 'custom-score-btn btn-six';
            } else if (text === 'OUT') {
                btn.className = 'custom-score-btn btn-out';
            } else if (text === 'UNDO') {
                btn.className = 'custom-score-btn btn-undo';
            } else if (text === 'ADD EXTRAS') {
                btn.className = 'custom-extras-btn';
            } else if (text.includes('RESET')) {
                btn.className = 'custom-reset-btn';
            } else if (text.includes('THEME')) {
                btn.className = 'custom-theme-btn';
            } else if (text.includes('START 2ND')) {
                btn.className = 'custom-theme-btn';
            } else if (text.includes('CREATE MATCH')) {
                btn.className = 'custom-extras-btn';
            }
        });
    };

    styleAppButtons();
    const observer = new MutationObserver(styleAppButtons);
    observer.observe(document.body, { childList: true, subtree: true });
    setInterval(styleAppButtons, 300);
})();
</script>
"""

# --- INJECTABLE SCRIPT FOR LIVE STREAM BROADCAST AUTO REFRESH ---
AUTO_REFRESH_SCRIPT = """
<script>
(function() {
    setTimeout(function() {
        window.location.reload();
    }, 4000);
})();
</script>
"""

def render_main(match_id):
    # Inject wake-lock, auto-defocus & dynamic styling injection scripts
    render_html(WAKE_LOCK_AND_DOM_STYLER_SCRIPT)
    
    render_html("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700;800&family=Roboto+Condensed:wght@400;700&display=swap');
            header, footer, #MainMenu { display: none !important; }
            
            .stApp { 
                background: radial-gradient(circle at top, #141c2c 0%, #080a10 100%) !important; 
                min-height: 100vh; 
            }
            
            .block-container { 
                padding: 10px 8px 12px 8px !important; 
                max-width: 440px !important; 
                margin: 0 auto !important; 
            }

            /* Single Row Bar for Innings and Share button side-by-side */
            .top-row-bar {
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                gap: 8px !important;
                margin-bottom: 12px !important;
                width: 100% !important;
            }
            
            /* Innings badge adjusted to look like a premium beveled capsule on left side of row */
            .top-row-item-innings {
                flex: 1 !important;
                height: 38px !important;
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                background: linear-gradient(180deg, #1d283f 0%, #0b111c 100%) !important;
                color: #f3c64f !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                letter-spacing: 1.5px !important;
                text-transform: uppercase !important;
                border-radius: 10px !important;
                border: 2px solid #bda064 !important;
                box-shadow: inset 0 1.5px 3px rgba(255,255,255,0.15), inset 0 -2px 4px rgba(0,0,0,0.5), 0 4px 10px rgba(0,0,0,0.4) !important;
                text-shadow: 0 1px 2px rgba(0,0,0,0.6) !important;
            }
            
            /* Share scoring link redesigned to match Copy Overlay Link design exactly */
            a.top-row-item-share {
                flex: 1 !important;
                height: 38px !important;
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                background: rgba(195, 164, 105, 0.15) !important;
                color: #c3a469 !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 12px !important;
                font-weight: 700 !important;
                letter-spacing: 1.5px !important;
                text-transform: uppercase !important;
                border: 1.5px solid rgba(195, 164, 105, 0.4) !important;
                border-radius: 10px !important;
                text-decoration: none !important;
                transition: background 0.2s !important;
            }
            a.top-row-item-share:hover, a.top-row-item-share:active, a.top-row-item-share:focus {
                background: rgba(195, 164, 105, 0.25) !important;
                text-decoration: none !important;
                color: #c3a469 !important;
                outline: none !important;
            }

            /* PREMIUM OVERLAY STYLE TICKER BAR */
            .broadcast-ticker {
                display: flex; align-items: center; justify-content: space-between;
                background: linear-gradient(180deg, #24282c 0%, #0f1113 100%);
                border: 1.5px solid #3c4045; border-radius: 14px;
                padding: 6px 16px; margin-bottom: 12px;
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.1), 0 10px 20px rgba(0,0,0,0.6);
                position: relative; overflow: hidden; width: 100%;
                font-family: 'Roboto Condensed', sans-serif;
            }
            .ticker-gold-bar {
                position: absolute; left: 0; top: 0; bottom: 0; width: 5px;
                background: linear-gradient(180deg, #ffb700, #c38400);
                box-shadow: 0 0 6px rgba(255, 183, 0, 0.5);
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
            .batting-sec { flex: 1.4; min-width: 90px; }
            .ticker-lbl {
                color: #ffffff; font-size: 10px; font-weight: 700;
                letter-spacing: 1px; text-transform: uppercase; margin-bottom: 1px;
            }
            
            /* Two Row Team Name styling */
            .ticker-team-rows {
                display: flex; flex-direction: column; align-items: center; justify-content: center;
                text-align: center; font-family: 'Oswald', sans-serif; line-height: 1.1;
                text-transform: uppercase; width: 100%;
            }
            .team-row-1 {
                font-size: 16px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;
            }
            .team-row-2 {
                font-size: 14px; font-weight: 700; color: #f3c64f; letter-spacing: 0.5px;
                text-shadow: 0 0 4px rgba(243, 198, 79, 0.3);
            }

            .score-sec { flex: 1.5; }
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
            .max-sec { flex: 1.2; text-align: center; }
            .ticker-val-max {
                color: #ffd700; font-family: 'Oswald', sans-serif;
                font-size: 20px; font-weight: 700; line-height: 1.1;
            }

            [data-testid="stHorizontalBlock"] { gap: 6px !important; flex-wrap: nowrap !important; }
            [data-testid="stColumn"] { padding: 0 !important; min-width: 0 !important; }
            [data-testid="stVerticalBlockBorderWrapper"] { gap: 0 !important; }
            [data-testid="stVerticalBlock"] > * { margin-bottom: 0 !important; }
            div[data-testid="stVerticalBlock"] > div { gap: 0 !important; }
            [data-testid="element-container"] { margin: 0 !important; padding: 0 !important; }
            .stButton { margin: 0 !important; padding: 0 !important; }

            /* NATIVE TARGET STYLING FOR COMPILATION ELEMENTS */
            button.custom-score-btn {
                background: linear-gradient(135deg, rgba(20, 38, 77, 0.8) 0%, rgba(10, 20, 41, 0.95) 100%) !important;
                border: 2.5px solid #ffd700 !important;
                border-radius: 20px !important;
                box-shadow: inset 0 1.5px 3px rgba(255,255,255,0.15), inset 0 -3px 6px rgba(0,0,0,0.5), 0 5px 12px rgba(0,0,0,0.4), 0 0 12px rgba(255, 215, 0, 0.4) !important;
                color: #ffffff !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 32px !important;
                font-weight: 800 !important;
                height: 84px !important;
                width: 100% !important;
                text-shadow: 0 0 8px rgba(255, 215, 0, 0.4) !important;
                transition: transform 0.08s ease, box-shadow 0.08s ease, background 0.08s ease !important;
            }
            button.custom-score-btn:focus,
            button.custom-score-btn:active,
            button.custom-score-btn:focus-visible {
                outline: none !important;
                transform: none !important;
                background: linear-gradient(135deg, rgba(20, 38, 77, 0.8) 0%, rgba(10, 20, 41, 0.95) 100%) !important;
                border-color: #ffd700 !important;
                box-shadow: inset 0 1.5px 3px rgba(255,255,255,0.15), inset 0 -3px 6px rgba(0,0,0,0.5), 0 5px 12px rgba(0,0,0,0.4), 0 0 12px rgba(255, 215, 0, 0.4) !important;
                color: #ffffff !important;
            }
            
            button.custom-score-btn.btn-four {
                border-color: #f3c64f !important;
                color: #f3c64f !important;
                box-shadow: inset 0 1.5px 3px rgba(255,255,255,0.15), inset 0 -3px 6px rgba(0,0,0,0.5), 0 5px 12px rgba(0,0,0,0.4), 0 0 12px rgba(243, 198, 79, 0.4) !important;
                text-shadow: 0 0 8px rgba(243, 198, 79, 0.6) !important;
            }
            button.custom-score-btn.btn-four:focus, button.custom-score-btn.btn-four:active {
                border-color: #f3c64f !important;
                color: #f3c64f !important;
                background: linear-gradient(135deg, rgba(20, 38, 77, 0.8) 0%, rgba(10, 20, 41, 0.95) 100%) !important;
                box-shadow: inset 0 1.5px 3px rgba(255,255,255,0.15), inset 0 -3px 6px rgba(0,0,0,0.5), 0 5px 12px rgba(0,0,0,0.4), 0 0 12px rgba(243, 198, 79, 0.4) !important;
            }
            
            button.custom-score-btn.btn-six {
                border-color: #52d273 !important;
                color: #52d273 !important;
                box-shadow: inset 0 1.5px 3px rgba(255,255,255,0.15), inset 0 -3px 6px rgba(0,0,0,0.5), 0 5px 12px rgba(0,0,0,0.4), 0 0 12px rgba(82, 210, 115, 0.4) !important;
                text-shadow: 0 0 8px rgba(82, 210, 115, 0.6) !important;
            }
            button.custom-score-btn.btn-six:focus, button.custom-score-btn.btn-six:active {
                border-color: #52d273 !important;
                color: #52d273 !important;
                background: linear-gradient(135deg, rgba(20, 38, 77, 0.8) 0%, rgba(10, 20, 41, 0.95) 100%) !important;
                box-shadow: inset 0 1.5px 3px rgba(255,255,255,0.15), inset 0 -3px 6px rgba(0,0,0,0.5), 0 5px 12px rgba(0,0,0,0.4), 0 0 12px rgba(82, 210, 115, 0.4) !important;
            }
            
            button.custom-score-btn.btn-out {
                border-color: #ec4849 !important;
                color: #ec4849 !important;
                font-size: 24px !important;
                box-shadow: inset 0 1.5px 3px rgba(255,255,255,0.15), inset 0 -3px 6px rgba(0,0,0,0.5), 0 5px 12px rgba(0,0,0,0.4), 0 0 12px rgba(236, 72, 73, 0.4) !important;
                text-shadow: 0 0 8px rgba(236, 72, 73, 0.6) !important;
            }
            button.custom-score-btn.btn-out:focus, button.custom-score-btn.btn-out:active {
                border-color: #ec4849 !important;
                color: #ec4849 !important;
                background: linear-gradient(135deg, rgba(20, 38, 77, 0.8) 0%, rgba(10, 20, 41, 0.95) 100%) !important;
                box-shadow: inset 0 1.5px 3px rgba(255,255,255,0.15), inset 0 -3px 6px rgba(0,0,0,0.5), 0 5px 12px rgba(0,0,0,0.4), 0 0 12px rgba(236, 72, 73, 0.4) !important;
            }
            
            button.custom-score-btn.btn-undo {
                border-color: #4da6ff !important;
                color: #4da6ff !important;
                font-size: 20px !important;
                box-shadow: inset 0 1.5px 3px rgba(255,255,255,0.15), inset 0 -3px 6px rgba(0,0,0,0.5), 0 5px 12px rgba(0,0,0,0.4), 0 0 12px rgba(77, 166, 255, 0.4) !important;
                text-shadow: 0 0 8px rgba(77, 166, 255, 0.6) !important;
            }
            button.custom-score-btn.btn-undo:focus, button.custom-score-btn.btn-undo:active {
                border-color: #4da6ff !important;
                color: #4da6ff !important;
                background: linear-gradient(135deg, rgba(20, 38, 77, 0.8) 0%, rgba(10, 20, 41, 0.95) 100%) !important;
                box-shadow: inset 0 1.5px 3px rgba(255,255,255,0.15), inset 0 -3px 6px rgba(0,0,0,0.5), 0 5px 12px rgba(0,0,0,0.4), 0 0 12px rgba(77, 166, 255, 0.4) !important;
            }

            button.custom-extras-btn {
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
            button.custom-extras-btn:active {
                transform: scale(0.97) !important;
            }

            .extras-modal {
                background: #11203b !important;
                border: 2px solid #bda064 !important;
                border-radius: 20px !important;
                overflow: hidden !important;
                box-shadow: inset 0 2px 3px rgba(255,255,255,0.1), 0 12px 28px rgba(0,0,0,0.6) !important;
                margin: 12px 0 !important;
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

            .extras-modal button {
                background: linear-gradient(180deg, #1b2e50 0%, #0d1729 100%) !important;
                border: 2.5px solid #ffd700 !important;
                border-radius: 14px !important;
                color: #ffffff !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 16px !important;
                font-weight: 700 !important;
                height: 52px !important;
                width: 100% !important;
                text-shadow: 0 1px 2px rgba(0,0,0,0.5) !important;
            }

            button.custom-reset-btn {
                background: linear-gradient(180deg, #321010 0%, #190808 100%) !important;
                border: 2px solid #ff5252 !important;
                border-radius: 16px !important;
                box-shadow: inset 0 1.5px 2px rgba(255,255,255,0.1), inset 0 -3px 6px rgba(0,0,0,0.5), 0 4px 10px rgba(0,0,0,0.4) !important;
                color: #ff5252 !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                height: 44px !important;
                letter-spacing: 1px;
                text-shadow: 0 1px 2px rgba(0,0,0,0.5) !important;
                text-transform: uppercase !important;
                width: 100% !important;
            }
            button.custom-theme-btn {
                background: linear-gradient(180deg, #1b2e50 0%, #0d1729 100%) !important;
                border: 2px solid #bda064 !important;
                border-radius: 16px !important;
                box-shadow: inset 0 1.5px 2px rgba(255,255,255,0.1), inset 0 -3px 6px rgba(0,0,0,0.5), 0 4px 10px rgba(0,0,0,0.4) !important;
                color: #f3c64f !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                height: 44px !important;
                letter-spacing: 1px;
                text-shadow: 0 1px 2px rgba(0,0,0,0.5) !important;
                text-transform: uppercase !important;
                width: 100% !important;
            }

            .target-bar {
                background: rgba(195, 164, 105, 0.08); border: 1.5px solid rgba(195, 164, 105, 0.3);
                border-radius: 10px; padding: 6px 12px; text-align: center; margin-bottom: 10px;
                font-family: 'Roboto Condensed', sans-serif; color: #e5c185; font-size: 13px; font-weight: 700; letter-spacing: 0.5px;
            }
            
            .credit { 
                text-align: center; 
                margin-top: 15px; 
                padding-top: 10px; 
                border-top: 1.5px solid rgba(255,255,255,0.05); 
            }
            .credit span { 
                font-family: 'Roboto Condensed', sans-serif; 
                font-size: 9px; 
                letter-spacing: 1.5px; 
                color: rgba(255,255,255,0.2); 
                text-transform: uppercase; 
            }
            .glowing-name { 
                font-family: 'Oswald', sans-serif !important;
                font-size: 16px !important;
                color: #ffd700 !important; 
                font-weight: 800 !important; 
                text-shadow: 0 0 10px rgba(255, 215, 0, 0.9), 0 0 20px rgba(255, 215, 0, 0.4) !important;
                display: inline-block;
                margin-top: 2px;
            }
            .credit-link {
                font-family: 'Roboto Condensed', sans-serif;
                font-size: 11px;
                color: rgba(195, 164, 105, 0.8) !important;
                letter-spacing: 1px;
                text-decoration: none !important;
                border-bottom: none !important;
                transition: color 0.2s, text-shadow 0.2s;
                display: inline-block;
                margin-top: 5px;
            }
            .credit-link:hover, .credit-link:active, .credit-link:focus {
                color: #ffd700 !important;
                text-shadow: 0 0 6px rgba(255, 215, 0, 0.6);
                text-decoration: none !important;
                border-bottom: none !important;
            }
        </style>
    """)

    if st.session_state.get("light_mode"):
        render_html("""
            <style>
                .stApp { background: radial-gradient(circle at top, #f0f4fa 0%, #d4dfec 100%) !important; }
                .broadcast-ticker { background: linear-gradient(180deg, #ffffff 0%, #eef3fb 100%) !important; border-color: rgba(0,0,0,0.15) !important; box-shadow: 0 6px 15px rgba(0,0,0,0.08); }
                .ticker-val-score { color: #141c2c !important; }
                .ticker-lbl { color: #555555 !important; }
                .team-row-1 { color: #141c2c !important; }
                button.custom-score-btn {
                    background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(230,238,248,0.95) 100%) !important;
                    color: #141c2c !important; border-color: #ffd700 !important;
                    box-shadow: inset 0 1.5px 3px rgba(255,255,255,1), 0 4px 8px rgba(0,0,0,0.08) !important;
                }
                button.custom-extras-btn {
                    background: linear-gradient(180deg, #ffffff 0%, #eef3fb 100%) !important;
                    color: #141c2c !important; border-color: #bda064 !important;
                }
                .extras-modal { background: #f0f4fa !important; border-color: #9b814a !important; }
                .extras-modal button {
                    background: linear-gradient(180deg, #ffffff 0%, #eef3fb 100%) !important;
                    color: #141c2c !important; border-color: #9b814a !important;
                }
                .target-bar { background: rgba(0,0,0,0.03) !important; color: #8c581a !important; border-color: rgba(140,88,26,0.2) !important; }
                .credit span { color: rgba(0,0,0,0.4) !important; }
                .credit-link { color: #8c581a !important; }
            </style>
        """)

    # --- DEFINE OVERLAY LINK ---
    base_url = st.context.url if hasattr(st, 'context') and hasattr(st.context, 'url') else "http://localhost:8501"
    if "?" in base_url:
        base_url = base_url.split("?")[0]
    overlay_url = base_url + "?mode=overlay&match=" + (match_id or "NONE")

    # Setup Setup/Create Match state
    if not match_id:
        st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
        render_html(SVG_LOGO_MARKUP)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div style='color:white;text-align:center;font-family:Oswald;font-size:30px;margin-top:10px;margin-bottom:4px;'>🏏 Smart Cricket Scorer</div>", unsafe_allow_html=True)
        st.markdown("<div style='color:rgba(255,255,255,0.4);text-align:center;font-family:Roboto Condensed;font-size:11px;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:24px;'>MATCH SETUP</div>", unsafe_allow_html=True)

        # Config Inputs with Custom Gold Design Accents
        st.markdown("<style>div[data-baseweb='input'] { border-radius: 12px; }</style>", unsafe_allow_html=True)
        team1_in = st.text_input("First Team Name", value="LIONS")
        team2_in = st.text_input("Second Team Name", value="WARRIORS")
        overs_in = st.number_input("Match Overs Limit", min_value=1, max_value=50, value=5)
        
        batting_options = [1, 2]
        batting_first_in = st.radio(
            "Who is batting first?",
            options=batting_options,
            format_func=lambda x: team1_in if x == 1 else team2_in
        )

        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        if st.button("CREATE MATCH"):
            new_id = generate_match_id()
            create_match(new_id, overs_in, team1_in, team2_in, batting_first_in)
            st.query_params["match"] = new_id
            st.rerun()
            
        # Add simple layout credit at bottom of setup
        st.markdown("""
            <div class="credit">
                <span>Powered by</span><br/>
                <div class="glowing-name">SMART SCORE 360</div>
            </div>
        """, unsafe_allow_html=True)
        return

    # --- SCORING ACTIVE MATCH SCREEN ---
    d = get_match(match_id)
    if not d:
        st.error("Match ID not found!")
        if st.button("Setup New Match"):
            st.query_params.clear()
            st.rerun()
        return

    # Derive Teams Statuses
    if d["batting_first"] == 1:
        team_batting_1st = d["team1_name"]
        team_batting_2nd = d["team2_name"]
    else:
        team_batting_1st = d["team2_name"]
        team_batting_2nd = d["team1_name"]

    if d["innings"] == 1:
        current_batting = team_batting_1st
        current_bowling = team_batting_2nd
    else:
        current_batting = team_batting_2nd
        current_bowling = team_batting_1st

    # Top Navigation Row
    st.markdown(f"""
        <div class="top-row-bar">
            <div class="top-row-item-innings">Innings {d['innings']}</div>
            <a href="{overlay_url}" target="_blank" class="top-row-item-share">Overlay HUD Link</a>
        </div>
    """, unsafe_allow_html=True)

    # Broadcasters Style Status Score Board Ticker
    wickets = get_wickets(d["history"])
    ticker_html = f"""
    <div class="broadcast-ticker">
        <div class="ticker-gold-bar"></div>
        <div class="ticker-section batting-sec">
            <div class="ticker-team-rows">
                <div class="team-row-1">{team_abbrev(current_batting)}</div>
                <div class="team-row-2">BATTING</div>
            </div>
        </div>
        <div class="ticker-divider"></div>
        <div class="ticker-section score-sec">
            <div class="ticker-val-score">{d['runs']}/{wickets}</div>
        </div>
        <div class="ticker-divider"></div>
        <div class="ticker-section overs-sec">
            <div class="overs-arch-wrap">
                <div class="overs-arch"></div>
                <div class="ticker-lbl">OVERS</div>
                <div class="ticker-val-overs">{d['balls'] // 6}.{d['balls'] % 6}</div>
            </div>
        </div>
        <div class="ticker-divider"></div>
        <div class="ticker-section max-sec">
            <div class="ticker-lbl">MAX OV</div>
            <div class="ticker-val-max">{d['match_overs']}</div>
        </div>
    </div>
    """
    st.markdown(ticker_html, unsafe_allow_html=True)

    # Secondary target layout context status messaging
    if d["innings"] == 2:
        target_score = d["innings1_runs"] + 1
        runs_needed = target_score - d["runs"]
        total_balls_limit = d["match_overs"] * 6
        balls_remaining = total_balls_limit - d["balls"]

        if runs_needed <= 0:
            status_text = f"🏆 {current_batting} won by {10 - wickets} wickets!"
        elif balls_remaining <= 0 or wickets >= 10:
            status_text = f"🏆 {current_bowling} won by {runs_needed - 1} runs!"
        else:
            status_text = f"Target: {target_score} | Need {runs_needed} runs off {balls_remaining} balls"
        st.markdown(f'<div class="target-bar">{status_text}</div>', unsafe_allow_html=True)

    # Scorer controls container layout grid (Row 1: 0, 1, 2, 3)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("0", key="b0"):
            update_score(match_id, 0, 1)
            st.rerun()
    with col2:
        if st.button("1", key="b1"):
            update_score(match_id, 1, 1)
            st.rerun()
    with col3:
        if st.button("2", key="b2"):
            update_score(match_id, 2, 1)
            st.rerun()
    with col4:
        if st.button("3", key="b3"):
            update_score(match_id, 3, 1)
            st.rerun()

    # Scorer controls container layout grid (Row 2: 4, 6, OUT, UNDO)
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        if st.button("4", key="b4"):
            update_score(match_id, 4, 1)
            st.rerun()
    with col6:
        if st.button("6", key="b6"):
            update_score(match_id, 6, 1)
            st.rerun()
    with col7:
        if st.button("OUT", key="bout"):
            update_score(match_id, 0, 1, is_wicket=True)
            st.rerun()
    with col8:
        if st.button("UNDO", key="bundo"):
            update_score(match_id, 0, 0, is_undo=True)
            st.rerun()

    # --- EXTRAS COLLAPSIBLE DRAWER POPUP MODAL ---
    if "show_extras" not in st.session_state:
        st.session_state.show_extras = False

    if st.button("ADD EXTRAS"):
        st.session_state.show_extras = not st.session_state.show_extras
        st.rerun()

    if st.session_state.show_extras:
        st.markdown("""
            <div class="extras-modal">
                <div class="extras-header">Extras Dispatch Board</div>
                <div class="extras-body">
        """, unsafe_allow_html=True)
        
        ex_col1, ex_col2 = st.columns(2)
        with ex_col1:
            if st.button("WIDE + 1 (1 Run)", key="wd1"):
                update_score(match_id, 1, 0)
                st.session_state.show_extras = False
                st.rerun()
            if st.button("WIDE + 4 (5 Runs)", key="wd4"):
                update_score(match_id, 5, 0)
                st.session_state.show_extras = False
                st.rerun()
        with ex_col2:
            if st.button("NO BALL + 1 (1 Run)", key="nb1"):
                update_score(match_id, 1, 0)
                st.session_state.show_extras = False
                st.rerun()
            if st.button("NO BALL + 4 (5 Runs)", key="nb4"):
                update_score(match_id, 5, 0)
                st.session_state.show_extras = False
                st.rerun()
        
        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        if st.button("CLOSE DRAWER", key="close_ex"):
            st.session_state.show_extras = False
            st.rerun()
            
        st.markdown("</div></div>", unsafe_allow_html=True)

    # --- ADVANCED MATCH ACTION CONTROLS UTILITY BOX ---
    st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
    ut_col1, ut_col2 = st.columns(2)
    with ut_col1:
        if d["innings"] == 1:
            if st.button("START 2ND INNINGS"):
                start_second_innings(match_id, d["runs"])
                st.rerun()
        else:
            if st.button("RESET MATCH BOARD"):
                reset_match(match_id)
                st.rerun()
    with ut_col2:
        if st.button("TOGGLE THEME MODE"):
            st.session_state.light_mode = not st.session_state.get("light_mode", False)
            st.rerun()

    # Glowing Designer branding signature footer
    st.markdown("""
        <div class="credit">
            <span>Powered by</span><br/>
            <div class="glowing-name">SMART SCORE 360</div>
        </div>
    """, unsafe_allow_html=True)


def render_overlay(match_id):
    # OBS / Live Broadcast Graphics Frame Overlay Mode
    render_html(AUTO_REFRESH_SCRIPT)
    render_html("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700;800&family=Roboto+Condensed:wght@400;700&display=swap');
            header, footer, #MainMenu { display: none !important; }
            .stApp { background: transparent !important; }
            .block-container { max-width: 100% !important; padding: 24px !important; }
            
            .overlay-hud {
                background: linear-gradient(180deg, #162238 0%, #090e18 100%);
                border: 3px solid #ffb700;
                border-radius: 16px;
                padding: 16px 32px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 10px 40px rgba(0,0,0,0.9), inset 0 2px 6px rgba(255,255,255,0.25);
                font-family: 'Oswald', sans-serif;
                color: #ffffff;
                max-width: 650px;
                margin: 40px auto;
                text-transform: uppercase;
                border-left: 8px solid #ffb700;
            }
            .hud-team {
                font-size: 28px;
                font-weight: 800;
                color: #ffd700;
                letter-spacing: 1px;
            }
            .hud-score {
                font-size: 42px;
                font-weight: 800;
                color: #ffffff;
                text-shadow: 0 0 12px rgba(255, 215, 0, 0.6);
                line-height: 1;
            }
            .hud-overs {
                font-size: 20px;
                color: #52d273;
                font-weight: 700;
                margin-top: 2px;
            }
            .hud-target {
                font-size: 14px;
                color: #f3c64f;
                font-family: 'Roboto Condensed', sans-serif;
                margin-top: 6px;
                text-align: center;
                letter-spacing: 0.5px;
            }
            .hud-badge-inn {
                font-size: 16px;
                font-weight: 700;
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                padding: 4px 12px;
                border-radius: 8px;
            }
        </style>
    """)

    d = get_match(match_id)
    if not d:
        st.markdown("<div style='color:white;text-align:center;'>Waiting for live match data...</div>", unsafe_allow_html=True)
        return

    # Derive Teams Statuses
    if d["batting_first"] == 1:
        team_batting_1st = d["team1_name"]
        team_batting_2nd = d["team2_name"]
    else:
        team_batting_1st = d["team2_name"]
        team_batting_2nd = d["team1_name"]

    if d["innings"] == 1:
        current_batting = team_batting_1st
        current_bowling = team_batting_2nd
    else:
        current_batting = team_batting_2nd
        current_bowling = team_batting_1st

    wickets = get_wickets(d["history"])
    
    target_hud_text = ""
    if d["innings"] == 2:
        target_score = d["innings1_runs"] + 1
        runs_needed = target_score - d["runs"]
        total_balls_limit = d["match_overs"] * 6
        balls_remaining = total_balls_limit - d["balls"]

        if runs_needed <= 0:
            target_hud_text = f"{current_batting} Won!"
        elif balls_remaining <= 0 or wickets >= 10:
            target_hud_text = f"{current_bowling} Won!"
        else:
            target_hud_text = f"Need {runs_needed} Runs from {balls_remaining} Balls"

    st.markdown(f"""
        <div class="overlay-hud">
            <div class="hud-team">{team_abbrev(current_batting)}</div>
            <div style="text-align: center; flex: 1; margin: 0 20px;">
                <div class="hud-score">{d['runs']}/{wickets}</div>
                <div class="hud-overs">{d['balls'] // 6}.{d['balls'] % 6} Overs</div>
                {f'<div class="hud-target">{target_hud_text}</div>' if target_hud_text else ''}
            </div>
            <div class="hud-badge-inn">INN {d['innings']}</div>
        </div>
    """, unsafe_allow_html=True)


def main():
    mode = st.query_params.get("mode", "main")
    match_id = st.query_params.get("match", None)

    if mode == "overlay" and match_id:
        render_overlay(match_id)
    else:
        render_main(match_id)


if __name__ == "__main__":
    main()
