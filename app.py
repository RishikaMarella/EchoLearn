import streamlit as st
import google.generativeai as genai
import os, json, requests, random
import speech_recognition as sr
from dotenv import load_dotenv
from streamlit_mic_recorder import mic_recorder
import urllib.parse
from datetime import datetime

load_dotenv()
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY   = os.getenv("YOUTUBE_API_KEY")
MURF_API_KEY      = os.getenv("MURF_API_KEY")
GOOGLE_CLIENT_ID  = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

REDIRECT_URI = "http://localhost:8501"
GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL  = "https://www.googleapis.com/oauth2/v3/userinfo"

genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel("gemini-2.5-flash")

QUOTES = [
    {"quote": "The beautiful thing about learning is that nobody can take it away from you.", "author": "B.B. King"},
    {"quote": "Education is the most powerful weapon to change the world.", "author": "Nelson Mandela"},
    {"quote": "The more that you read, the more things you will know.", "author": "Dr. Seuss"},
    {"quote": "Learning never exhausts the mind.", "author": "Leonardo da Vinci"},
    {"quote": "The expert in anything was once a beginner.", "author": "Helen Hayes"},
    {"quote": "Believe you can and you are halfway there.", "author": "Theodore Roosevelt"},
    {"quote": "Every day is a new chance to learn something amazing!", "author": "EchoLearn"},
]

ANIMALS = {
    "🦒": "Giraffe", "🦁": "Lion", "🐼": "Panda",
    "🦜": "Parrot", "🐯": "Tiger", "🦆": "Duck",
    "🦉": "Owl", "🐶": "Dog", "🐱": "Cat"
}

HISTORY_FILE = "lesson_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_to_history(subject, topic, lesson):
    history = load_history()
    history.insert(0, {
        "subject": subject, "topic": topic, "lesson": lesson,
        "date": datetime.now().strftime("%d %b %Y, %I:%M %p")
    })
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[:20], f)

def get_youtube_videos(query):
    try:
        from googleapiclient.discovery import build
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        res = youtube.search().list(
            q=query, part="snippet", maxResults=3, type="video"
        ).execute()
        return res.get("items", [])
    except:
        return []

def murf_audio(text):
    try:
        r = requests.post(
            "https://api.murf.ai/v1/speech/generate",
            headers={"Content-Type": "application/json", "api-key": MURF_API_KEY},
            json={"voiceId": "en-US-natalie", "style": "Conversational",
                  "text": text[:3000], "modelVersion": "GEN2"},
            timeout=30
        )
        if r.status_code == 200:
            return r.json().get("audioFile")
    except:
        pass
    return None

def get_google_auth_url():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account"
    }
    return GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)

def exchange_code_for_user(code):
    try:
        token_resp = requests.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        })
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return None
        user_resp = requests.get(
            GOOGLE_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        return user_resp.json()
    except:
        return None

st.set_page_config(
    page_title="EchoLearn 🎓",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Righteous&family=Nunito:wght@400;600;700&family=Dancing+Script:wght@700&family=Space+Grotesk:wght@400;600;700&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Nunito', sans-serif !important;
    background: radial-gradient(ellipse at top left, #2D1B69 0%, #1A0A3C 40%, #0D0620 100%) !important;
    background-attachment: fixed !important;
    color: #E8D5FF !important;
    min-height: 100vh;
}
.block-container { background: transparent !important; padding-top: 1rem !important; }

@keyframes fadeUp   { from{opacity:0;transform:translateY(36px)} to{opacity:1;transform:translateY(0)} }
@keyframes bounceIn { 0%{transform:scale(.4);opacity:0} 55%{transform:scale(1.06)} 80%{transform:scale(.97)} 100%{transform:scale(1);opacity:1} }
@keyframes float    { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-14px)} }
@keyframes glow     { 0%,100%{box-shadow:0 0 0 0 rgba(167,139,250,.5)} 50%{box-shadow:0 0 0 16px rgba(167,139,250,0)} }
@keyframes gradMove { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
@keyframes spin     { from{transform:rotate(0)} to{transform:rotate(360deg)} }
@keyframes popIn    { 0%{transform:scale(0);opacity:0} 70%{transform:scale(1.1)} 100%{transform:scale(1);opacity:1} }

.page { animation: fadeUp .65s ease both; }
.pop  { animation: bounceIn .65s ease both; }

/* HERO */
.hero {
    background: linear-gradient(270deg,#7C3AED,#9333EA,#6D28D9,#A855F7,#7C3AED);
    background-size: 400% 400%;
    animation: gradMove 7s ease infinite, fadeUp .8s ease both;
    border-radius: 26px; padding: 44px 32px; text-align: center;
    margin-bottom: 22px;
    box-shadow: 0 12px 50px rgba(124,58,237,.5), 0 0 80px rgba(168,85,247,.2);
    position: relative; overflow: hidden;
    border: 1px solid rgba(167,139,250,.3);
}
.hero::before {
    content:''; position:absolute; top:-60%; left:-60%;
    width:220%; height:220%;
    background: radial-gradient(circle,rgba(255,255,255,.1) 0%,transparent 65%);
    animation: spin 10s linear infinite;
}
.hero h1 {
    font-family:'Righteous',cursive !important; color:#FFFFFF !important;
    font-size:3rem; margin:0;
    text-shadow: 0 0 30px rgba(216,180,254,.8), 0 2px 10px rgba(0,0,0,.4);
    letter-spacing:3px;
}
.hero p { font-family:'Dancing Script',cursive !important; color:#E9D5FF !important; font-size:1.3rem; margin-top:8px; }

/* CARDS */
.card {
    background: linear-gradient(135deg,rgba(45,27,105,.75),rgba(30,15,70,.85));
    border-radius: 22px; padding: 24px 26px; margin: 12px 0;
    box-shadow: 0 6px 30px rgba(0,0,0,.4), inset 0 1px 0 rgba(167,139,250,.2);
    border: 1px solid rgba(167,139,250,.25);
    position: relative; overflow: hidden;
    animation: fadeUp .55s ease both;
    backdrop-filter: blur(10px);
}
.card::after {
    content:''; position:absolute; top:0; right:0;
    width:120px; height:120px;
    background: radial-gradient(circle,rgba(167,139,250,.15) 0%,transparent 70%);
    border-radius:0 22px 0 0;
}

/* LOGIN */
.login-box {
    background: linear-gradient(135deg,rgba(45,27,105,.9),rgba(26,10,60,.95));
    border-radius: 28px; padding: 44px 40px; max-width: 460px; margin: auto;
    box-shadow: 0 20px 60px rgba(0,0,0,.6), 0 0 40px rgba(124,58,237,.3);
    border: 1.5px solid rgba(167,139,250,.35);
    animation: bounceIn .75s ease both; backdrop-filter: blur(16px);
}
.login-box h2 { font-family:'Dancing Script',cursive !important; color:#E9D5FF !important; font-size:2.2rem; text-align:center; margin-bottom:4px; }
.login-subtitle { text-align:center; color:#C4B5FD !important; font-style:italic; font-size:.95rem; margin-bottom:22px; }

.google-btn {
    display:flex; align-items:center; justify-content:center; gap:12px;
    background: rgba(255,255,255,.95); border: 2px solid #fff;
    border-radius:50px; padding:13px 24px;
    font-family:'Space Grotesk',sans-serif !important;
    font-weight:700; font-size:15px;
    color:#1A1A1A !important; cursor:pointer; width:100%;
    margin:0 0 14px 0;
    box-shadow:0 4px 15px rgba(0,0,0,.3);
    text-decoration:none; transition:all .25s;
}
.google-btn:hover { transform:scale(1.02); box-shadow:0 6px 20px rgba(0,0,0,.4); }

.divider { text-align:center; color:#9F7AEA !important; font-size:.85rem; margin:12px 0; position:relative; }
.divider::before,.divider::after { content:''; position:absolute; top:50%; width:36%; height:1px; background:rgba(167,139,250,.3); }
.divider::before{left:0} .divider::after{right:0}

/* SECTION TITLES */
.sec-title {
    font-family:'Space Grotesk',sans-serif !important;
    font-size:1.1rem; font-weight:700; font-style:italic;
    color:#CCF900 !important; margin-bottom:10px;
    display:flex; align-items:center; gap:8px;
}

/* BUTTONS */
.stButton>button {
    background: linear-gradient(135deg,#7C3AED,#A855F7) !important;
    color:#FFFFFF !important; border-radius:50px !important;
    padding:13px 32px !important; font-size:16px !important;
    font-weight:800 !important; font-family:'Space Grotesk',sans-serif !important;
    border: 1px solid rgba(216,180,254,.3) !important; width:100%;
    letter-spacing:.5px; animation: glow 2.4s ease-in-out infinite;
    transition:all .3s ease !important;
    box-shadow: 0 4px 20px rgba(124,58,237,.4) !important;
}
.stButton>button:hover { transform:scale(1.04) !important; background:linear-gradient(135deg,#6D28D9,#9333EA) !important; }

/* BACK BUTTON */
.back-btn>button {
    background: transparent !important;
    border: 1.5px solid rgba(167,139,250,.4) !important;
    color:#C4B5FD !important;
    font-size:14px !important; font-weight:600 !important;
    padding:8px 20px !important;
    border-radius:50px !important;
    animation: none !important;
    box-shadow: none !important;
    width:auto !important;
}
.back-btn>button:hover { background:rgba(167,139,250,.15) !important; }

/* NAVBAR */
.navbar {
    display:flex; align-items:center; justify-content:space-between;
    background: rgba(30,15,70,.85);
    border-radius:16px; padding:10px 20px; margin-bottom:18px;
    backdrop-filter:blur(16px);
    box-shadow:0 4px 20px rgba(0,0,0,.4);
    border:1px solid rgba(167,139,250,.25);
    position:sticky; top:0; z-index:999;
}
.navbar-brand { font-family:'Righteous',cursive !important; color:#E9D5FF !important; font-size:1.2rem; text-shadow:0 0 10px rgba(216,180,254,.5); }
.navbar-links { display:flex; gap:8px; }
.navbar-link {
    color:#C4B5FD !important; font-size:.85rem; font-weight:600;
    padding:6px 14px; border-radius:50px;
    background:rgba(167,139,250,.12);
    border:1px solid rgba(167,139,250,.2);
    cursor:pointer; transition:all .2s; text-decoration:none;
    font-family:'Space Grotesk',sans-serif;
}
.navbar-link:hover { background:rgba(167,139,250,.3); color:#E9D5FF !important; }

/* USER AVATAR */
.user-avatar {
    display:flex; align-items:center; gap:10px;
    background:rgba(167,139,250,.15); border-radius:50px;
    padding:6px 14px;
    border:1px solid rgba(167,139,250,.3);
}
.user-avatar img { width:28px; height:28px; border-radius:50%; }
.user-avatar span { font-size:.85rem; color:#E9D5FF; font-family:'Space Grotesk',sans-serif; font-weight:600; }

/* BUDDY CHECKBOX */
.buddy-grid { display:flex; flex-wrap:wrap; gap:12px; justify-content:center; margin:16px 0; }
.buddy-item {
    background:linear-gradient(135deg,rgba(45,27,105,.8),rgba(74,29,150,.6));
    border-radius:20px; padding:16px 20px;
    display:flex; align-items:center; gap:12px;
    cursor:pointer; border:2px solid rgba(167,139,250,.2);
    transition:all .3s ease; min-width:130px;
    box-shadow:0 4px 14px rgba(0,0,0,.3);
}
.buddy-item:hover { border-color:#A78BFA; transform:translateY(-4px); box-shadow:0 8px 24px rgba(124,58,237,.4); }
.buddy-item-sel { border-color:#CCF900 !important; background:linear-gradient(135deg,rgba(74,29,150,.9),rgba(109,40,217,.8)) !important; box-shadow:0 0 18px rgba(204,249,0,.3) !important; }
.buddy-emoji-big { font-size:2.5rem; animation:float 3s ease-in-out infinite; }
.buddy-name { font-family:'Space Grotesk',sans-serif; font-weight:600; color:#E9D5FF; font-size:.9rem; }

/* WELCOME */
.welcome-big {
    background:linear-gradient(135deg,#2D1B69 0%,#4C1D95 50%,#3B0764 100%);
    border-radius:28px; padding:48px 32px; text-align:center;
    box-shadow:0 16px 50px rgba(0,0,0,.5), 0 0 60px rgba(124,58,237,.3);
    border:1px solid rgba(167,139,250,.3); animation:bounceIn .85s ease both;
}
.welcome-big .buddy { font-size:6rem; animation:float 2.6s ease-in-out infinite; display:block; }
.welcome-big h1 { font-family:'Righteous',cursive !important; color:#E9D5FF !important; font-size:2.7rem; margin:12px 0 8px; text-shadow:0 0 20px rgba(216,180,254,.6); }
.welcome-big p { color:#C4B5FD !important; font-size:1.05rem; line-height:1.85; }

/* QUOTE */
.quote-fixed {
    position:fixed; bottom:22px; right:22px; max-width:265px; z-index:1000;
    background:linear-gradient(135deg,rgba(45,27,105,.95),rgba(74,29,150,.9));
    border-radius:18px; padding:16px 18px;
    box-shadow:0 8px 30px rgba(0,0,0,.4), 0 0 20px rgba(124,58,237,.3);
    border-left:4px solid #CCF900; border-top:1px solid rgba(167,139,250,.3);
    animation:float 4.5s ease-in-out infinite; backdrop-filter:blur(12px);
}
.quote-fixed p { font-family:'Dancing Script',cursive !important; font-size:1rem; color:#E9D5FF !important; margin:0 0 5px; line-height:1.5; }
.quote-fixed span { font-size:.75rem; color:#CCF900 !important; font-style:italic; }

/* YOUTUBE */
.yt-card {
    background:linear-gradient(135deg,rgba(45,27,105,.8),rgba(30,15,70,.9));
    border-radius:18px; overflow:hidden;
    box-shadow:0 5px 22px rgba(0,0,0,.4);
    border:1px solid rgba(167,139,250,.2); border-top:4px solid #A855F7;
    transition:transform .3s ease; animation:popIn .5s ease both; margin-bottom:12px;
}
.yt-card:hover { transform:translateY(-8px) scale(1.02); box-shadow:0 12px 35px rgba(124,58,237,.4); }
.yt-card img { width:100%; display:block; }
.yt-body { padding:10px 12px; }
.yt-title { font-family:'Space Grotesk',sans-serif !important; font-weight:600; font-size:.84rem; color:#E9D5FF !important; margin:0 0 4px; }
.yt-ch { font-size:.76rem; color:#A78BFA !important; }

/* DOTS */
.dots { display:flex; justify-content:center; gap:8px; margin:10px 0 20px; }
.dot  { width:10px; height:10px; border-radius:50%; background:rgba(167,139,250,.25); }
.dot-on { width:28px; height:10px; border-radius:5px; background:linear-gradient(90deg,#7C3AED,#CCF900); }

/* INPUTS */
div[data-testid="stTextInput"] input {
    border-radius:14px !important; border:2px solid rgba(167,139,250,.35) !important;
    padding:13px 18px !important; font-family:'Nunito',sans-serif !important;
    font-size:1rem !important; background:rgba(45,27,105,.5) !important; color:#E9D5FF !important;
}
div[data-testid="stTextInput"] input::placeholder { color:#9F7AEA !important; }
div[data-testid="stTextInput"] input:focus { border-color:#A78BFA !important; box-shadow:0 0 0 3px rgba(167,139,250,.2) !important; }
.stSelectbox>div>div { border-radius:14px !important; border:2px solid rgba(167,139,250,.35) !important; background:rgba(45,27,105,.5) !important; color:#E9D5FF !important; }
div[data-testid="stChatMessage"] { background:rgba(45,27,105,.5) !important; border-radius:16px !important; border:1px solid rgba(167,139,250,.2) !important; margin:8px 0 !important; }
.stCheckbox label { color:#E9D5FF !important; font-family:'Nunito',sans-serif !important; }
.streamlit-expanderHeader { background:rgba(45,27,105,.5) !important; border-radius:12px !important; color:#E9D5FF !important; font-family:'Space Grotesk',sans-serif !important; }
div[data-testid="stVerticalBlock"] > div:empty { display:none !important; }
.element-container:empty { display:none !important; }

/* FOOTER */
.footer { text-align:center; font-family:'Dancing Script',cursive !important; color:#9F7AEA !important; font-size:1rem; margin-top:40px; padding:18px; }
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────
defaults = {
    "page": "login", "user_name": "", "user_email": "",
    "user_picture": "", "buddy_emoji": "", "buddy_name": "",
    "subject": "", "topic": "", "messages": [], "lesson_text": "",
    "quote": random.choice(QUOTES)
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Handle Google OAuth callback
query_params = st.query_params
if "code" in query_params and st.session_state.page == "login":
    code = query_params["code"]
    with st.spinner("🔐 Signing you in with Google..."):
        user_info = exchange_code_for_user(code)
    if user_info:
        st.session_state.user_name    = user_info.get("name", "Friend")
        st.session_state.user_email   = user_info.get("email", "")
        st.session_state.user_picture = user_info.get("picture", "")
        st.session_state.page = "name_buddy"
        st.query_params.clear()
        st.rerun()
    else:
        st.error("❌ Google sign-in failed. Please try again.")
        st.query_params.clear()

def footer():
    st.markdown('<div class="footer">Made with ❤️ by EchoLearn &nbsp;|&nbsp; Powered by Gemini AI &amp; Murf AI 🤖</div>', unsafe_allow_html=True)

def show_navbar(show_links=True):
    name    = st.session_state.get("user_name", "")
    picture = st.session_state.get("user_picture", "")
    page    = st.session_state.get("page", "")

    avatar_html = f'<img src="{picture}"/>' if picture else "👤"
    user_html = f'<div class="user-avatar">{avatar_html}<span>{name}</span></div>' if name else ""

    if show_links and page not in ["login", "name_buddy", "welcome"]:
        st.markdown(f"""
        <div class="navbar">
            <span class="navbar-brand">🎓 EchoLearn</span>
            <div class="navbar-links">
                <span class="navbar-link">📚 Learn</span>
                <span class="navbar-link">🕒 History</span>
            </div>
            {user_html}
        </div>""", unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🔁 New Topic", key="nav_new"):
                st.session_state.page     = "topic"
                st.session_state.messages = []
                st.rerun()
        with c2:
            if st.button("🕒 History", key="nav_hist"):
                st.session_state.page = "history"
                st.rerun()
        with c3:
            if st.button("🚪 Logout", key="nav_logout"):
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()
    else:
        st.markdown(f"""
        <div class="navbar">
            <span class="navbar-brand">🎓 EchoLearn</span>
            {user_html}
        </div>""", unsafe_allow_html=True)

def back_button(to_page, label="← Back"):
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button(label, key=f"back_{to_page}"):
        st.session_state.page = to_page
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════
# PAGE 1 — LOGIN
# ════════════════════════════════════════════════
if st.session_state.page == "login":
    show_navbar(show_links=False)

    st.markdown("""
    <div class="hero">
        <h1>🎓 EchoLearn</h1>
        <p>✨ Your Personal AI Study Companion ✨</p>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("""
    <h2>👋 Welcome!</h2>
    <p class="login-subtitle">Sign in to start your amazing learning journey!</p>
    """, unsafe_allow_html=True)

    auth_url = get_google_auth_url()
    st.markdown(f"""
    <a href="{auth_url}" class="google-btn">
        <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" width="22"/>
        Continue with Google
    </a>
    <p class="divider">or continue as guest</p>
    """, unsafe_allow_html=True)

    guest_name = st.text_input("", placeholder="✏️  Enter your name to continue as guest…", label_visibility="collapsed", key="guest")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🚀 Continue as Guest"):
            if guest_name.strip():
                st.session_state.user_name = guest_name.strip()
                st.session_state.page = "name_buddy"
                st.rerun()
            else:
                st.warning("⚠️ Please enter your name!")

    st.markdown('</div>', unsafe_allow_html=True)
    footer()

# ════════════════════════════════════════════════
# PAGE 2 — BUDDY SELECTION
# ════════════════════════════════════════════════
# ════════════════════════════════════════════════
# PAGE 2 — BUDDY SELECTION
# ════════════════════════════════════════════════
elif st.session_state.page == "name_buddy":
    show_navbar(show_links=False)
    back_button("login")

    st.markdown("""
    <div class="hero page">
        <h1>🌟 Pick Your Buddy!</h1>
        <p>Choose your study companion for this journey!</p>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="dots"><div class="dot-on"></div><div class="dot"></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<p class="sec-title">🐾 Choose your Study Buddy!</p>', unsafe_allow_html=True)
    st.markdown('<p style="color:#C4B5FD;font-style:italic;font-size:.92rem;margin-bottom:16px;">Check one to be your learning companion! 🎉</p>', unsafe_allow_html=True)

    # Buddy selection using radio button styled as cards
    animal_list  = list(ANIMALS.keys())
    animal_names = list(ANIMALS.values())

    # Show as 3 columns with checkboxes
    cols = st.columns(3)
    for idx, (emoji, animal_name) in enumerate(ANIMALS.items()):
        with cols[idx % 3]:
            is_selected = st.session_state.buddy_emoji == emoji
            sel_class   = "buddy-item-sel" if is_selected else ""
            st.markdown(f"""
            <div class="buddy-item {sel_class}" style="justify-content:center;flex-direction:column;text-align:center;">
                <span style="font-size:2.5rem;">{emoji}</span>
                <span class="buddy-name" style="margin-top:6px;">{"✅ " if is_selected else ""}{animal_name}</span>
            </div>""", unsafe_allow_html=True)
            if st.checkbox(
                animal_name,
                value=is_selected,
                key=f"cb_{idx}"
            ):
                if st.session_state.buddy_emoji != emoji:
                    st.session_state.buddy_emoji = emoji
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Buddy name input — always shown if buddy selected
    if st.session_state.buddy_emoji:
        selected_name = ANIMALS.get(st.session_state.buddy_emoji, "buddy")
        st.markdown(f"""
        <div style="text-align:center; margin:16px 0 8px;">
            <span style="font-size:3rem; display:inline-block; animation:float 2s ease-in-out infinite;">
                {st.session_state.buddy_emoji}
            </span>
            <p style="color:#CCF900; font-family:'Space Grotesk',sans-serif; font-weight:700; margin:8px 0;">
                Great choice! Now name your {selected_name}! 🎉
            </p>
        </div>""", unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p class="sec-title">💝 Give your buddy a name!</p>', unsafe_allow_html=True)
        buddy_name_input = st.text_input(
            "",
            value=st.session_state.buddy_name,
            placeholder=f"✏️  What will you call your {selected_name}?",
            label_visibility="collapsed",
            key="buddy_name_field"
        )
        if buddy_name_input.strip():
            st.session_state.buddy_name = buddy_name_input.strip()
        st.markdown('</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("✨ Let's Go!"):
                if not st.session_state.buddy_name.strip():
                    st.warning("⚠️ Please give your buddy a name!")
                else:
                    st.session_state.page = "welcome"
                    st.rerun()
    else:
        st.info("👆 Please select a study buddy above!")

    footer()

# ════════════════════════════════════════════════
# PAGE 3 — WELCOME
# ════════════════════════════════════════════════
elif st.session_state.page == "welcome":
    show_navbar(show_links=False)
    back_button("name_buddy")

    name       = st.session_state.user_name
    buddy      = st.session_state.buddy_emoji
    buddy_name = st.session_state.buddy_name

    st.markdown(f"""
    <div class="welcome-big page">
        <span class="buddy">{buddy}</span>
        <h1>Hey {name}! 🎉</h1>
        <p>
            Welcome to <strong>EchoLearn</strong>!<br>
            <strong>{buddy_name}</strong> is thrilled to learn with you today! 🌟<br><br>
            🎙️ <em>Speak or type what you want to learn</em><br>
            📚 <em>Get instant AI-powered lessons</em><br>
            📺 <em>Watch curated YouTube videos</em><br>
            🧠 <em>Track your entire learning history</em>
        </p>
    </div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button(f"🚀 Start Learning with {buddy_name}!"):
            st.session_state.page = "subject"
            st.rerun()
    footer()

# ════════════════════════════════════════════════
# PAGE 4 — SUBJECT
# ════════════════════════════════════════════════
elif st.session_state.page == "subject":
    show_navbar()
    back_button("welcome")

    buddy      = st.session_state.buddy_emoji
    buddy_name = st.session_state.buddy_name
    name       = st.session_state.user_name

    st.markdown(f"""
    <div class="hero page">
        <div style="font-size:3rem;animation:float 2.2s ease-in-out infinite;display:inline-block;">{buddy}</div>
        <h1 style="font-size:2.2rem;">📚 What are we studying?</h1>
        <p>{buddy_name} is ready to dive in with you, {name}!</p>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="dots"><div class="dot-on"></div><div class="dot-on"></div><div class="dot"></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="card page">', unsafe_allow_html=True)
    st.markdown('<p class="sec-title">📖 Pick a subject or type your own!</p>', unsafe_allow_html=True)

    presets = ["Math ➗","Science 🔬","History 🏛️","Programming 💻",
               "Biology 🧬","Physics ⚡","Chemistry 🧪",
               "English 📝","Economics 📈","General Knowledge 🌍"]

    choice = st.selectbox("", ["✏️ Type my own subject…"] + presets, label_visibility="collapsed")
    subject = ""
    if choice == "✏️ Type my own subject…":
        subject = st.text_input("", placeholder="e.g. Astronomy, Music Theory, Psychology…", label_visibility="collapsed", key="cs")
    else:
        subject = choice
    st.markdown('</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("✨ Next Step!"):
            if subject and subject != "✏️ Type my own subject…":
                st.session_state.subject = subject
                st.session_state.page    = "topic"
                st.rerun()
            else:
                st.warning("⚠️ Please select or type a subject!")
    footer()

# ════════════════════════════════════════════════
# PAGE 5 — TOPIC + SPEECH TO TEXT
# ════════════════════════════════════════════════
elif st.session_state.page == "topic":
    show_navbar()
    back_button("subject")

    buddy      = st.session_state.buddy_emoji
    buddy_name = st.session_state.buddy_name
    subject    = st.session_state.subject
    name       = st.session_state.user_name

    st.markdown(f"""
    <div class="hero page">
        <div style="font-size:3rem;animation:float 2.2s ease-in-out infinite;display:inline-block;">{buddy}</div>
        <h1 style="font-size:2.1rem;">🎯 What do you want to learn?</h1>
        <p>Tell {buddy_name} what to explore in <strong>{subject}</strong>!</p>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="dots"><div class="dot-on"></div><div class="dot-on"></div><div class="dot-on"></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="card page">', unsafe_allow_html=True)
    st.markdown('<p class="sec-title">✏️ Type your topic:</p>', unsafe_allow_html=True)
    typed = st.text_input("", placeholder="e.g. Photosynthesis, Black Holes, Machine Learning…", label_visibility="collapsed", key="tt")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card page">', unsafe_allow_html=True)
    st.markdown('<p class="sec-title">🎙️ Or speak your topic:</p>', unsafe_allow_html=True)
    st.markdown('<p style="color:#C4B5FD;font-style:italic;font-size:.9rem;margin-bottom:10px;">Click the mic and speak — we\'ll transcribe it instantly!</p>', unsafe_allow_html=True)

    audio = mic_recorder(
        start_prompt="🎙️ Click to Speak",
        stop_prompt="⏹️ Stop Recording",
        key="mic_t"
    )

    voice_topic = ""
    if audio and audio.get("bytes"):
        with st.spinner("🎙️ Listening..."):
            recognizer = sr.Recognizer()
            recognizer.energy_threshold        = 300
            recognizer.pause_threshold         = 0.8
            recognizer.dynamic_energy_threshold = True
            try:
                audio_data  = sr.AudioData(audio["bytes"], audio["sample_rate"], 2)
                voice_topic = recognizer.recognize_google(audio_data, language="en-US")
                if voice_topic:
                    st.success(f"🎙️ Got it: **{voice_topic}**")
            except sr.UnknownValueError:
                st.info("🎙️ Didn't catch that — please try again or type below!")
            except sr.RequestError:
                st.info("🎙️ Speech service temporarily unavailable — please type below!")
            except Exception:
                st.info("🎙️ Please type your topic below!")
    st.markdown('</div>', unsafe_allow_html=True)

    final_topic = voice_topic if voice_topic else typed

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🚀 Start Learning!"):
            if final_topic.strip():
                st.session_state.topic       = final_topic.strip()
                st.session_state.messages    = []
                st.session_state.lesson_text = ""
                st.session_state.page        = "results"
                st.rerun()
            else:
                st.warning("⚠️ Please type or speak a topic!")
    footer()

# ════════════════════════════════════════════════
# PAGE 6 — RESULTS
# ════════════════════════════════════════════════
elif st.session_state.page == "results":
    show_navbar()

    name       = st.session_state.user_name
    buddy      = st.session_state.buddy_emoji
    buddy_name = st.session_state.buddy_name
    subject    = st.session_state.subject
    topic      = st.session_state.topic
    q          = st.session_state.quote

    st.markdown(f"""
    <div class="quote-fixed">
        <p>💬 "{q['quote']}"</p>
        <span>— {q['author']}</span>
    </div>""", unsafe_allow_html=True)

    back_button("topic")

    if not st.session_state.messages:
        with st.spinner(f"✨ {buddy_name} is preparing your lesson on **{topic}**…"):
            prompt = f"""You are EchoLearn, a brilliant and friendly AI study companion.
Student: {name} | Subject: {subject} | Topic: {topic}

Provide a perfectly structured lesson:

📖 **Simple Explanation**
2-3 clear easy sentences.

🔑 **Key Points**
- Point 1
- Point 2
- Point 3

🌍 **Real Life Example**
Something {name} can relate to daily.

💡 **Fun Fact**
One surprising memorable fact.

📝 **Quick Summary**
One sentence recap.

Be warm and encouraging. Use emojis. Address {name} once!"""
            try:
                response = ai_model.generate_content(prompt)
                reply    = response.text
                st.session_state.lesson_text = reply
                st.session_state.messages    = [{"role": "assistant", "content": reply}]
                save_to_history(subject, topic, reply)
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    if st.session_state.messages:
        st.markdown('<div class="card page">', unsafe_allow_html=True)
        st.markdown(f'<p class="sec-title">📖 Your Lesson — {topic}</p>', unsafe_allow_html=True)
        st.chat_message("assistant").write(st.session_state.messages[0]["content"])
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card page">', unsafe_allow_html=True)
        st.markdown('<p class="sec-title">🔊 Listen to Your Lesson</p>', unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca:
            if st.button("🎙️ Play with Murf AI"):
                with st.spinner("🔊 Generating voice…"):
                    audio_url = murf_audio(st.session_state.lesson_text)
                    if audio_url:
                        st.audio(audio_url)
                    else:
                        clean = st.session_state.lesson_text.replace("'","").replace('"',"")[:600]
                        st.components.v1.html(f"""
                        <script>
                        var u=new SpeechSynthesisUtterance('{clean}');
                        u.rate=0.9; u.pitch=1.1;
                        window.speechSynthesis.speak(u);
                        </script>""", height=0)
                        st.info("🔊 Playing via browser voice!")
        with cb:
            if st.button("⏹️ Stop Audio"):
                st.components.v1.html("<script>window.speechSynthesis.cancel();</script>", height=0)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.topic:
        st.markdown('<div class="card page">', unsafe_allow_html=True)
        st.markdown('<p class="sec-title">📺 Watch Related YouTube Videos</p>', unsafe_allow_html=True)
        show_yt = st.checkbox("🎬 Show YouTube videos!", value=True)
        if show_yt:
            with st.spinner("🎬 Fetching videos…"):
                videos = get_youtube_videos(f"{topic} {subject} explained")
            if videos:
                cols = st.columns(3)
                for idx, video in enumerate(videos):
                    vid_id  = video["id"]["videoId"]
                    title   = video["snippet"]["title"]
                    thumb   = video["snippet"]["thumbnails"]["medium"]["url"]
                    channel = video["snippet"]["channelTitle"]
                    url     = f"https://www.youtube.com/watch?v={vid_id}"
                    with cols[idx % 3]:
                        st.markdown(f"""
                        <a href="{url}" target="_blank" style="text-decoration:none;">
                            <div class="yt-card">
                                <img src="{thumb}"/>
                                <div class="yt-body">
                                    <p class="yt-title">{title[:55]}…</p>
                                    <p class="yt-ch">📺 {channel}</p>
                                </div>
                            </div>
                        </a>""", unsafe_allow_html=True)
            else:
                encoded = urllib.parse.quote(f"{topic} {subject}")
                st.markdown(f'🔴 <a href="https://www.youtube.com/results?search_query={encoded}" target="_blank" style="color:#A78BFA;">Search YouTube for <strong>{topic}</strong></a>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.messages:
        st.markdown('<div class="card page">', unsafe_allow_html=True)
        st.markdown('<p class="sec-title">💬 Ask a Follow-Up Question</p>', unsafe_allow_html=True)
        user_input = st.chat_input("Ask anything about this topic…")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            try:
                r     = ai_model.generate_content(f"You are EchoLearn. Student:{name}. Subject:{subject}. Topic:{topic}. Answer simply in max 4 sentences: {user_input}")
                reply = r.text
                st.session_state.messages.append({"role": "assistant", "content": reply})
                st.chat_message("user").write(user_input)
                st.chat_message("assistant").write(reply)
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
        st.markdown('</div>', unsafe_allow_html=True)

    footer()

# ════════════════════════════════════════════════
# PAGE 7 — HISTORY
# ════════════════════════════════════════════════
elif st.session_state.page == "history":
    show_navbar()
    back_button("results")

    name  = st.session_state.user_name
    buddy = st.session_state.buddy_emoji

    st.markdown(f"""
    <div class="hero page">
        <div style="font-size:3rem;">{buddy}</div>
        <h1 style="font-size:2rem;">🕒 Your Learning History</h1>
        <p>Everything you've learned so far, {name}! 🌟</p>
    </div>""", unsafe_allow_html=True)

    history = load_history()
    if not history:
        st.markdown("""
        <div class="card" style="text-align:center;">
            <p style="font-size:3rem;">📭</p>
            <p style="font-family:'Space Grotesk',sans-serif;color:#C4B5FD;font-style:italic;">
                No lessons yet! Go learn something amazing! 🚀
            </p>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f'<p style="color:#C4B5FD;font-style:italic;margin-bottom:10px;">📚 {len(history)} lessons completed!</p>', unsafe_allow_html=True)
        for item in history:
            with st.expander(f"📖 {item['subject']} — {item['topic']} | 🕒 {item['date']}"):
                st.write(item["lesson"])
    footer()