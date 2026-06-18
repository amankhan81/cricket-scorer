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

def render_main(match_id):
    # Base Premium CSS covering glossy bevel elements, squircle buttons & custom colors
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Roboto+Condensed:wght@400;700&display=swap');
            header, footer, #MainMenu { display: none !important; }
            
            /* Background matches image_f143bf.png radial gradient */
            .stApp { 
                background: radial-gradient(circle at top, #14223f 0%, #0a0f1d 100%) !important; 
                min-height: 100vh; 
            }
            .block-container { padding: 12px 10px 16px 10px !important; max-width: 440px !important; margin: 0 auto !important; }

            /* Badges & Headers */
            .innings-badge { text-align: center; margin-bottom: 8px; }
            .innings-badge span {
                background: rgba(195, 164, 105, 0.12); color: #c3a469;
                font-family: 'Roboto Condensed', sans-serif; font-size: 13px; font-weight: 700;
                letter-spacing: 2.5px; text-transform: uppercase;
                padding: 5px 20px; border-radius: 20px; border: 1.5px solid rgba(195, 164, 105, 0.4);
            }
            
            /* Share Scoring Pill Style */
            .share-pill {
                display: inline-flex; align-items: center; gap: 6px; 
                background: rgba(37, 211, 102, 0.12); color: #25d366; 
                font-family: 'Roboto Condensed', sans-serif; font-size: 11px; 
                font-weight: 700; letter-spacing: 2px; text-transform: uppercase; 
                padding: 6px 16px; border-radius: 20px; 
                border: 1.5px solid rgba(37, 211, 102, 0.35); text-decoration: none;
                transition: background 0.2s;
            }
            .share-pill:hover { background: rgba(37, 211, 102, 0.22); }

            /* Score Card Box styling from image_f143bf.png */
            .score-header {
                display: flex; justify-content: space-around; align-items: center;
                background: linear-gradient(180deg, rgba(20, 31, 58, 0.8) 0%, rgba(10, 16, 32, 0.9) 100%);
                border: 1.5px solid rgba(255,255,255,0.08);
                border-radius: 24px; padding: 12px 10px; margin-bottom: 14px;
                box-shadow: inset 0 2px 2px rgba(255,255,255,0.05), 0 10px 25px rgba(0,0,0,0.5);
            }
            .score-divider { width: 1.5px; height: 50px; background: rgba(255,255,255,0.08); }
            .score-col { text-align: center; }
            .lbl { color: rgba(255,255,255,0.4); font-family: 'Roboto Condensed', sans-serif; font-size: 11px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; display: block; margin-bottom: 2px; }
            .val { color: #ffffff; font-family: 'Oswald', sans-serif; font-size: 48px; font-weight: 700; display: block; line-height: 1; }

            /* Clean layout structures */
            [data-testid="stHorizontalBlock"] { gap: 8px !important; flex-wrap: nowrap !important; }
            [data-testid="stColumn"] { padding: 0 !important; min-width: 0 !important; }
            [data-testid="stVerticalBlockBorderWrapper"] { gap: 0 !important; }
            [data-testid="stVerticalBlock"] > * { margin-bottom: 0 !important; }
            div[data-testid="stVerticalBlock"] > div { gap: 0 !important; }
            [data-testid="element-container"] { margin: 0 !important; padding: 0 !important; }
            .stButton { margin: 0 !important; padding: 0 !important; }

            /* GLOSSY BUTTON GENERATOR matches image_f143bf.png exactly */
            .glossy-btn-container button {
                background: linear-gradient(180deg, #20355c 0%, #111d33 100%) !important;
                border: 2.5px solid #bda064 !important;
                border-radius: 22px !important;
                box-shadow: inset 0 2px 4px rgba(255,255,255,0.15), inset 0 -4px 8px rgba(0,0,0,0.6), 0 6px 14px rgba(0,0,0,0.5) !important;
                color: #ffffff !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 34px !important;
                font-weight: 700 !important;
                height: 84px !important;
                width: 100% !important;
                text-shadow: 0 2px 4px rgba(0,0,0,0.6) !important;
                transition: transform 0.1s ease, box-shadow 0.1s ease !important;
            }
            .glossy-btn-container button:active {
                transform: scale(0.96) !important;
                box-shadow: inset 0 3px 5px rgba(0,0,0,0.8) !important;
            }
            
            /* Custom Colors for Keys */
            .btn-four button { color: #f3c64f !important; }
            .btn-six button { color: #52d273 !important; }
            .btn-out button { color: #ec4849 !important; font-size: 26px !important; }
            .btn-undo button { color: #4da6ff !important; font-size: 20px !important; }

            /* ADD EXTRAS Premium Pill Button */
            .add-extras-btn button {
                background: linear-gradient(180deg, #234075 0%, #12213f 100%) !important;
                border: 2.5px solid #bda064 !important;
                border-radius: 30px !important;
                box-shadow: inset 0 3px 6px rgba(255,255,255,0.2), inset 0 -3px 6px rgba(0,0,0,0.4), 0 8px 16px rgba(0,0,0,0.6) !important;
                color: #ffffff !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 24px !important;
                font-weight: 700 !important;
                height: 64px !important;
                width: 100% !important;
                letter-spacing: 1.5px !important;
                text-shadow: 0 2px 4px rgba(0,0,0,0.6) !important;
                margin: 12px 0 !important;
            }
            .add-extras-btn button:active {
                transform: scale(0.98) !important;
            }

            /* POPUP EXTRAS MODAL matches app new interface.png */
            .extras-modal {
                background: #142850 !important;
                border: 2.5px solid #99804a !important;
                border-radius: 18px !important;
                overflow: hidden !important;
                box-shadow: 0 12px 30px rgba(0,0,0,0.7) !important;
                margin: 10px 0 !important;
            }
            .extras-header {
                background: linear-gradient(180deg, #99804a 0%, #7a6637 100%) !important;
                color: #ffffff !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 22px !important;
                font-weight: 700 !important;
                text-align: center !important;
                padding: 10px 0 !important;
                letter-spacing: 2px !important;
                text-shadow: 0 2px 4px rgba(0,0,0,0.4) !important;
                text-transform: uppercase !important;
            }
            .extras-body {
                padding: 20px 12px !important;
            }

            /* Wide Buttons in modal (4 col) */
            .extra-wide-btn button {
                background: linear-gradient(180deg, #1d335c 0%, #101c34 100%) !important;
                border: 2.2px solid #bda064 !important;
                border-radius: 18px !important;
                box-shadow: inset 0 2px 4px rgba(255,255,255,0.15), inset 0 -3px 6px rgba(0,0,0,0.5), 0 5px 10px rgba(0,0,0,0.4) !important;
                color: #ffffff !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 26px !important;
                font-weight: 700 !important;
                height: 72px !important;
                width: 100% !important;
            }
            
            /* No Ball Buttons in modal (6 col) */
            .extra-no-btn button {
                background: linear-gradient(180deg, #1d335c 0%, #101c34 100%) !important;
                border: 1.8px solid #bda064 !important;
                border-radius: 14px !important;
                box-shadow: inset 0 2px 3px rgba(255,255,255,0.15), inset 0 -2px 4px rgba(0,0,0,0.5), 0 4px 8px rgba(0,0,0,0.4) !important;
                color: #ffffff !important;
                font-family: 'Oswald', sans-serif !important;
                font-size: 16px !important;
                font-weight: 700 !important;
                height: 48px !important;
                width: 100% !important;
                padding: 0 !important;
            }

            /* Cancel Pill Button */
            .extra-cancel-btn button {
                background: transparent !important;
                border: 2px solid #bda064 !important;
                border-radius: 20px !important;
                color: #ff5252 !important;
                font-family: 'Roboto Condensed', sans-serif !important;
                font-size: 14px !important;
                font-weight: 700 !important;
                height: 38px !important;
                width: 130px !important;
                margin: 15px auto 0 auto !important;
                display: block !important;
                text-shadow: 0 1px 2px rgba(0,0,0,0.5) !important;
                transition: background 0.2s !important;
            }
            .extra-cancel-btn button:hover {
                background: rgba(255, 82, 82, 0.1) !important;
            }

            /* Redesigned Premium Reset and Theme Toggle Controls */
            .premium-reset-btn button {
                background: linear-gradient(180deg, #3d1b1b 0%, #200d0d 100%) !important;
                border: 1.5px solid #ff6b6b !important;
                border-radius: 14px !important;
                color: #ff8b8b !important;
                font-family: 'Roboto Condensed', sans-serif !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                height: 44px !important;
                letter-spacing: 1px !important;
                box-shadow: 0 4px 8px rgba(0,0,0,0.4) !important;
            }
            .premium-theme-btn button {
                background: linear-gradient(180deg, #1d335c 0%, #101c34 100%) !important;
                border: 1.5px solid #bda064 !important;
                border-radius: 14px !important;
                color: #f0c040 !important;
                font-family: 'Roboto Condensed', sans-serif !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                height: 44px !important;
                letter-spacing: 1px !important;
                box-shadow: 0 4px 8px rgba(0,0,0,0.4) !important;
            }

            /* Other layouts */
            .target-bar {
                background: rgba(195, 164, 105, 0.1); border: 1px solid rgba(195, 164, 105, 0.3);
                border-radius: 12px; padding: 8px 16px; text-align: center; margin-bottom: 12px;
                font-family: 'Roboto Condensed', sans-serif; color: #e5c185; font-size: 14px; font-weight: 700; letter-spacing: 1px;
            }
            .credit { text-align: center; margin-top: 15px; padding-top: 10px; border-top: 1.5px solid rgba(255,255,255,0.05); }
            .credit span { font-family: 'Roboto Condensed', sans-serif; font-size: 10px; letter-spacing: 2px; color: rgba(255,255,255,0.25); text-transform: uppercase; }
            .credit strong { color: rgba(195, 164, 105, 0.6); font-weight: 700; }
        </style>
    """, unsafe_allow_html=True)

    if st.session_state.get("light_mode"):
        st.markdown("""
            <style>
                .stApp { background: radial-gradient(circle at top, #eef3f9 0%, #d5e0ee 100%) !important; }
                .score-header { background: linear-gradient(180deg, #ffffff 0%, #e6effa 100%) !important; border-color: rgba(0,0,0,0.1) !important; }
                .lbl { color: rgba(0,0,0,0.5) !important; }
                .val { color: #14223f !important; }
                .glossy-btn-container button {
                    background: linear-gradient(180deg, #ffffff 0%, #e2ebf6 100%) !important;
                    color: #14223f !important;
                    border-color: #bda064 !important;
                    box-shadow: inset 0 2px 4px rgba(255,255,255,1), 0 4px 8px rgba(0,0,0,0.15) !important;
                }
                .add-extras-btn button {
                    background: linear-gradient(180deg, #ffffff 0%, #e2ebf6 100%) !important;
                    color: #14223f !important;
                    border-color: #bda064 !important;
                }
                .extras-modal { background: #eef3f9 !important; border-color: #7a6637 !important; }
                .extra-wide-btn button, .extra-no-btn button {
                    background: linear-gradient(180deg, #ffffff 0%, #e2ebf6 100%) !important;
                    color: #14223f !important;
                }
                .extra-cancel-btn button { background: rgba(0,0,0,0.03) !important; }
                .target-bar { background: rgba(0,0,0,0.03) !important; color: #7a6637 !important; }
                .credit span { color: rgba(0,0,0,0.4) !important; }
            </style>
        """, unsafe_allow_html=True)

    base_url = st.context.url if hasattr(st, 'context') and hasattr(st.context, 'url') else "https://your-app.streamlit.app"
    if "?" in base_url:
        base_url = base_url.split("?")[0]
    overlay_url = base_url + "?mode=overlay&match=" + match_id

    if not match_id:
        st.markdown("<div style='color:white;text-align:center;font-family:Oswald;font-size:32px;margin-top:40px;margin-bottom:5px;'>🏏 Smart Cricket Scorer</div>", unsafe_allow_html=True)
        st.markdown("<div style='color:rgba(255,255,255,0.4);text-align:center;font-family:Roboto Condensed;font-size:12px;letter-spacing:3px;text-transform:uppercase;margin-bottom:30px;'>MATCH SETUP</div>", unsafe_allow_html=True)

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

    if innings == 1 and innings_over:
        st.markdown(f"""
            <div style="background:rgba(20,31,58,0.5); border:1.5px solid rgba(255,255,255,0.08); border-radius:24px; padding:30px 10px; text-align:center; margin:20px 0;">
                <h2 style="font-family:'Oswald',sans-serif; color:#f0c040; font-size:28px; margin-bottom:10px;">Innings Over</h2>
                <div style="font-family:'Oswald',sans-serif; color:white; font-size:60px; font-weight:700; line-height:1; margin-bottom:4px;">{current_runs}/{wickets}</div>
                <div style="font-family:'Roboto Condensed',sans-serif; color:rgba(255,255,255,0.45); font-size:12px; letter-spacing:3px; text-transform:uppercase; margin-bottom:20px;">{batting_team} — 1st Innings Score</div>
                <p style="font-family:'Roboto Condensed',sans-serif; color:rgba(255,255,255,0.6); font-size:15px;">{bowling_team} to chase. Start 2nd innings.</p>
            </div>
        """, unsafe_allow_html=True)
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
        st.markdown(f"""
            <div style="background:rgba(195,164,105,0.12); border:1.5px solid rgba(195,164,105,0.35); border-radius:24px; padding:32px 20px; text-align:center; margin:20px 0;">
                <h2 style="font-family:'Oswald',sans-serif; color:#f0c040; font-size:32px; margin-bottom:10px;">Match Over</h2>
                <p style="font-family:'Roboto Condensed',sans-serif; color:rgba(255,255,255,0.7); font-size:18px; margin-bottom:24px;">{result}</p>
                <div style="font-family:'Roboto Condensed',sans-serif; color:rgba(255,255,255,0.5); font-size:13px; letter-spacing:2px;">
                    {team_inn1}: {innings1_runs} &nbsp;|&nbsp; {team_inn2}: {current_runs}/{wickets}
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="add-extras-btn">', unsafe_allow_html=True)
        if st.button("NEW MATCH", use_container_width=True):
            st.query_params.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    st.markdown('<div class="innings-badge"><span>' + batting_team + ' &mdash; ' + ("1st" if innings == 1 else "2nd") + ' Innings</span></div>', unsafe_allow_html=True)
    whatsapp_share_url = "https://easyscoring.streamlit.app/?match=" + match_id
    whatsapp_link = "https://wa.me/?text=" + whatsapp_share_url
    st.markdown(f'<div style="text-align:center;margin-bottom:12px;"><a class="share-pill" href="{whatsapp_link}" target="_blank">📲 Share Scoring</a></div>', unsafe_allow_html=True)

    # Score Board View from image_f143bf.png
    st.markdown(f"""
        <div class="score-header">
            <div class="score-col">
                <span class="lbl">Score</span>
                <span class="val">{current_runs}/{wickets}</span>
            </div>
            <div class="score-divider"></div>
            <div class="score-col">
                <span class="lbl">Overs</span>
                <span class="val">{current_balls//6}.{current_balls%6}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Target statement for 2nd innings
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
        
        # Row 1: Wides (w+1, w+2, w+3, w+4)
        st.markdown('<div style="margin-bottom: 5px; text-align: center; color: rgba(255,255,255,0.4); font-family:\'Roboto Condensed\', sans-serif; font-size:11px; font-weight:700; letter-spacing:1px; text-transform:uppercase;">Wide Balls</div>', unsafe_allow_html=True)
        wcols = st.columns(4)
        w_options = [1, 2, 3, 4]
        for idx, val in enumerate(w_options):
            with wcols[idx]:
                st.markdown('<div class="extra-wide-btn">', unsafe_allow_html=True)
                if st.button(f"w+{val}", key=f"popup_w_{val}", use_container_width=True):
                    # Adds val runs, 0 legal balls recorded
                    update_score(match_id, val, 0)
                    st.session_state.show_extras = False
                    st.session_state.continue_after_target = False
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div style="height: 16px;"></div>', unsafe_allow_html=True)
        
        # Row 2: No Balls (N+1, N+2, N+3, N+4, N+5, N+6)
        st.markdown('<div style="margin-bottom: 5px; text-align: center; color: rgba(255,255,255,0.4); font-family:\'Roboto Condensed\', sans-serif; font-size:11px; font-weight:700; letter-spacing:1px; text-transform:uppercase;">No Balls</div>', unsafe_allow_html=True)
        ncols = st.columns(6)
        n_options = [1, 2, 3, 4, 5, 6]
        for idx, val in enumerate(n_options):
            with ncols[idx]:
                st.markdown('<div class="extra-no-btn">', unsafe_allow_html=True)
                if st.button(f"N+{val}", key=f"popup_n_{val}", use_container_width=True):
                    # Adds val runs, 0 legal balls recorded
                    update_score(match_id, val, 0)
                    st.session_state.show_extras = False
                    st.session_state.continue_after_target = False
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
                
        # Cancel Button
        st.markdown('<div class="extra-cancel-btn">', unsafe_allow_html=True)
        if st.button("Cancel", key="cancel_extras_popup", use_container_width=True):
            st.session_state.show_extras = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div></div>', unsafe_allow_html=True)

    else:
        
        # Row 1: 0, 1, 2, 3
        c0, c1, c2, c3 = st.columns(4)
        with c0:
            st.markdown('<div class="glossy-btn-container">', unsafe_allow_html=True)
            if st.button("0", key="g0", use_container_width=True):
                update_score(match_id, 0, 1)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c1:
            st.markdown('<div class="glossy-btn-container">', unsafe_allow_html=True)
            if st.button("1", key="g1", use_container_width=True):
                update_score(match_id, 1, 1)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="glossy-btn-container">', unsafe_allow_html=True)
            if st.button("2", key="g2", use_container_width=True):
                update_score(match_id, 2, 1)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c3:
            st.markdown('<div class="glossy-btn-container">', unsafe_allow_html=True)
            if st.button("3", key="g3", use_container_width=True):
                update_score(match_id, 3, 1)
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

        # Huge Premium Pill Style 'ADD EXTRAS' Button
        st.markdown('<div class="add-extras-btn">', unsafe_allow_html=True)
        if st.button("ADD EXTRAS", key="trigger_extras_popup", use_container_width=True):
            st.session_state.show_extras = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Render footer utilities & overlays
    if st.session_state.get("confirm_reset_active"):
        st.markdown("""
            <div style="background:rgba(235,87,87,0.12); border:1.5px solid rgba(235,87,87,0.35); border-radius:14px; padding:12px; margin-top:10px; text-align:center;">
                <p style="font-family:'Roboto Condensed',sans-serif; color:white; font-size:14px; font-weight:700; margin-bottom:10px;">⚠️ Confirm Reset Match?</p>
            </div>
        """, unsafe_allow_html=True)
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
            
            /* Compact ticker bar overlay */
            .ticker {
                position: fixed; bottom: 14px; left: 14px;
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
            .ticker-winner    { font-family: 'Roboto Condensed', sans-serif; font-size: 11px; font-weight: 700; letter-spacing: 1.5px; color: #4ade80; text-transform: uppercase; align-self: center; padding: 2px 8px; background: rgba(74,222,128,0.15); border: 1px solid rgba(74,222,128,0.35); border-radius: 6px; white-space: nowrap; }
        </style>
    """, unsafe_allow_html=True)

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

    t  = '<div class="ticker">'
    t += '<div class="ticker-accent"></div>'
    t += '<div class="ticker-body">'
    t += '<div class="ticker-icon">🏏</div>'
    t += '<div class="ticker-overs"><div class="ticker-overs-lbl">Batting</div><div class="ticker-overs-val" style="color:#f0c040;font-size:16px;">' + batting_abbrev + '</div></div>'
    t += '<div class="ticker-sep"></div>'
    t += '<div class="ticker-score">' + str(current_runs) + '/' + str(wickets) + '</div>'
    t += '<div class="ticker-sep"></div>'
    t += '<div class="ticker-overs"><div class="ticker-overs-lbl">Overs</div><div class="ticker-overs-val">' + overs_str + '</div></div>'
    t += '<div class="ticker-sep"></div>'
    t += '<div class="ticker-overs"><div class="ticker-overs-lbl">Max</div><div class="ticker-overs-val">' + str(max_overs) + '</div></div>'

    if match_over:
        t += '<div class="ticker-sep"></div>'
        t += '<div class="ticker-winner">🏆 ' + winner_text + '</div>'
    elif innings == 2:
        t += '<div class="ticker-sep"></div>'
        t += '<div class="ticker-overs"><div class="ticker-overs-lbl">Target</div><div class="ticker-overs-val" style="color:#c8c8c8;">' + str(target_val) + '</div></div>'
        t += '<div class="ticker-sep"></div>'
        t += '<div class="ticker-overs"><div class="ticker-overs-lbl">Need</div><div class="ticker-overs-val" style="color:' + need_color + ';">' + f"{need_val} off {balls_left}" + '</div></div>'

    t += '</div></div>'

    st.markdown(t, unsafe_allow_html=True)
    time.sleep(2)
    st.rerun()

params   = st.query_params
mode     = params.get("mode", "")
match_id = params.get("match", "").strip().upper()

if mode == "overlay":
    render_overlay(match_id)
else:
    render_main(match_id)
