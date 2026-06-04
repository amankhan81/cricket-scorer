import streamlit as st
from supabase import create_client
import json
import time
import random
import string

# --- DB CONNECTION ---
# Replace these with your own Supabase project URL and anon/public key
URL = "https://pnuyhhbvdzfursvnngwq.supabase.co"
KEY = "sb_publishable_Lmh7sO4LnBkSWgmSjanplg_9qgT7svQ"
supabase = create_client(URL, KEY)

# --- HELPERS ---

def generate_match_id(length=6):
    """Generate a short random uppercase alphanumeric match ID."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

def team_abbrev(name):
    """Return initials if multi-word, first 3 letters if single word."""
    words = name.strip().split()
    if len(words) > 1:
        return "".join(w[0].upper() for w in words)
    return name[:3].upper()


def get_match(match_id):
    """Fetch match row by match_id. Returns None if not found."""
    res = supabase.table("match_data").select("*").eq("match_id", match_id).execute()
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

def create_match(match_id, match_overs, team1_name="Team 1", team2_name="Team 2", batting_first=1):
    """Insert a new match row."""
    supabase.table("match_data").insert({
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

def update_score(match_id, runs_inc, balls_inc, is_undo=False):
    d = get_match(match_id)
    if not d:
        return
    history = json.loads(d["history"])
    if is_undo:
        if len(history) > 0:
            last = history.pop()
            supabase.table("match_data").update({
                "runs":    max(0, d["runs"]  - last["r"]),
                "balls":   max(0, d["balls"] - last["b"]),
                "history": json.dumps(history)
            }).eq("match_id", match_id).execute()
    else:
        history.append({"r": runs_inc, "b": balls_inc})
        supabase.table("match_data").update({
            "runs":    d["runs"]  + runs_inc,
            "balls":   d["balls"] + balls_inc,
            "history": json.dumps(history)
        }).eq("match_id", match_id).execute()

def reset_match(match_id):
    supabase.table("match_data").update({
        "runs": 0, "balls": 0, "history": "[]",
        "innings": 1, "innings1_runs": 0
    }).eq("match_id", match_id).execute()

def start_second_innings(match_id, innings1_score):
    supabase.table("match_data").update({
        "innings": 2, "innings1_runs": innings1_score,
        "runs": 0, "balls": 0, "history": "[]"
    }).eq("match_id", match_id).execute()

# --- SHARED CSS ---
SHARED_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Roboto+Condensed:wght@400;700&display=swap');
</style>
"""

# ════════════════════════════════════════════════════════
#  OVERLAY MODE  (?mode=overlay&match=XXXXXX)
# ════════════════════════════════════════════════════════

def render_overlay(match_id):
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@700&family=Roboto+Condensed:wght@700&display=swap');

            html, body { background: transparent !important; background-color: transparent !important; }
            .stApp { background: transparent !important; background-color: transparent !important; }
            [data-testid="stAppViewContainer"] { background: transparent !important; }
            [data-testid="stHeader"]           { display: none !important; }
            [data-testid="stToolbar"]          { display: none !important; }
            [data-testid="stDecoration"]       { display: none !important; }
            [data-testid="stStatusWidget"]     { display: none !important; }
            [data-testid="stMainBlockContainer"]{ background: transparent !important; }
            [data-testid="block-container"]    { background: transparent !important; }
            .main { background: transparent !important; }
            section[data-testid="stSidebar"]   { display: none !important; }
            header, footer, #MainMenu          { display: none !important; }
            .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }

            .ticker {
                position: fixed; top: 14px; left: 14px;
                display: inline-flex; align-items: stretch;
                border-radius: 8px; overflow: hidden;
                box-shadow: 0 4px 24px rgba(0,0,0,0.5), 0 1px 4px rgba(0,0,0,0.3);
                font-family: 'Oswald', sans-serif;
            }
            .ticker-accent { width: 5px; background: linear-gradient(180deg, #f0c040, #c8960a); flex-shrink: 0; }
            .ticker-body {
                background: rgba(10, 10, 20, 0.88);
                backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
                padding: 10px 16px 10px 12px; display: flex; align-items: center; gap: 10px;
            }
            .ticker-icon  { font-size: 18px; line-height: 1; opacity: 0.85; }
            .ticker-score { font-size: 42px; font-weight: 700; color: #ffffff; line-height: 1; letter-spacing: -1px; }
            .ticker-sep   { width: 1px; height: 36px; background: rgba(255,255,255,0.15); flex-shrink: 0; }
            .ticker-overs { display: flex; flex-direction: column; align-items: flex-start; gap: 1px; }
            .ticker-overs-lbl { font-family: 'Roboto Condensed', sans-serif; font-size: 9px; letter-spacing: 2px; color: rgba(255,255,255,1); text-transform: uppercase; }
            .ticker-overs-val { font-size: 20px; font-weight: 700; color: #f0c040; line-height: 1; }
            .ticker-match-id  { font-family: 'Roboto Condensed', sans-serif; font-size: 9px; letter-spacing: 1.5px; color: rgba(255,255,255,0.5); text-transform: uppercase; align-self: flex-end; padding-bottom: 2px; }
            .ticker-innings   { font-family: 'Roboto Condensed', sans-serif; font-size: 9px; letter-spacing: 1.5px; color: rgba(255,255,255,1); text-transform: uppercase; align-self: flex-end; padding-bottom: 2px; }
        </style>
    """, unsafe_allow_html=True)

    d = get_match(match_id)
    if not d:
        st.markdown("<div style='color:red;font-family:monospace;padding:10px;'>Match not found: " + match_id + "</div>", unsafe_allow_html=True)
        return

    innings       = int(d.get("innings") or 1)
    overs_str     = str(d['balls'] // 6) + "." + str(d['balls'] % 6)
    max_overs     = int(d['match_overs'])
    innings1_runs = int(d.get("innings1_runs") or 0)
    current_runs  = int(d["runs"])
    needed        = innings1_runs - current_runs + 1
    target_val    = innings1_runs + 1
    need_val      = max(0, needed)
    need_color    = "#ff6b6b" if needed > 0 else "#6fcf97"

    # Determine batting team abbreviation
    team1_name    = d.get("team1_name") or "Team 1"
    team2_name    = d.get("team2_name") or "Team 2"
    batting_first = int(d.get("batting_first") or 1)
    if innings == 1:
        batting_team = team1_name if batting_first == 1 else team2_name
        bowling_team = team2_name if batting_first == 1 else team1_name
    else:
        batting_team = team2_name if batting_first == 1 else team1_name
        bowling_team = team1_name if batting_first == 1 else team2_name
    batting_abbrev = team_abbrev(batting_team)
    bowling_abbrev = team_abbrev(bowling_team)
    innings_lbl   = batting_abbrev + " INN" + str(innings)

    t  = '<div class="ticker">'
    t += '<div class="ticker-accent"></div>'
    t += '<div class="ticker-body">'
    t += '<div class="ticker-icon">🏏</div>'
    t += '<div class="ticker-overs"><div class="ticker-overs-lbl">Batting</div><div class="ticker-overs-val" style="color:#f0c040;font-size:16px;">' + batting_abbrev + '</div></div>'
    t += '<div class="ticker-sep"></div>'
    t += '<div class="ticker-score">' + str(current_runs) + '</div>'
    t += '<div class="ticker-sep"></div>'
    t += '<div class="ticker-overs"><div class="ticker-overs-lbl">Overs</div><div class="ticker-overs-val">' + overs_str + '</div></div>'
    t += '<div class="ticker-sep"></div>'
    t += '<div class="ticker-overs"><div class="ticker-overs-lbl">Max</div><div class="ticker-overs-val">' + str(max_overs) + '</div></div>'

    if innings == 2:
        t += '<div class="ticker-sep"></div>'
        t += '<div class="ticker-overs"><div class="ticker-overs-lbl">Target</div><div class="ticker-overs-val" style="color:#c8c8c8;">' + str(target_val) + '</div></div>'
        t += '<div class="ticker-sep"></div>'
        t += '<div class="ticker-overs"><div class="ticker-overs-lbl">Need</div><div class="ticker-overs-val" style="color:' + need_color + ';">' + str(need_val) + '</div></div>'

    t += '<div class="ticker-sep"></div>'
    t += '<div class="ticker-overs"><div class="ticker-innings">' + innings_lbl + '</div><div class="ticker-match-id">' + match_id + '</div></div>'
    t += '</div></div>'

    st.markdown(t, unsafe_allow_html=True)
    time.sleep(2)
    st.rerun()


# ════════════════════════════════════════════════════════
#  MAIN SCORING APP
# ════════════════════════════════════════════════════════

def render_main(match_id):
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Roboto+Condensed:wght@400;700&display=swap');

            header, footer, #MainMenu { display: none !important; }
            .stApp { background: linear-gradient(160deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%) !important; min-height: 100vh; }
            .block-container { padding: 16px 12px 24px 12px !important; max-width: 480px !important; margin: 0 auto !important; }

            .innings-badge { text-align: center; margin-bottom: 6px; }
            .innings-badge span {
                background: rgba(240,192,64,0.18); color: #f0c040;
                font-family: 'Roboto Condensed', sans-serif; font-size: 13px; font-weight: 700;
                letter-spacing: 3px; text-transform: uppercase;
                padding: 4px 18px; border-radius: 20px; border: 1px solid rgba(240,192,64,0.35);
            }
            .match-id-badge { text-align: center; margin-bottom: 12px; }
            .match-id-badge span {
                background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.4);
                font-family: 'Roboto Condensed', sans-serif; font-size: 11px; font-weight: 700;
                letter-spacing: 3px; text-transform: uppercase;
                padding: 3px 14px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.1);
            }

            .score-header {
                display: flex; justify-content: space-around; align-items: center;
                background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
                border-radius: 16px; padding: 14px 10px 10px; margin-bottom: 14px;
                backdrop-filter: blur(10px);
            }
            .score-divider { width: 1px; height: 60px; background: rgba(255,255,255,0.15); }
            .score-col { text-align: center; }
            .lbl { color: rgba(255,255,255,0.5); font-family: 'Roboto Condensed', sans-serif; font-size: 13px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; display: block; margin-bottom: 2px; }
            .val { color: #ffffff; font-family: 'Oswald', sans-serif; font-size: 54px; font-weight: 700; display: block; line-height: 1; }

            .target-bar {
                background: rgba(240,192,64,0.12); border: 1px solid rgba(240,192,64,0.3);
                border-radius: 10px; padding: 8px 16px; text-align: center; margin-bottom: 12px;
                font-family: 'Roboto Condensed', sans-serif; color: #f0c040; font-size: 15px; font-weight: 700; letter-spacing: 1px;
            }

            .overlay-box {
                background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1);
                border-radius: 14px; padding: 14px 16px; margin: 10px 0 4px 0;
            }
            .overlay-box-title { font-family: 'Roboto Condensed', sans-serif; font-size: 10px; letter-spacing: 3px; color: rgba(255,255,255,0.35); text-transform: uppercase; margin-bottom: 8px; }
            .overlay-link-row { display: flex; align-items: center; gap: 10px; background: rgba(0,0,0,0.3); border: 1px solid rgba(240,192,64,0.2); border-radius: 8px; padding: 8px 12px; }
            .overlay-link-icon { font-size: 16px; flex-shrink: 0; }
            .overlay-link-url { font-family: 'Roboto Condensed', sans-serif; font-size: 11px; color: #f0c040; letter-spacing: 0.3px; word-break: break-all; flex: 1; }
            .overlay-hint { font-family: 'Roboto Condensed', sans-serif; font-size: 10px; color: rgba(255,255,255,0.25); letter-spacing: 1.5px; text-transform: uppercase; margin-top: 6px; text-align: center; }

            [data-testid="stHorizontalBlock"] { gap: 8px !important; flex-wrap: nowrap !important; }
            [data-testid="stColumn"] { padding: 0 !important; min-width: 0 !important; }

            .main-btn button {
                width: 100% !important; height: 100px !important;
                background: rgba(255,255,255,0.07) !important; color: white !important;
                font-family: 'Oswald', sans-serif !important; font-size: 42px !important; font-weight: 700 !important;
                border: 1px solid rgba(255,255,255,0.12) !important; border-radius: 12px !important; padding: 0 !important;
            }
            .btn-four button { background: rgba(52,168,83,0.2)  !important; border-color: rgba(52,168,83,0.4)  !important; color: #6fcf97 !important; }
            .btn-six  button { background: rgba(240,192,64,0.2)  !important; border-color: rgba(240,192,64,0.4) !important; color: #f0c040 !important; }
            .btn-undo button {
                width: 100% !important; height: 100px !important;
                background: rgba(235,87,87,0.15) !important; border: 1px solid rgba(235,87,87,0.3) !important;
                border-radius: 12px !important; color: #eb5757 !important;
                font-family: 'Oswald', sans-serif !important; font-size: 20px !important; font-weight: 700 !important;
            }

            .section-hdr { color: rgba(255,255,255,0.45); font-family: 'Roboto Condensed', sans-serif; font-size: 11px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; text-align: center; padding: 14px 0 6px 0; }

            .extra-btn button {
                width: 100% !important; height: 52px !important;
                background: rgba(255,255,255,0.06) !important; color: rgba(255,255,255,0.85) !important;
                font-family: 'Roboto Condensed', sans-serif !important; font-size: 14px !important; font-weight: 700 !important;
                border: 1px solid rgba(255,255,255,0.1) !important; border-radius: 10px !important; padding: 0 !important;
            }

            .reset-btn button {
                width: 100% !important; height: 52px !important;
                background: rgba(235,87,87,0.1) !important; color: rgba(235,87,87,0.8) !important;
                font-family: 'Roboto Condensed', sans-serif !important; font-size: 16px !important; font-weight: 700 !important;
                letter-spacing: 2px !important; border: 1px solid rgba(235,87,87,0.25) !important;
                border-radius: 12px !important; margin-top: 14px !important;
            }

            .innings-over-box { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 20px; padding: 32px 20px; text-align: center; margin: 20px 0; }
            .innings-over-box h2 { font-family: 'Oswald', sans-serif; color: #f0c040; font-size: 32px; margin-bottom: 8px; }
            .innings-over-box p  { font-family: 'Roboto Condensed', sans-serif; color: rgba(255,255,255,0.6); font-size: 16px; margin-bottom: 24px; }
            .innings-over-box .big-score { font-family: 'Oswald', sans-serif; color: white; font-size: 64px; font-weight: 700; line-height: 1; margin-bottom: 4px; }
            .innings-over-box .big-score-lbl { font-family: 'Roboto Condensed', sans-serif; color: rgba(255,255,255,0.45); font-size: 12px; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 28px; }

            .start-btn button {
                width: 100% !important; height: 60px !important;
                background: linear-gradient(135deg, #f0c040, #e6a817) !important; color: #1a1a2e !important;
                font-family: 'Oswald', sans-serif !important; font-size: 22px !important; font-weight: 700 !important;
                letter-spacing: 2px !important; border: none !important; border-radius: 14px !important;
            }

            .result-box { background: rgba(240,192,64,0.12); border: 1px solid rgba(240,192,64,0.35); border-radius: 20px; padding: 32px 20px; text-align: center; margin: 20px 0; }
            .result-box h2 { font-family: 'Oswald', sans-serif; color: #f0c040; font-size: 36px; margin-bottom: 10px; }
            .result-box p  { font-family: 'Roboto Condensed', sans-serif; color: rgba(255,255,255,0.7); font-size: 18px; margin-bottom: 24px; }

            .setup-title { font-family: 'Oswald', sans-serif; color: white; font-size: 36px; text-align: center; margin-bottom: 4px; }
            .setup-sub   { font-family: 'Roboto Condensed', sans-serif; color: rgba(255,255,255,0.4); font-size: 13px; letter-spacing: 3px; text-transform: uppercase; text-align: center; margin-bottom: 28px; }
            label, .stNumberInput label { color: rgba(255,255,255,0.6) !important; font-family: 'Roboto Condensed', sans-serif !important; font-size: 13px !important; letter-spacing: 2px !important; }

            .credit { text-align: center; margin-top: 28px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.07); }
            .credit span { font-family: 'Roboto Condensed', sans-serif; font-size: 11px; letter-spacing: 2px; color: rgba(255,255,255,0.2); text-transform: uppercase; }
            .credit strong { color: rgba(240,192,64,0.5); font-weight: 700; }

            .new-match-btn button {
                width: 100% !important; height: 52px !important;
                background: rgba(255,255,255,0.07) !important; color: rgba(255,255,255,0.7) !important;
                font-family: 'Roboto Condensed', sans-serif !important; font-size: 14px !important; font-weight: 700 !important;
                letter-spacing: 2px !important; border: 1px solid rgba(255,255,255,0.15) !important;
                border-radius: 12px !important; margin-top: 8px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # Determine the base URL for overlay links
    # Streamlit Cloud puts the app URL in a header; we construct it from the current URL params
    base_url = st.context.url if hasattr(st, 'context') and hasattr(st.context, 'url') else "https://your-app.streamlit.app"
    # Strip any existing query params to get clean base
    if "?" in base_url:
        base_url = base_url.split("?")[0]

    overlay_url = base_url + "?mode=overlay&match=" + match_id
    scorer_url  = base_url + "?match=" + match_id

    # ── NO match_id yet → LANDING / SETUP ──
    if not match_id:
        st.markdown("<div class='setup-title'>🏏 Smart Cricket Scorer</div>", unsafe_allow_html=True)
        st.markdown("<div class='setup-sub'>MATCH SETUP</div>", unsafe_allow_html=True)

        team1_in = st.text_input("TEAM 1 NAME", value="Team 1", placeholder="e.g. Pak Eagles Riyadh")
        team2_in = st.text_input("TEAM 2 NAME", value="Team 2", placeholder="e.g. Desert Lions")
        batting_first = st.selectbox("WHO IS BATTING FIRST?", options=[team1_in, team2_in])
        ov_in = st.number_input("MATCH OVERS", min_value=1, max_value=50, value=10)

        st.markdown('<div class="start-btn">', unsafe_allow_html=True)
        if st.button("CREATE MATCH", use_container_width=True):
            new_id = generate_match_id()
            batting_first_num = 1 if batting_first == team1_in else 2
            create_match(new_id, ov_in, team1_in, team2_in, batting_first_num)
            # Redirect to URL with match param
            st.query_params["match"] = new_id
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="credit"><span>Created by <strong>Amanullah Khan</strong></span></div>', unsafe_allow_html=True)
        return

    # ── Fetch match data ──
    d = get_match(match_id)
    if not d:
        st.error("Match not found. The match ID **" + match_id + "** doesn't exist.")
        st.markdown('<div class="new-match-btn">', unsafe_allow_html=True)
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

    # Team names
    team1_name    = d.get("team1_name") or "Team 1"
    team2_name    = d.get("team2_name") or "Team 2"
    batting_first = int(d.get("batting_first") or 1)
    if innings == 1:
        batting_team = team1_name if batting_first == 1 else team2_name
        bowling_team = team2_name if batting_first == 1 else team1_name
    else:
        batting_team = team2_name if batting_first == 1 else team1_name
        bowling_team = team1_name if batting_first == 1 else team2_name

    # ── INNINGS 1 COMPLETE ──
    if innings == 1 and innings_over:
        st.markdown(f"""
            <div class="innings-over-box">
                <h2>Innings Over</h2>
                <div class="big-score">{current_runs}</div>
                <div class="big-score-lbl">{batting_team} — 1st Innings Score</div>
                <p>{bowling_team} to chase. Start the 2nd innings.</p>
            </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="start-btn">', unsafe_allow_html=True)
        if st.button("START 2ND INNINGS", use_container_width=True):
            start_second_innings(match_id, current_runs)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("RESET MATCH", key="reset_mid", use_container_width=True):
            reset_match(match_id)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        _render_overlay_box(overlay_url)
        st.markdown('<div class="credit"><span>Created by <strong>Amanullah Khan</strong></span></div>', unsafe_allow_html=True)
        return

    # ── INNINGS 2 COMPLETE → RESULT ──
    if innings == 2 and innings_over:
        # batting_first==1 means team1 batted first (innings1), team2 batted second (innings2)
        team_inn1 = team1_name if batting_first == 1 else team2_name
        team_inn2 = team2_name if batting_first == 1 else team1_name
        if current_runs > innings1_runs:
            result = team_inn2 + " wins by " + str(current_runs - innings1_runs) + " runs! 🎉"
        elif current_runs < innings1_runs:
            result = team_inn1 + " wins by " + str(innings1_runs - current_runs) + " runs! 🎉"
        else:
            result = "It's a tie! 🤝"
        st.markdown(f"""
            <div class="result-box">
                <h2>Match Over</h2>
                <p>{result}</p>
                <div style="font-family:'Roboto Condensed',sans-serif;color:rgba(255,255,255,0.5);font-size:13px;letter-spacing:2px;">
                    {team_inn1}: {innings1_runs} &nbsp;|&nbsp; {team_inn2}: {current_runs}
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="start-btn">', unsafe_allow_html=True)
        if st.button("NEW MATCH", use_container_width=True):
            st.query_params.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="credit"><span>Created by <strong>Amanullah Khan</strong></span></div>', unsafe_allow_html=True)
        return

    # ── ACTIVE SCORING ──
    st.markdown('<div class="innings-badge"><span>' + batting_team + ' &mdash; ' + ("1st" if innings == 1 else "2nd") + ' Innings</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="match-id-badge"><span>MATCH&nbsp;&nbsp;' + match_id + '</span></div>', unsafe_allow_html=True)

    st.markdown(f"""
        <div class="score-header">
            <div class="score-col">
                <span class="lbl">Score</span>
                <span class="val">{current_runs}</span>
            </div>
            <div class="score-divider"></div>
            <div class="score-col">
                <span class="lbl">Overs</span>
                <span class="val">{current_balls//6}.{current_balls%6}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if innings == 2:
        needed     = innings1_runs - current_runs + 1
        balls_left = max_balls - current_balls
        overs_left = str(balls_left // 6) + "." + str(balls_left % 6)
        if needed > 0:
            st.markdown('<div class="target-bar">🎯 Need ' + str(needed) + ' runs in ' + overs_left + ' overs</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="target-bar">✅ Target achieved!</div>', unsafe_allow_html=True)

    # ── Run buttons (row 1: 0, 1, 2, 3) ──
    c0, c1, c2, c3 = st.columns(4)
    with c0:
        st.markdown('<div class="main-btn">', unsafe_allow_html=True)
        if st.button("0", key="b0", use_container_width=True): update_score(match_id, 0, 1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c1:
        st.markdown('<div class="main-btn">', unsafe_allow_html=True)
        if st.button("1", key="b1", use_container_width=True): update_score(match_id, 1, 1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="main-btn">', unsafe_allow_html=True)
        if st.button("2", key="b2", use_container_width=True): update_score(match_id, 2, 1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="main-btn">', unsafe_allow_html=True)
        if st.button("3", key="b3", use_container_width=True): update_score(match_id, 3, 1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Run buttons (row 2: 4, 6, UNDO) ──
    c4, c5, c6 = st.columns(3)
    with c4:
        st.markdown('<div class="main-btn btn-four">', unsafe_allow_html=True)
        if st.button("4", key="b4", use_container_width=True): update_score(match_id, 4, 1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c5:
        st.markdown('<div class="main-btn btn-six">', unsafe_allow_html=True)
        if st.button("6", key="b6", use_container_width=True): update_score(match_id, 6, 1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c6:
        st.markdown('<div class="btn-undo">', unsafe_allow_html=True)
        if st.button("UNDO", key="bun", use_container_width=True): update_score(match_id, 0, 0, is_undo=True); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Wides ──
    st.markdown('<div class="section-hdr">Wides</div>', unsafe_allow_html=True)
    wcols = st.columns(5)
    for i in range(5):
        with wcols[i]:
            st.markdown('<div class="extra-btn">', unsafe_allow_html=True)
            if st.button(f"W+{i}", key=f"w{i}", use_container_width=True):
                update_score(match_id, 1 + i, 0); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ── No Ball ──
    st.markdown('<div class="section-hdr">No Ball</div>', unsafe_allow_html=True)
    ncols = st.columns(7)
    for i in range(7):
        with ncols[i]:
            st.markdown('<div class="extra-btn">', unsafe_allow_html=True)
            if st.button(f"N+{i}", key=f"n{i}", use_container_width=True):
                update_score(match_id, 1 + i, 0); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Overlay link ──
    _render_overlay_box(overlay_url)

    # ── Reset ──
    st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
    if st.button("RESET MATCH", key="reset", use_container_width=True):
        reset_match(match_id)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="credit"><span>Created by <strong>Amanullah Khan</strong></span></div>', unsafe_allow_html=True)


def _render_overlay_box(overlay_url):
    st.markdown(f"""
        <div class="overlay-box">
            <div class="overlay-box-title">📺 &nbsp;Your Score Overlay Link</div>
            <div class="overlay-link-row">
                <div class="overlay-link-icon">🔗</div>
                <div class="overlay-link-url">{overlay_url}</div>
            </div>
            <div class="overlay-hint">Add as browser source in OBS / CameraFi / PrismLive</div>
        </div>
    """, unsafe_allow_html=True)
    st.code(overlay_url, language=None)


# ════════════════════════════════════════════════════════
#  ROUTER
# ════════════════════════════════════════════════════════

params   = st.query_params
mode     = params.get("mode", "")
match_id = params.get("match", "").strip().upper()

if mode == "overlay":
    render_overlay(match_id)
else:
    render_main(match_id)
