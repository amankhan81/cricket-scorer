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

    /* 3. Client-Side Styler that maps Streamlit buttons to Screenshot-accurate visual styles */
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
            } else if (text.includes('UNDO')) {
                btn.className = 'custom-score-btn btn-undo';
            } else if (text === 'ADD EXTRAS') {
                btn.className = 'custom-extras-btn';
            } else if (text.includes('RESET')) {
                btn.className = 'custom-reset-btn';
            } else if (text.includes('MODE')) {
                btn.className = 'custom-theme-btn';
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

WAKE_LOCK_AND_ANTI_STICK_SCRIPT = WAKE_LOCK_AND_DOM_STYLER_SCRIPT

def render_main(match_id):
    # Inject wake-lock, auto-defocus & dynamic styling injection scripts
    render_html(WAKE_LOCK_AND_DOM_STYLER_SCRIPT)
    
    render_html("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700;800&family=Roboto+Condensed:wght@400;700&display=swap');
            header, footer, #MainMenu { display: none !important; }
            
            .stApp { 
                background: radial-gradient(circle at top, #0f1c30 0%, #080d1a 100%) !important; 
                min-height: 100vh; 
            }
            
            .block-container { 
                padding: 10px 8px 12px 8px !important; 
                max-width: 440px !important; 
                margin: 0 auto !important; 
            }

            /* Header Badges Layout matching the Screenshot exactly */
            .header-badges {
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                gap: 8px !important;
                margin-top: 6px !important;
                margin-bottom: 16px !important;
                width: 100% !important;
            }
            .innings-capsule {
                background: linear-gradient(180deg, #1d283f 0%, #0b111c 100%) !important;
                color: #bda064 !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 11px !important;
                font-weight: 700 !important;
                letter-spacing: 2px !important;
                text-transform: uppercase !important;
                border-radius: 20px !important;
                border: 2px solid #bda064 !important;
                padding: 5px 16px !important;
                box-shadow: inset 0 1px 2px rgba(255,255,255,0.1), 0 4px 10px rgba(0,0,0,0.5) !important;
                text-shadow: 0 1px 2px rgba(0,0,0,0.6) !important;
                display: inline-block !important;
                text-align: center !important;
            }
            .share-capsule {
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                gap: 6px !important;
                background: #082d1c !important;
                color: #2ecc71 !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 11px !important;
                font-weight: 700 !important;
                letter-spacing: 1.5px !important;
                text-transform: uppercase !important;
                border-radius: 20px !important;
                border: 2px solid #14613c !important;
                padding: 5px 16px !important;
                text-decoration: none !important;
                box-shadow: inset 0 1px 2px rgba(255,255,255,0.1), 0 4px 10px rgba(0,0,0,0.5) !important;
                transition: background 0.2s !important;
            }
            .share-capsule:hover {
                background: #0c3d26 !important;
                color: #2ecc71 !important;
            }

            /* Score Card Panel matching Score and Overs in screenshot */
            .score-card-panel {
                display: flex !important;
                align-items: center !important;
                background: linear-gradient(180deg, #131e33 0%, #0a1121 100%) !important;
                border: 1.5px solid rgba(255, 255, 255, 0.08) !important;
                border-radius: 18px !important;
                padding: 14px 20px !important;
                margin-bottom: 20px !important;
                box-shadow: inset 0 1px 2px rgba(255,255,255,0.1), 0 8px 20px rgba(0,0,0,0.6) !important;
                width: 100% !important;
            }
            .score-card-col {
                flex: 1 !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
            }
            .score-card-lbl {
                color: #7d8ea6 !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 11px !important;
                font-weight: 700 !important;
                letter-spacing: 2px !important;
                text-transform: uppercase !important;
                margin-bottom: 4px !important;
            }
            .score-card-val {
                color: #ffffff !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 46px !important;
                font-weight: 700 !important;
                line-height: 1 !important;
            }
            .score-card-divider {
                width: 1px !important;
                background: rgba(255, 255, 255, 0.1) !important;
                height: 46px !important;
            }

            [data-testid="stHorizontalBlock"] { gap: 10px !important; flex-wrap: nowrap !important; }
            [data-testid="stColumn"] { padding: 0 !important; min-width: 0 !important; }
            [data-testid="stVerticalBlockBorderWrapper"] { gap: 0 !important; }
            [data-testid="stVerticalBlock"] > * { margin-bottom: 0 !important; }
            div[data-testid="stVerticalBlock"] > div { gap: 0 !important; }
            [data-testid="element-container"] { margin: 0 !important; padding: 0 !important; }
            .stButton { margin: 0 !important; padding: 0 !important; }

            button.custom-score-btn {
                background: radial-gradient(circle at center, #24395d 0%, #101a2f 100%) !important;
                border: 3px solid #bca068 !important; /* Bronze-gold frame */
                border-radius: 28px !important; /* Smooth squircle shape matching image */
                box-shadow: 
                    inset 0 0 0 3px #101a2f, /* Inner dark gap */
                    inset 0 0 0 5px #bca068, /* Gold inner bevel highlight */
                    inset 0 4px 6px rgba(255, 255, 255, 0.25), /* Gloss highlight */
                    inset 0 -6px 10px rgba(0, 0, 0, 0.8), /* Deep 3D bottom shadow */
                    0 6px 12px rgba(0, 0, 0, 0.6) !important; /* Soft dropdown shadow */
                color: #ffffff !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 34px !important;
                font-weight: 700 !important;
                height: 84px !important;
                width: 100% !important;
                text-shadow: 0 2px 4px rgba(0,0,0,0.8) !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                transition: transform 0.05s ease, box-shadow 0.05s ease !important;
            }
            
            button.custom-score-btn:focus,
            button.custom-score-btn:active,
            button.custom-score-btn:focus-visible {
                outline: none !important;
                transform: scale(0.95) !important;
                background: radial-gradient(circle at center, #24395d 0%, #101a2f 100%) !important;
                border-color: #bca068 !important;
                box-shadow: 
                    inset 0 0 0 3px #101a2f,
                    inset 0 0 0 5px #bca068,
                    inset 0 2px 4px rgba(0,0,0,0.8),
                    0 2px 4px rgba(0,0,0,0.4) !important;
            }
            
            /* Custom Colored Buttons to Match the Image */
            /* Button 4: Golden text */
            button.custom-score-btn.btn-four {
                color: #eec54f !important;
                text-shadow: 0 2px 4px rgba(0,0,0,0.9), 0 0 8px rgba(238, 197, 79, 0.3) !important;
            }
            /* Button 6: Green text */
            button.custom-score-btn.btn-six {
                color: #4ade80 !important;
                text-shadow: 0 2px 4px rgba(0,0,0,0.9), 0 0 8px rgba(74, 222, 128, 0.3) !important;
            }
            /* Button OUT: Red text */
            button.custom-score-btn.btn-out {
                color: #ef4444 !important;
                font-size: 24px !important;
                text-shadow: 0 2px 4px rgba(0,0,0,0.9), 0 0 8px rgba(239, 68, 68, 0.3) !important;
            }
            /* Button UNDO: Blue label with scaled down size for double-rim alignment */
            button.custom-score-btn.btn-undo {
                color: #3fa9f5 !important;
                font-size: 15px !important;
                font-weight: 700 !important;
                letter-spacing: 0.5px !important;
                text-shadow: 0 1px 3px rgba(0,0,0,0.9) !important;
            }

            /* Skeuomorphic ADD EXTRAS Button */
            button.custom-extras-btn {
                background: linear-gradient(180deg, #24395d 0%, #101a2f 100%) !important;
                border: 3px solid #bca068 !important;
                border-radius: 30px !important;
                box-shadow: 
                    inset 0 0 0 2px #101a2f,
                    inset 0 0 0 4px #bca068,
                    inset 0 3px 6px rgba(255,255,255,0.25),
                    inset 0 -5px 10px rgba(0,0,0,0.8),
                    0 6px 12px rgba(0,0,0,0.6) !important;
                color: #ffffff !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 20px !important;
                font-weight: 700 !important;
                letter-spacing: 1.5px !important;
                height: 58px !important;
                width: 100% !important;
                text-shadow: 0 2px 4px rgba(0,0,0,0.8) !important;
                text-transform: uppercase !important;
                margin: 12px 0 !important;
                transition: transform 0.05s ease !important;
            }
            button.custom-extras-btn:active {
                transform: scale(0.97) !important;
            }

            /* Extras Popup customization */
            .extras-modal {
                background: #111d33 !important;
                border: 2px solid #bca068 !important;
                border-radius: 20px !important;
                overflow: hidden !important;
                box-shadow: inset 0 2px 3px rgba(255,255,255,0.1), 0 12px 28px rgba(0,0,0,0.6) !important;
                margin: 6px 0 !important;
            }
            .extras-header {
                background: linear-gradient(180deg, #bca068 0%, #8c7343 100%) !important;
                color: #ffffff !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 18px !important;
                font-weight: 700 !important;
                text-align: center !important;
                padding: 10px 0 !important;
                letter-spacing: 2px !important;
                text-shadow: 0 1.5px 3px rgba(0,0,0,0.6) !important;
                text-transform: uppercase !important;
                border-bottom: 2px solid #bca068 !important;
            }
            .extras-body {
                padding: 16px 12px !important;
            }

            /* Extra popup button styles */
            div[data-testid="element-container"]:has(.extra-wide-btn) + div[data-testid="element-container"] button {
                background: linear-gradient(180deg, #1b2e50 0%, #0d1729 100%) !important;
                border: 2px solid #bca068 !important;
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
            
            div[data-testid="element-container"]:has(.extra-no-btn) + div[data-testid="element-container"] button {
                background: linear-gradient(180deg, #1b2e50 0%, #0d1729 100%) !important;
                border: 1.5px solid #bca068 !important;
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

            div[data-testid="element-container"]:has(.extra-cancel-btn) + div[data-testid="element-container"] button {
                background: transparent !important;
                border: 2px solid #bca068 !important;
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

            /* Utility reset/theme button styles */
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
                letter-spacing: 1px !important;
                text-shadow: 0 1px 2px rgba(0,0,0,0.5) !important;
                text-transform: uppercase !important;
                width: 100% !important;
            }
            button.custom-theme-btn {
                background: linear-gradient(180deg, #1b2e50 0%, #0d1729 100%) !important;
                border: 2px solid #bca068 !important;
                border-radius: 16px !important;
                box-shadow: inset 0 1.5px 2px rgba(255,255,255,0.1), inset 0 -3px 6px rgba(0,0,0,0.5), 0 4px 10px rgba(0,0,0,0.4) !important;
                color: #eec54f !important;
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
                background: rgba(188, 160, 104, 0.08); border: 1.5px solid rgba(188, 160, 104, 0.3);
                border-radius: 10px; padding: 6px 12px; text-align: center; margin-bottom: 10px;
                font-family: 'Roboto Condensed', sans-serif; color: #e5c185; font-size: 13px; font-weight: 700; letter-spacing: 0.5px;
            }
            
            /* Credits and Glowing Signature */
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
                color: rgba(188, 160, 104, 0.8) !important;
                letter-spacing: 1px;
                text-decoration: none !important;
                border-bottom: none !important;
                transition: color 0.2s, text-shadow 0.2s;
                display: inline-block;
                margin-top: 5px;
            }
            .credit-link:hover {
                color: #ffd700 !important;
                text-shadow: 0 0 6px rgba(255, 215, 0, 0.6);
            }
        </style>
    """)

    if st.session_state.get("light_mode"):
        render_html("""
            <style>
                .stApp { background: radial-gradient(circle at top, #f0f4fa 0%, #d4dfec 100%) !important; }
                .score-card-panel { background: linear-gradient(180deg, #ffffff 0%, #eef3fb 100%) !important; border-color: rgba(0,0,0,0.15) !important; box-shadow: 0 6px 15px rgba(0,0,0,0.08) !important; }
                .score-card-val { color: #101c31 !important; }
                .score-card-lbl { color: #555555 !important; }
                button.custom-score-btn {
                    background: radial-gradient(circle at center, rgba(255,255,255,0.9) 0%, rgba(230,238,248,0.95) 100%) !important;
                    color: #101c31 !important; border-color: #bca068 !important;
                    box-shadow: inset 0 0 0 2px #ffffff, inset 0 0 0 4px #bca068, 0 4px 8px rgba(0,0,0,0.08) !important;
                }
                button.custom-extras-btn {
                    background: linear-gradient(180deg, #ffffff 0%, #eef3fb 100%) !important;
                    color: #101c31 !important; border-color: #bca068 !important;
                    box-shadow: inset 0 0 0 1px #ffffff, inset 0 0 0 3px #bca068, 0 4px 8px rgba(0,0,0,0.08) !important;
                }
                .extras-modal { background: #f0f4fa !important; border-color: #8c7343 !important; }
                div[data-testid="element-container"]:has(.extra-wide-btn) + div[data-testid="element-container"] button,
                div[data-testid="element-container"]:has(.extra-no-btn) + div[data-testid="element-container"] button {
                    background: linear-gradient(180deg, #ffffff 0%, #eef3fb 100%) !important;
                    color: #101c31 !important; border-color: #8c7343 !important;
                }
                div[data-testid="element-container"]:has(.extra-cancel-btn) + div[data-testid="element-container"] button { background: rgba(0,0,0,0.02) !important; border-color: #bca068 !important; }
                .target-bar { background: rgba(0,0,0,0.03) !important; color: #8c581a !important; border-color: rgba(140,88,26,0.2) !important; }
                .credit span { color: rgba(0,0,0,0.4) !important; }
                .credit-link { color: #8c581a !important; }
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
        
        render_html("""
            <div class="credit">
                <span>Created by <strong class="glowing-name">Amanullah Khan</strong></span><br/>
                <a href="https://www.smartstudygrid.com/" target="_blank" class="credit-link">www.smartstudygrid.com</a>
            </div>
        """)
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
    wickets       = get_wickets(d.get("history"))
    max_overs_val = str(d['match_overs'])

    team1_name    = d.get("team1_name") or "Team 1"
    team2_name    = d.get("team2_name") or "Team 2"
    batting_first = int(d.get("batting_first") or 1)
    
    team_inn1 = team1_name if batting_first == 1 else team2_name
    team_inn2 = team2_name if batting_first == 1 else team1_name
    
    if innings == 1:
        batting_team = team_inn1
        bowling_team = team_inn2
    else:
        batting_team = team_inn2
        bowling_team = team_inn1

    # Automate Match Over if target is achieved in 2nd innings
    target_achieved = (innings == 2 and current_runs > innings1_runs)
    innings2_completed = (innings == 2 and (current_balls >= max_balls or wickets >= 10))
    match_over = target_achieved or innings2_completed

    # Handle First Innings boundaries
    if innings == 1 and (current_balls >= max_balls or wickets >= 10):
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
        
        render_html("""
            <div class="credit">
                <span>Created by <strong class="glowing-name">Amanullah Khan</strong></span><br/>
                <a href="https://www.smartstudygrid.com/" target="_blank" class="credit-link">www.smartstudygrid.com</a>
            </div>
        """)
        return

    # Parse batting team words
    words = batting_team.strip().split()
    row1 = ""
    row2 = ""
    if len(words) >= 2:
        row1 = words[0].upper()
        row2 = words[1].upper()
    elif len(words) == 1:
        row1 = words[0].upper()
        row2 = ""
    else:
        row1 = "TEAM"
        row2 = "1"

    # Setup formatted overs parenthetical value
    try:
        formatted_max = f"({int(max_overs_val):02d})"
    except:
        formatted_max = f"({max_overs_val})"

    if match_over:
        if current_runs > innings1_runs:
            winner_text = batting_team.upper()
            wickets_left = 10 - wickets
            margin = f"{wickets_left} WICKET" + ("S" if wickets_left > 1 else "")
            outcome_banner = f"🏆 {winner_text} WON BY {margin}"
        elif current_runs < innings1_runs:
            winner_text = bowling_team.upper()
            runs_diff = innings1_runs - current_runs
            margin = f"{runs_diff} RUN" + ("S" if runs_diff > 1 else "")
            outcome_banner = f"🏆 {winner_text} WON BY {margin}"
        else:
            outcome_banner = "🏆 MATCH TIED 🤝"

        render_html(f"""
            <div class="score-card-panel" style="justify-content: center; padding: 24px 10px;">
                <div style="font-family:'Oswald', sans-serif; font-size: 20px; font-weight: 800; color: #ffd700; text-align: center; text-transform: uppercase; letter-spacing: 0.5px;">
                    {outcome_banner}
                </div>
            </div>
        """)
        st.markdown('<div class="add-extras-btn">', unsafe_allow_html=True)
        if st.button("NEW MATCH", use_container_width=True):
            st.query_params.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    else:
        # Redesigned Innings and Share capsules centered sequentially matching screenshot
        innings_text = "1ST INNINGS" if innings == 1 else "2ND INNINGS"
        whatsapp_share_url = "https://easyscoring.streamlit.app/?match=" + match_id
        whatsapp_link = "https://wa.me/?text=" + whatsapp_share_url
        
        render_html(f"""
            <div class="header-badges">
                <div class="innings-capsule">
                    {batting_team.upper()} — {innings_text}
                </div>
                <a class="share-capsule" href="{whatsapp_link}" target="_blank">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" style="display:inline; vertical-align:middle; margin-right:4px;"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>
                    SHARE SCORING
                </a>
            </div>
        """)
        
        # score-card-panel layout matching the Score/Overs widget exactly
        render_html(f"""
            <div class="score-card-panel">
                <div class="score-card-col">
                    <span class="score-card-lbl">SCORE</span>
                    <span class="score-card-val">{current_runs}/{wickets}</span>
                </div>
                <div class="score-card-divider"></div>
                <div class="score-card-col">
                    <span class="score-card-lbl">OVERS</span>
                    <span class="score-card-val">{current_balls//6}.{current_balls%6}</span>
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
                    update_score(match_id, val + 1, 0)
                    st.session_state.show_extras = False
                    st.session_state.continue_after_target = False
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
                
        # Cancel Outline Button
        st.markdown('<div class="extra-cancel-btn">', unsafe_allow_html=True)
        if st.button("Cancel", key="cancel_extras_popup", use_container_width=True):
            st.session_state.show_extras = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    else:
        # Scoring Row 1 (0, 1, 2, 3)
        c0, c1, c2, c3 = st.columns(4)
        for idx, val in enumerate(["0", "1", "2", "3"]):
            col_target = [c0, c1, c2, c3][idx]
            with col_target:
                st.markdown('<div class="glossy-btn-container">', unsafe_allow_html=True)
                if st.button(val, key=f"g{val}", use_container_width=True):
                    update_score(match_id, int(val), 1)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        # Scoring Row 2 (4, 6, OUT, UNDO with icon)
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
            # Unicode back-arrow matching the screenshot aesthetic for UNDO action
            if st.button("↩ UNDO", key="gundo", use_container_width=True):
                update_score(match_id, 0, 0, is_undo=True)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # Huge Premium Pill Style 'ADD EXTRAS' Button
        st.markdown('<div class="add-extras-btn">', unsafe_allow_html=True)
        if st.button("ADD EXTRAS", key="trigger_extras_popup", use_container_width=True):
            st.session_state.show_extras = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

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

    render_html("""
        <div class="credit">
            <span>Created by <strong class="glowing-name">Amanullah Khan</strong></span><br/>
            <a href="https://www.smartstudygrid.com/" target="_blank" class="credit-link">www.smartstudygrid.com</a>
        </div>
    """)

def _render_overlay_box(overlay_url, match_id=None, confirm_key=None, reset_key=None, show_reset=False):
    """Renders the OBS Link Copy action matching Screenshot 2026-06-18 120145.png button layout precisely."""
    components.html(f"""
        <style>
            * {{ margin:0; padding:0; box-sizing:border-box; }}
            body {{ background:transparent; font-family:'Roboto Condensed',sans-serif; }}
            .wrap {{ display:flex; flex-direction:column; gap:5px; margin-bottom:10px; }}
            
            .copy-btn {{
                width: 100%; 
                height: 40px; 
                cursor: pointer;
                background: #0d1322; 
                color: #eaeaea;
                font-family: 'Roboto Condensed', sans-serif;
                font-size: 12px; 
                font-weight: 700; 
                letter-spacing: 1.5px;
                border: 1px solid rgba(188, 160, 104, 0.4); 
                border-radius: 20px;
                text-transform: uppercase; 
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 16px;
                box-shadow: inset 0 1px 1px rgba(255,255,255,0.05), 0 4px 10px rgba(0,0,0,0.5);
                transition: all 0.2s;
            }}
            .copy-btn:hover {{ 
                background: #111a30; 
                border-color: rgba(188, 160, 104, 0.7);
            }}
            .url-box {{
                background:rgba(0,0,0,0.35); border:1px solid rgba(188,160,104,0.15);
                border-radius:8px; padding:6px 10px;
                display:flex; align-items:center; gap:8px;
            }}
            .url-text {{ font-size:10px; color:#c3a469; word-break:break-all; flex:1; }}
            .hint {{ font-size:9px; color:rgba(255,255,255,0.3); letter-spacing:1px; text-transform:uppercase; text-align:center; margin-top: 2px; }}
        </style>
        <div class="wrap">
            <button class="copy-btn" onclick="
                navigator.clipboard.writeText('{overlay_url}').then(function(){{
                    document.getElementById('btn-txt').innerText='✅ Copied!';
                    setTimeout(function(){{ document.getElementById('btn-txt').innerText='Copy Overlay Link'; }}, 2000);
                }}).catch(function(){{
                    document.getElementById('btn-txt').innerText='⚠️ Failed to Copy';
                }});
            ">
                <span>🔗 &nbsp;<span id="btn-txt">Copy Overlay Link</span></span>
                <span>✦</span>
            </button>
            <div class="url-box"><span>🔗</span><span class="url-text">{overlay_url}</span></div>
            <div class="hint">Add as browser source in OBS / CameraFi / PrismLive</div>
        </div>
    """, height=104)

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
    render_html(WAKE_LOCK_AND_DOM_STYLER_SCRIPT)

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
            
            /* Premium Broadcast ticker layout */
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
            
            .ticker-team-rows {
                display: flex; flex-direction: column; align-items: center; justify-content: center;
                text-align: center; font-family: 'Oswald', sans-serif; line-height: 1.1;
                text-transform: uppercase; width: 100%; min-width: 80px;
            }
            .team-row-1 {
                font-size: 16px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;
            }
            .team-row-2 {
                font-size: 14px; font-weight: 700; color: #f3c64f; letter-spacing: 0.5px;
                text-shadow: 0 0 4px rgba(243, 198, 79, 0.3);
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
            .ticker-val-max-overlay {
                color: #ffd700; font-family: 'Oswald', sans-serif;
                font-size: 24px; font-weight: 700; line-height: 1.1;
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
    need_val      = max(0, needed)
    balls_left    = max(0, max_balls - current_balls)
    need_color    = "#ff6b6b" if needed > 0 else "#6fcf97"
    wickets       = get_wickets(d.get("history"))

    team1_name    = d.get("team1_name") or "Team 1"
    team2_name    = d.get("team2_name") or "Team 2"
    batting_first = int(d.get("batting_first") or 1)
    team_inn1     = team1_name if batting_first == 1 else team2_name
    team_inn2     = team2_name if batting_first == 1 else team1_name
    
    if innings == 1:
        batting_team = team_inn1
        bowling_team = team_inn2
    else:
        batting_team = team_inn2
        bowling_team = team_inn1
        
    words = batting_team.strip().split()
    row1 = ""
    row2 = ""
    if len(words) >= 2:
        row1 = words[0].upper()
        row2 = words[1].upper()
    elif len(words) == 1:
        row1 = words[0].upper()
        row2 = ""
    else:
        row1 = "TEAM"
        row2 = "1"

    try:
        formatted_max = f"({int(max_overs):02d})"
    except:
        formatted_max = f"({max_overs})"

    target_achieved = (innings == 2 and current_runs > innings1_runs)
    innings2_completed = (innings == 2 and (current_balls >= max_balls or wickets >= 10))
    match_over = target_achieved or innings2_completed

    if match_over:
        if current_runs > innings1_runs:
            winner_text = batting_team.upper()
            wickets_left = 10 - wickets
            margin = f"{wickets_left} WICKET" + ("S" if wickets_left > 1 else "")
            outcome_banner = f"🏆 {winner_text} WON BY {margin}"
        elif current_runs < innings1_runs:
            winner_text = bowling_team.upper()
            runs_diff = innings1_runs - current_runs
            margin = f"{runs_diff} RUN" + ("S" if runs_diff > 1 else "")
            outcome_banner = f"🏆 {winner_text} WON BY {margin}"
        else:
            outcome_banner = "🏆 MATCH TIED 🤝"

        t = f'<div class="ticker-overlay-container" style="justify-content: center; padding: 12px 24px;">'
        t += '  <div class="ticker-accent-bar"></div>'
        t += f'  <div style="font-family:\'Oswald\', sans-serif; font-size: 24px; font-weight: 800; color: #ffd700; text-align: center; text-transform: uppercase; letter-spacing: 0.5px;">'
        t += f'    {outcome_banner}'
        t += '  </div>'
        t += '</div>'
    else:
        # Standard broadcast overlay layout
        t = f'<div class="ticker-overlay-container">'
        t += '  <div class="ticker-accent-bar"></div>'
        
        t += '  <div class="ticker-cell" style="min-width: 80px;">'
        t += '    <div class="ticker-team-rows">'
        t += f'      <div class="team-row-1">{row1}</div>'
        t += f'      <div class="team-row-2">{row2}</div>'
        t += '    </div>'
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
        t += f'    <span class="ticker-val-max-overlay">{formatted_max}</span>'
        t += '  </div>'

        if innings == 2:
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
