import streamlit as st
import google.generativeai as genai
import os, json, requests, random, tempfile
import urllib.parse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY")
YOUTUBE_API_KEY      = os.getenv("YOUTUBE_API_KEY")
MURF_API_KEY         = os.getenv("MURF_API_KEY")
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

REDIRECT_URI     = "http://localhost:8501"
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

ANIMALS      = ["🦒","🦁","🐼","🦜","🐯","🦆","🦉","🐶","🐱"]
ANIMAL_NAMES = ["JACK","LIO","COCO","RUBY","TACO","BEN","MILO","MAX","BELLA"]

HISTORY_FILE = "lesson_history.json"
NOTES_FILE   = "notes.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE,"r") as f: return json.load(f)
    return []

def save_to_history(subject, topic, lesson):
    h = load_history()
    h.insert(0,{"subject":subject,"topic":topic,"lesson":lesson,"date":datetime.now().strftime("%d %b %Y, %I:%M %p")})
    with open(HISTORY_FILE,"w") as f: json.dump(h[:20],f)

def load_notes():
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE,"r") as f: return json.load(f)
    return []

def save_note(subject, topic, note):
    notes = load_notes()
    notes.insert(0,{"subject":subject,"topic":topic,"note":note,"date":datetime.now().strftime("%d %b %Y, %I:%M %p")})
    with open(NOTES_FILE,"w") as f: json.dump(notes[:50],f)

def get_youtube_videos(query):
    try:
        from googleapiclient.discovery import build
        yt  = build("youtube","v3",developerKey=YOUTUBE_API_KEY)
        res = yt.search().list(q=query,part="snippet",maxResults=3,type="video").execute()
        return res.get("items",[])
    except: return []

def murf_audio(text):
    try:
        r = requests.post(
            "https://api.murf.ai/v1/speech/generate",
            headers={"Content-Type":"application/json","api-key":MURF_API_KEY},
            json={"voiceId":"en-US-natalie","style":"Conversational","text":text[:3000],"modelVersion":"GEN2"},
            timeout=30)
        if r.status_code==200: return r.json().get("audioFile")
    except: pass
    return None

def transcribe_audio(audio_bytes):
    try:
        import whisper
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        model  = whisper.load_model("base")
        result = model.transcribe(tmp_path)
        os.unlink(tmp_path)
        return result.get("text","").strip()
    except: return ""

def get_google_auth_url():
    params = {"client_id":GOOGLE_CLIENT_ID,"redirect_uri":REDIRECT_URI,
              "response_type":"code","scope":"openid email profile",
              "access_type":"offline","prompt":"select_account"}
    return GOOGLE_AUTH_URL+"?"+urllib.parse.urlencode(params)

def exchange_code_for_user(code):
    try:
        t  = requests.post(GOOGLE_TOKEN_URL,data={"code":code,"client_id":GOOGLE_CLIENT_ID,
             "client_secret":GOOGLE_CLIENT_SECRET,"redirect_uri":REDIRECT_URI,
             "grant_type":"authorization_code"}).json()
        at = t.get("access_token")
        if not at: return None
        return requests.get(GOOGLE_USER_URL,headers={"Authorization":f"Bearer {at}"}).json()
    except: return None

st.set_page_config(page_title="EchoLearn 🎓", page_icon="🎓", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Outfit:wght@400;500;600;700;800&display=swap');

/* ── BASE ── */
html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif !important;
    background: #000D1A !important;
    min-height: 100vh;
    color: #E0F7F4 !important;
}
.block-container {
    background: transparent !important;
    padding-top: 0.5rem !important;
    max-width: 780px !important;
}

/* ── OCEAN GREEN + DEEP BLUE ANIMATED BACKGROUND ── */
.stApp::before {
    content: '';
    position: fixed; inset: 0; z-index: -1;
    background:
        radial-gradient(ellipse at 0% 0%,   rgba(0,128,128,0.5)  0%, transparent 55%),
        radial-gradient(ellipse at 100% 0%,  rgba(0,50,180,0.55)  0%, transparent 55%),
        radial-gradient(ellipse at 50% 100%, rgba(0,150,120,0.35) 0%, transparent 60%),
        radial-gradient(ellipse at 100% 100%,rgba(0,30,120,0.5)   0%, transparent 55%),
        radial-gradient(ellipse at 50% 50%,  rgba(0,80,100,0.25)  0%, transparent 70%);
    background-color: #000D1A;
    animation: bgPulse 8s ease-in-out infinite alternate;
}
@keyframes bgPulse {
    0%   { opacity: 0.85; filter: hue-rotate(0deg); }
    50%  { opacity: 1;    filter: hue-rotate(15deg); }
    100% { opacity: 0.9;  filter: hue-rotate(-10deg); }
}

/* ── ANIMATIONS ── */
@keyframes fadeUp  { from{opacity:0;transform:translateY(28px)} to{opacity:1;transform:translateY(0)} }
@keyframes popIn   { from{opacity:0;transform:scale(0.85)} to{opacity:1;transform:scale(1)} }
@keyframes float   { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-12px)} }
@keyframes glow    { 0%,100%{box-shadow:0 0 20px rgba(0,180,160,0.4)} 50%{box-shadow:0 0 50px rgba(0,100,200,0.7)} }
@keyframes shimmer {
    0%   { transform:translateX(-100%) rotate(45deg); }
    100% { transform:translateX(300%) rotate(45deg); }
}
@keyframes borderGlow {
    0%,100% { border-color: rgba(0,150,130,0.5); }
    50%     { border-color: rgba(0,80,200,0.8); }
}

.page { animation: fadeUp .6s ease both; }
.pop  { animation: popIn .5s ease both; }

/* ── HERO ── */
.hero {
    background: linear-gradient(135deg, #001A2E 0%, #003D3D 40%, #001830 70%, #002040 100%);
    border-radius: 22px;
    padding: 44px 32px;
    text-align: center;
    margin-bottom: 18px;
    border: 1px solid rgba(0,180,160,0.3);
    box-shadow: 0 0 60px rgba(0,120,130,0.3), 0 16px 40px rgba(0,0,0,0.5);
    position: relative; overflow: hidden;
    animation: fadeUp .8s ease both, borderGlow 3s ease-in-out infinite;
}
.hero::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%; width: 30px; height: 300%;
    background: rgba(255,255,255,0.04);
    transform: rotate(45deg);
    animation: shimmer 4s ease-in-out infinite;
}
.hero h1 {
    font-family: 'Outfit', sans-serif !important;
    color: #FFFFFF !important;
    font-size: 2.8rem; font-weight: 800;
    margin: 0; letter-spacing: 0.5px;
    text-shadow: 0 0 30px rgba(0,220,200,0.5);
}
.hero p {
    color: rgba(255,255,255,0.8) !important;
    font-size: 1rem; margin-top: 8px; font-weight: 500;
}

/* ── NAVBAR ── */
.navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(0,20,40,0.8);
    backdrop-filter: blur(20px);
    border-radius: 14px;
    padding: 10px 20px;
    margin-bottom: 18px;
    border: 1px solid rgba(0,150,130,0.3);
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    position: sticky; top: 8px; z-index: 999;
    animation: borderGlow 3s ease-in-out infinite;
}
.nav-brand {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 800; font-size: 1.2rem;
    color: #FFFFFF !important;
}
.nav-links { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.nav-btn {
    background: rgba(0,150,130,0.15);
    border: 1px solid rgba(0,150,130,0.3);
    border-radius: 50px;
    padding: 5px 14px;
    color: #7FFFD4 !important;
    font-size: 0.8rem; font-weight: 600;
    cursor: pointer; transition: all .2s;
    text-decoration: none;
}
.nav-btn:hover { background: rgba(0,150,130,0.35); color: #fff !important; }

/* ── CARDS ── */
.card {
    background: rgba(0,30,50,0.6);
    backdrop-filter: blur(16px);
    border-radius: 18px;
    padding: 22px 24px;
    margin: 10px 0;
    border: 1px solid rgba(0,150,130,0.2);
    box-shadow: 0 6px 24px rgba(0,0,0,0.3);
    animation: fadeUp .5s ease both;
    position: relative; overflow: hidden;
}
.card::after {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,220,180,0.4), transparent);
}

/* ── LOGIN BOX ── */
.login-box {
    background: rgba(0,20,40,0.85);
    backdrop-filter: blur(24px);
    border-radius: 24px;
    padding: 40px 36px;
    max-width: 440px; margin: auto;
    border: 1px solid rgba(0,150,130,0.35);
    box-shadow: 0 0 60px rgba(0,100,120,0.3), 0 20px 60px rgba(0,0,0,0.5);
    animation: popIn .7s ease both;
}
.login-box h2 {
    font-family: 'Outfit', sans-serif !important;
    color: #FFFFFF !important;
    font-size: 1.9rem; text-align: center;
    margin-bottom: 4px; font-weight: 700;
}
.login-subtitle {
    text-align: center; color: rgba(255,255,255,0.6) !important;
    font-size: .9rem; margin-bottom: 20px;
}
.google-btn {
    display: flex; align-items: center; justify-content: center; gap: 10px;
    background: rgba(255,255,255,0.95);
    border: none; border-radius: 50px;
    padding: 12px 24px; width: 100%; margin-bottom: 12px;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600; font-size: 14px;
    color: #1A1A1A !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
    text-decoration: none; transition: all .2s; cursor: pointer;
}
.google-btn:hover { transform: scale(1.02); }
.divider {
    text-align: center; color: rgba(255,255,255,0.3) !important;
    font-size: .8rem; margin: 10px 0; position: relative;
}
.divider::before,.divider::after {
    content: ''; position: absolute; top: 50%;
    width: 36%; height: 1px; background: rgba(255,255,255,.15);
}
.divider::before{left:0} .divider::after{right:0}

/* ── SECTION TITLES ── */
.sec-title {
    font-family: 'Outfit', sans-serif !important;
    font-size: 1rem; font-weight: 700;
    color: #00E5CC !important;
    margin-bottom: 10px;
    display: flex; align-items: center; gap: 8px;
}

/* ── BUTTONS ── */
.stButton>button {
    background: linear-gradient(135deg, #005F5F, #003080) !important;
    color: #FFFFFF !important;
    border-radius: 50px !important;
    padding: 12px 28px !important;
    font-size: 15px !important; font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    border: 1px solid rgba(0,200,180,0.3) !important;
    width: 100%;
    box-shadow: 0 4px 20px rgba(0,100,120,0.4) !important;
    transition: all .3s ease !important;
}
.stButton>button:hover {
    transform: scale(1.03) !important;
    box-shadow: 0 8px 30px rgba(0,150,180,0.6) !important;
    background: linear-gradient(135deg, #007A7A, #0040A0) !important;
}

/* ── BACK BUTTON ── */
.back-btn>button {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: rgba(255,255,255,0.7) !important;
    font-size: 13px !important; font-weight: 500 !important;
    padding: 6px 16px !important; border-radius: 50px !important;
    animation: none !important; box-shadow: none !important; width: auto !important;
}
.back-btn>button:hover { background: rgba(255,255,255,0.12) !important; }

/* ── BUDDY SLIDER ── */
.buddy-slider {
    display: flex; align-items: center; justify-content: center;
    gap: 24px; margin: 20px 0;
}
.buddy-main {
    background: linear-gradient(135deg, rgba(0,60,80,0.7), rgba(0,30,100,0.7));
    backdrop-filter: blur(12px);
    border-radius: 22px;
    width: 170px; height: 170px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    border: 2px solid rgba(0,200,180,0.35);
    box-shadow: 0 0 40px rgba(0,150,160,0.3);
    cursor: pointer; transition: all .3s ease;
    animation: float 3s ease-in-out infinite, glow 3s ease-in-out infinite;
}
.buddy-main:hover {
    border-color: #00E5CC;
    box-shadow: 0 0 60px rgba(0,220,200,0.5);
    transform: scale(1.05);
}
.buddy-emoji { font-size: 4.5rem; display: block; }
.buddy-name-label {
    font-family: 'Outfit', sans-serif;
    font-weight: 600; font-size: .9rem;
    color: #00E5CC; margin-top: 6px;
}
.arrow-btn {
    background: rgba(0,100,100,0.3);
    border: 1px solid rgba(0,180,160,0.3);
    border-radius: 50%; width: 44px; height: 44px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem; color: white; transition: all .2s ease;
}
.arrow-btn:hover { background: rgba(0,150,150,0.5); transform: scale(1.1); }

/* ── WELCOME ── */
.welcome-big {
    background: linear-gradient(135deg, rgba(0,60,80,0.6), rgba(0,30,100,0.5));
    backdrop-filter: blur(16px);
    border-radius: 24px; padding: 44px 32px; text-align: center;
    border: 1px solid rgba(0,180,160,0.3);
    box-shadow: 0 0 60px rgba(0,100,120,0.3), 0 16px 40px rgba(0,0,0,0.4);
    animation: popIn .8s ease both;
}
.welcome-big .buddy { font-size: 5.5rem; animation: float 2.5s ease-in-out infinite; display: block; }
.welcome-big h1 {
    font-family: 'Outfit', sans-serif !important;
    color: #FFFFFF !important; font-size: 2.5rem; margin: 12px 0 8px; font-weight: 800;
    text-shadow: 0 0 20px rgba(0,220,200,0.4);
}
.welcome-big p { color: rgba(255,255,255,0.8) !important; font-size: 1rem; line-height: 1.9; }

/* ── NOTEBOOK MODAL ── */
.notebook-modal {
    position: fixed; top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    z-index: 9999; width: 90%; max-width: 500px;
    background: linear-gradient(135deg, #001A2E, #003040);
    border-radius: 22px; padding: 30px;
    border: 1px solid rgba(0,180,160,0.3);
    box-shadow: 0 0 80px rgba(0,100,120,0.5), 0 24px 60px rgba(0,0,0,0.6);
    animation: popIn .4s ease both;
}
.notebook-modal h3 {
    font-family: 'Outfit', sans-serif !important;
    color: #00E5CC !important; font-size: 1.3rem;
    font-weight: 700; margin: 0 0 14px;
}

/* ── QUOTE FIXED ── */
.quote-fixed {
    position: fixed; bottom: 18px; right: 18px;
    max-width: 250px; z-index: 1000;
    background: rgba(0,20,40,0.85);
    backdrop-filter: blur(16px);
    border-radius: 16px; padding: 14px 16px;
    border: 1px solid rgba(0,150,130,0.3);
    border-left: 3px solid #00E5CC;
    box-shadow: 0 8px 30px rgba(0,0,0,0.4);
    animation: float 4s ease-in-out infinite;
}
.quote-fixed p {
    font-size: .85rem; color: #FFFFFF !important;
    margin: 0 0 4px; line-height: 1.5; font-weight: 400;
}
.quote-fixed span { font-size: .72rem; color: #00E5CC !important; }

/* ── YOUTUBE CARDS ── */
.yt-card {
    background: rgba(0,30,50,0.6);
    backdrop-filter: blur(10px);
    border-radius: 14px; overflow: hidden;
    border: 1px solid rgba(0,150,130,0.2);
    border-top: 3px solid #005F7A;
    transition: transform .3s ease;
    animation: popIn .5s ease both; margin-bottom: 10px;
}
.yt-card:hover { transform: translateY(-5px); box-shadow: 0 10px 30px rgba(0,150,160,0.3); }
.yt-card img { width: 100%; display: block; }
.yt-body { padding: 9px 11px; }
.yt-title { font-weight: 600; font-size: .82rem; color: #FFFFFF !important; margin: 0 0 3px; }
.yt-ch { font-size: .74rem; color: rgba(255,255,255,0.5) !important; }

/* ── DOTS ── */
.dots { display: flex; justify-content: center; gap: 6px; margin: 8px 0 18px; }
.dot  { width: 8px; height: 8px; border-radius: 50%; background: rgba(255,255,255,0.15); }
.dot-on { width: 22px; height: 8px; border-radius: 4px; background: linear-gradient(90deg,#005F7A,#00E5CC); }

/* ── QUIZ ── */
.quiz-card {
    background: rgba(0,30,50,0.5);
    border-radius: 14px; padding: 16px 18px; margin: 8px 0;
    border: 1px solid rgba(0,150,130,0.2);
    animation: fadeUp .4s ease both;
}
.quiz-q { font-family: 'Outfit', sans-serif; font-weight: 700; color: #00E5CC !important; font-size: .95rem; margin-bottom: 10px; }

/* ── HISTORY CARD ── */
.hist-card {
    background: rgba(0,30,50,0.5);
    border-radius: 12px; padding: 12px 14px; margin: 6px 0;
    border-left: 3px solid #00E5CC;
}

/* ── INPUTS ── */
div[data-testid="stTextInput"] input {
    border-radius: 10px !important;
    border: 1px solid rgba(0,150,130,0.3) !important;
    padding: 11px 14px !important;
    background: rgba(0,30,50,0.6) !important;
    color: #FFFFFF !important;
    font-family: 'Inter', sans-serif !important;
    font-size: .95rem !important;
}
div[data-testid="stTextInput"] input::placeholder { color: rgba(255,255,255,0.35) !important; }
div[data-testid="stTextInput"] input:focus { border-color: #00E5CC !important; box-shadow: 0 0 0 2px rgba(0,229,204,0.2) !important; }
.stSelectbox>div>div { border-radius: 10px !important; border: 1px solid rgba(0,150,130,0.3) !important; background: rgba(0,30,50,0.6) !important; color: #FFFFFF !important; }
div[data-testid="stTextArea"] textarea { border-radius: 10px !important; border: 1px solid rgba(0,150,130,0.3) !important; background: rgba(0,30,50,0.6) !important; color: #FFFFFF !important; font-family: 'Inter', sans-serif !important; }
div[data-testid="stChatMessage"] { background: rgba(0,30,50,0.5) !important; border-radius: 14px !important; border: 1px solid rgba(0,150,130,0.15) !important; }
.stCheckbox label { color: rgba(255,255,255,0.85) !important; font-size: .9rem !important; }
.streamlit-expanderHeader { background: rgba(0,30,50,0.5) !important; border-radius: 10px !important; color: #FFFFFF !important; }
div[data-testid="stVerticalBlock"]>div:empty { display: none !important; }
.element-container:empty { display: none !important; }
.stRadio label { color: rgba(255,255,255,0.85) !important; font-size: .9rem !important; }

/* ── FOOTER ── */
.footer {
    text-align: center; color: rgba(255,255,255,0.3) !important;
    font-size: .85rem; margin-top: 36px; padding: 16px;
}
</style>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────
defaults = {
    "page": "login", "user_name": "", "user_email": "",
    "user_picture": "", "buddy_idx": 0, "buddy_emoji": "",
    "subject": "", "topic": "", "messages": [], "lesson_text": "",
    "quiz_questions": [], "quiz_answers": {}, "quiz_submitted": False,
    "show_notebook": False, "note_text": "",
    "quote": random.choice(QUOTES),
    "followup_audio": None
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Handle Google OAuth
query_params = st.query_params
if "code" in query_params and st.session_state.page == "login":
    with st.spinner("Signing you in..."):
        user_info = exchange_code_for_user(query_params["code"])
    if user_info:
        st.session_state.user_name    = user_info.get("name","Friend")
        st.session_state.user_email   = user_info.get("email","")
        st.session_state.user_picture = user_info.get("picture","")
        st.session_state.page = "buddy"
        st.query_params.clear()
        st.rerun()

def footer():
    st.markdown('<div class="footer">Made with ❤️ by EchoLearn &nbsp;|&nbsp; Powered by Gemini AI & Murf AI</div>', unsafe_allow_html=True)

def show_navbar():
    page    = st.session_state.get("page","")
    name    = st.session_state.get("user_name","")
    picture = st.session_state.get("user_picture","")
    if page in ["login","buddy","welcome"]: return

    avatar = f'<img src="{picture}" style="width:26px;height:26px;border-radius:50%;object-fit:cover;"/>' if picture else "👤"

    st.markdown(f"""
    <div class="navbar">
        <span class="nav-brand">🎓 EchoLearn</span>
        <div class="nav-links">
            <span class="nav-btn">📚 Learn</span>
            <span class="nav-btn">🕒 History</span>
            <span class="nav-btn">📓 Notebook</span>
            <span style="display:flex;align-items:center;gap:6px;background:rgba(0,150,130,0.15);border-radius:50px;padding:4px 12px;border:1px solid rgba(0,150,130,0.3);">
                {avatar}
                <span style="font-size:.8rem;color:#7FFFD4;font-weight:600;">{name}</span>
            </span>
        </div>
    </div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("📚 Learn", key="nav_learn"):
            st.session_state.page = "subject"
            st.session_state.messages = []
            st.rerun()
    with c2:
        if st.button("🕒 History", key="nav_hist"):
            st.session_state.page = "history"
            st.rerun()
    with c3:
        if st.button("📓 Notebook", key="nav_note"):
            st.session_state.show_notebook = True
            st.rerun()
    with c4:
        if st.button("🚪 Logout", key="nav_out"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

def back_button(to_page):
    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button("← Back", key=f"back_{to_page}"):
        st.session_state.page = to_page
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def show_notebook_modal():
    if not st.session_state.show_notebook: return
    st.markdown('<div class="notebook-modal pop">', unsafe_allow_html=True)
    st.markdown('<h3>📓 My Notebook</h3>', unsafe_allow_html=True)

    note_input = st.text_area(
        "", value=st.session_state.note_text,
        placeholder="Write your notes here...",
        height=180, label_visibility="collapsed", key="note_area"
    )
    st.session_state.note_text = note_input

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 Save Note", key="save_note"):
            if note_input.strip():
                save_note(st.session_state.get("subject","General"),
                          st.session_state.get("topic","Note"), note_input.strip())
                st.success("Note saved!")
                st.session_state.note_text = ""
    with c2:
        if st.button("✖ Close", key="close_note"):
            st.session_state.show_notebook = False
            st.rerun()

    notes = load_notes()
    if notes:
        st.markdown('<p style="color:#00E5CC;font-weight:600;margin-top:14px;font-size:.9rem;">Recent Notes:</p>', unsafe_allow_html=True)
        for n in notes[:3]:
            st.markdown(f'<div class="hist-card"><p style="color:#FFFFFF;font-size:.83rem;margin:0;">{n["note"][:100]}...</p><p style="color:rgba(255,255,255,.4);font-size:.73rem;margin:3px 0 0;">{n["date"]}</p></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════
# PAGE 1 — LOGIN
# ════════════════════════════════════════════════
if st.session_state.page == "login":
    st.markdown("""
    <div class="hero">
        <h1>🎓 EchoLearn</h1>
        <p>Your Personal AI Study Companion</p>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown("""
    <h2>Welcome!</h2>
    <p class="login-subtitle">Sign in to start your learning journey</p>""", unsafe_allow_html=True)

    auth_url = get_google_auth_url()
    st.markdown(f"""
    <a href="{auth_url}" class="google-btn">
        <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" width="20"/>
        Continue with Google
    </a>
    <p class="divider">or continue as guest</p>""", unsafe_allow_html=True)

    guest = st.text_input("", placeholder="Enter your name to continue as guest", label_visibility="collapsed", key="guest")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🚀 Continue"):
            if guest.strip():
                st.session_state.user_name = guest.strip()
                st.session_state.page = "buddy"
                st.rerun()
            else:
                st.warning("Please enter your name!")
    st.markdown('</div>', unsafe_allow_html=True)
    footer()

# ════════════════════════════════════════════════
# PAGE 2 — BUDDY SLIDER
# ════════════════════════════════════════════════
elif st.session_state.page == "buddy":
    name = st.session_state.user_name
    idx  = st.session_state.buddy_idx

    st.markdown(f"""
    <div class="hero page">
        <h1>🐾 Pick Your Buddy!</h1>
        <p>Hey {name}! Choose your study companion!</p>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="dots"><div class="dot-on"></div><div class="dot"></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<p class="sec-title">Swipe and pick your favourite!</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="text-align:center;color:rgba(255,255,255,.4);font-size:.82rem;margin-bottom:10px;">{idx+1} / {len(ANIMALS)}</p>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="buddy-slider">
        <div class="arrow-btn">←</div>
        <div class="buddy-main">
            <span class="buddy-emoji">{ANIMALS[idx]}</span>
            <span class="buddy-name-label">{ANIMAL_NAMES[idx]}</span>
        </div>
        <div class="arrow-btn">→</div>
    </div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col1:
        if st.button("←", key="prev_buddy"):
            st.session_state.buddy_idx = (idx - 1) % len(ANIMALS)
            st.rerun()
    with col3:
        if st.button("→", key="next_buddy"):
            st.session_state.buddy_idx = (idx + 1) % len(ANIMALS)
            st.rerun()
    with col2:
        if st.button(f"✅ Choose {ANIMAL_NAMES[idx]}!", key="select_buddy"):
            st.session_state.buddy_emoji = ANIMALS[idx]
            st.session_state.page = "welcome"
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    back_button("login")
    footer()

# ════════════════════════════════════════════════
# PAGE 3 — WELCOME
# ════════════════════════════════════════════════
elif st.session_state.page == "welcome":
    name       = st.session_state.user_name
    buddy      = st.session_state.buddy_emoji
    buddy_name = ANIMAL_NAMES[st.session_state.buddy_idx]

    st.markdown(f"""
    <div class="welcome-big page">
        <span class="buddy">{buddy}</span>
        <h1>Hey {name}! 🎉</h1>
        <p>
            Welcome to <strong>EchoLearn</strong>!<br>
            Your buddy <strong>{buddy_name}</strong> is ready to learn with you! 🌟<br><br>
            🎙️ Speak or type what you want to learn<br>
            📚 Get instant AI-powered lessons<br>
            📺 Watch curated YouTube videos<br>
            📝 Take notes and test yourself with quizzes
        </p>
    </div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🚀 Start Learning!"):
            st.session_state.page = "subject"
            st.rerun()
    footer()

# ════════════════════════════════════════════════
# PAGE 4 — SUBJECT
# ════════════════════════════════════════════════
elif st.session_state.page == "subject":
    show_navbar()
    show_notebook_modal()
    back_button("welcome")

    buddy      = st.session_state.buddy_emoji
    buddy_name = ANIMAL_NAMES[st.session_state.buddy_idx]
    name       = st.session_state.user_name

    st.markdown(f"""
    <div class="hero page">
        <div style="font-size:3rem;animation:float 2s ease-in-out infinite;display:inline-block;">{buddy}</div>
        <h1 style="font-size:2rem;">What are we studying?</h1>
        <p>{buddy_name} is ready to dive in with you!</p>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="dots"><div class="dot-on"></div><div class="dot-on"></div><div class="dot"></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="card page">', unsafe_allow_html=True)
    st.markdown('<p class="sec-title">📖 Pick a subject or type your own</p>', unsafe_allow_html=True)

    presets = ["Math ➗","Science 🔬","History 🏛️","Programming 💻",
               "Biology 🧬","Physics ⚡","Chemistry 🧪",
               "English 📝","Economics 📈","General Knowledge 🌍"]

    choice = st.selectbox("", ["✏️ Type my own…"] + presets, label_visibility="collapsed")
    subject = ""
    if choice == "✏️ Type my own…":
        subject = st.text_input("", placeholder="e.g. Astronomy, Music Theory…", label_visibility="collapsed", key="cs")
    else:
        subject = choice
    st.markdown('</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("Next →"):
            if subject and subject != "✏️ Type my own…":
                st.session_state.subject = subject
                st.session_state.page    = "topic"
                st.rerun()
            else:
                st.warning("Please select or type a subject!")
    footer()

# ════════════════════════════════════════════════
# PAGE 5 — TOPIC + SPEECH TO TEXT
# ════════════════════════════════════════════════
elif st.session_state.page == "topic":
    show_navbar()
    show_notebook_modal()
    back_button("subject")

    buddy      = st.session_state.buddy_emoji
    buddy_name = ANIMAL_NAMES[st.session_state.buddy_idx]
    subject    = st.session_state.subject

    st.markdown(f"""
    <div class="hero page">
        <div style="font-size:3rem;animation:float 2s ease-in-out infinite;display:inline-block;">{buddy}</div>
        <h1 style="font-size:2rem;">What do you want to learn?</h1>
        <p>Explore anything in <strong>{subject}</strong>!</p>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="dots"><div class="dot-on"></div><div class="dot-on"></div><div class="dot-on"></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="card page">', unsafe_allow_html=True)
    st.markdown('<p class="sec-title">✏️ Type your topic</p>', unsafe_allow_html=True)
    typed = st.text_input("", placeholder="e.g. Photosynthesis, Black Holes, Machine Learning…", label_visibility="collapsed", key="tt")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card page">', unsafe_allow_html=True)
    st.markdown('<p class="sec-title">🎙️ Or speak your topic</p>', unsafe_allow_html=True)

    voice_topic = ""
    try:
        from audio_recorder_streamlit import audio_recorder
        audio_bytes = audio_recorder(
            text="Click to record",
            recording_color="#00E5CC",
            neutral_color="#005F7A",
            icon_size="2x", key="audio_rec"
        )
        if audio_bytes:
            with st.spinner("Transcribing..."):
                voice_topic = transcribe_audio(audio_bytes)
            if voice_topic:
                st.success(f"Got it: **{voice_topic}**")
            else:
                st.info("Try again or type below.")
    except:
        try:
            from streamlit_mic_recorder import mic_recorder
            import speech_recognition as sr
            audio = mic_recorder(start_prompt="🎙️ Speak", stop_prompt="⏹️ Stop", key="mic_t")
            if audio and audio.get("bytes"):
                with st.spinner("Listening..."):
                    try:
                        rec = sr.Recognizer()
                        rec.energy_threshold = 300
                        rec.dynamic_energy_threshold = True
                        ad = sr.AudioData(audio["bytes"], audio["sample_rate"], 2)
                        voice_topic = rec.recognize_google(ad, language="en-US")
                        if voice_topic:
                            st.success(f"Got it: **{voice_topic}**")
                    except:
                        st.info("Please type your topic below.")
        except:
            st.info("Please type your topic below.")

    st.markdown('</div>', unsafe_allow_html=True)

    final_topic = voice_topic if voice_topic else typed

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🚀 Start Learning!"):
            if final_topic.strip():
                st.session_state.topic          = final_topic.strip()
                st.session_state.messages       = []
                st.session_state.lesson_text    = ""
                st.session_state.quiz_questions = []
                st.session_state.quiz_submitted = False
                st.session_state.page           = "results"
                st.rerun()
            else:
                st.warning("Please type or speak a topic!")
    footer()

# ════════════════════════════════════════════════
# PAGE 6 — RESULTS
# ════════════════════════════════════════════════
elif st.session_state.page == "results":
    show_navbar()
    show_notebook_modal()

    name       = st.session_state.user_name
    buddy      = st.session_state.buddy_emoji
    buddy_name = ANIMAL_NAMES[st.session_state.buddy_idx]
    subject    = st.session_state.subject
    topic      = st.session_state.topic
    q          = st.session_state.quote

    st.markdown(f"""
    <div class="quote-fixed">
        <p>"{q['quote']}"</p>
        <span>— {q['author']}</span>
    </div>""", unsafe_allow_html=True)

    back_button("topic")

    if not st.session_state.messages:
        with st.spinner(f"Preparing your lesson on {topic}..."):
            prompt = f"""You are EchoLearn, a brilliant friendly AI study companion.
Student: {name} | Subject: {subject} | Topic: {topic}

Structure your lesson exactly like this:

📖 **Simple Explanation**
2-3 clear sentences.

🔑 **Key Points**
- Point 1
- Point 2
- Point 3

🌍 **Real Life Example**
One relatable example.

💡 **Fun Fact**
One surprising fact.

📝 **Quick Summary**
One sentence recap.

Be warm and encouraging. Use emojis. Mention {name} once!"""
            try:
                response = ai_model.generate_content(prompt)
                reply    = response.text
                st.session_state.lesson_text = reply
                st.session_state.messages    = [{"role":"assistant","content":reply}]
                save_to_history(subject, topic, reply)
            except Exception as e:
                st.error(f"Error: {str(e)}")

    if st.session_state.messages:
        st.markdown('<div class="card page">', unsafe_allow_html=True)
        st.markdown(f'<p class="sec-title">📖 Your Lesson — {topic}</p>', unsafe_allow_html=True)
        st.chat_message("assistant").write(st.session_state.messages[0]["content"])
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card page">', unsafe_allow_html=True)
        st.markdown('<p class="sec-title">🔊 Listen to Your Lesson</p>', unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca:
            if st.button("▶ Play with Murf AI", key="play_lesson"):
                with st.spinner("Generating voice..."):
                    audio_url = murf_audio(st.session_state.lesson_text)
                    if audio_url:
                        st.audio(audio_url)
                    else:
                        clean = st.session_state.lesson_text.replace("'","").replace('"',"")[:600]
                        st.components.v1.html(f"""<script>
                        var u=new SpeechSynthesisUtterance('{clean}');
                        u.rate=0.9; u.pitch=1.1;
                        window.speechSynthesis.speak(u);
                        </script>""", height=0)
                        st.info("Playing via browser voice!")
        with cb:
            if st.button("⏹ Stop", key="stop_lesson"):
                st.components.v1.html("<script>window.speechSynthesis.cancel();</script>", height=0)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card page">', unsafe_allow_html=True)
        st.markdown('<p class="sec-title">📝 Quick Note</p>', unsafe_allow_html=True)
        quick_note = st.text_area("", placeholder="Jot something from this lesson...", height=75, label_visibility="collapsed", key="qnote")
        if st.button("💾 Save Note", key="save_qnote"):
            if quick_note.strip():
                save_note(subject, topic, quick_note.strip())
                st.success("Note saved!")
            else:
                st.warning("Write something first!")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.topic:
        st.markdown('<div class="card page">', unsafe_allow_html=True)
        st.markdown('<p class="sec-title">📺 Watch on YouTube</p>', unsafe_allow_html=True)
        show_yt = st.checkbox("Show YouTube videos", value=True)
        if show_yt:
            with st.spinner("Fetching videos..."):
                videos = get_youtube_videos(f"{topic} {subject} explained")
            if videos:
                cols = st.columns(3)
                for idx2, video in enumerate(videos):
                    vid_id  = video["id"]["videoId"]
                    title   = video["snippet"]["title"]
                    thumb   = video["snippet"]["thumbnails"]["medium"]["url"]
                    channel = video["snippet"]["channelTitle"]
                    url     = f"https://www.youtube.com/watch?v={vid_id}"
                    with cols[idx2 % 3]:
                        st.markdown(f"""
                        <a href="{url}" target="_blank" style="text-decoration:none;">
                            <div class="yt-card">
                                <img src="{thumb}"/>
                                <div class="yt-body">
                                    <p class="yt-title">{title[:50]}...</p>
                                    <p class="yt-ch">📺 {channel}</p>
                                </div>
                            </div>
                        </a>""", unsafe_allow_html=True)
            else:
                encoded = urllib.parse.quote(f"{topic} {subject}")
                st.markdown(f'<a href="https://www.youtube.com/results?search_query={encoded}" target="_blank" style="color:#00E5CC;">Search YouTube for {topic}</a>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.messages:
        st.markdown('<div class="card page">', unsafe_allow_html=True)
        st.markdown('<p class="sec-title">🧠 Test Yourself</p>', unsafe_allow_html=True)

        if not st.session_state.quiz_questions:
            if st.button("🎯 Generate Quiz"):
                with st.spinner("Creating quiz..."):
                    quiz_prompt = f"""Create exactly 3 multiple choice questions about {topic} in {subject}.
Format EXACTLY like this:
Q1: [question]
A) [option]
B) [option]
C) [option]
D) [option]
Answer: [A/B/C/D]

Q2: [question]
A) [option]
B) [option]
C) [option]
D) [option]
Answer: [A/B/C/D]

Q3: [question]
A) [option]
B) [option]
C) [option]
D) [option]
Answer: [A/B/C/D]"""
                    try:
                        r     = ai_model.generate_content(quiz_prompt)
                        lines = r.text.strip().split("\n")
                        questions = []
                        i = 0
                        while i < len(lines):
                            line = lines[i].strip()
                            if line.startswith("Q") and ":" in line:
                                q_text = line.split(":",1)[1].strip()
                                opts, ans = [], ""
                                i += 1
                                while i < len(lines) and not lines[i].strip().startswith("Q"):
                                    l2 = lines[i].strip()
                                    if l2.startswith(("A)","B)","C)","D)")): opts.append(l2)
                                    elif l2.startswith("Answer:"): ans = l2.split(":",1)[1].strip()
                                    i += 1
                                if q_text and len(opts)==4 and ans:
                                    questions.append({"q":q_text,"opts":opts,"ans":ans})
                            else: i += 1
                        st.session_state.quiz_questions = questions
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        else:
            if not st.session_state.quiz_submitted:
                for qi, qitem in enumerate(st.session_state.quiz_questions):
                    st.markdown(f'<div class="quiz-card"><p class="quiz-q">Q{qi+1}: {qitem["q"]}</p></div>', unsafe_allow_html=True)
                    choice = st.radio("", qitem["opts"], key=f"q_{qi}", label_visibility="collapsed")
                    if choice: st.session_state.quiz_answers[qi] = choice[0]
                if st.button("✅ Submit Quiz"):
                    st.session_state.quiz_submitted = True
                    st.rerun()
            else:
                score = 0
                for qi, qitem in enumerate(st.session_state.quiz_questions):
                    user_ans = st.session_state.quiz_answers.get(qi,"")
                    correct  = qitem["ans"]
                    if user_ans == correct: score += 1
                    icon = "✅" if user_ans == correct else "❌"
                    st.markdown(f"""
                    <div class="quiz-card">
                        <p class="quiz-q">{icon} Q{qi+1}: {qitem["q"]}</p>
                        <p style="color:rgba(255,255,255,.6);font-size:.85rem;">Your answer: {user_ans} | Correct: {correct}</p>
                    </div>""", unsafe_allow_html=True)

                st.markdown(f"""
                <div style="text-align:center;margin:14px 0;">
                    <p style="font-family:'Outfit',sans-serif;font-size:1.4rem;font-weight:800;color:#00E5CC;">
                        {"🏆 Perfect!" if score==3 else "👍 Good job!" if score>=2 else "📚 Keep studying!"} {score}/3
                    </p>
                </div>""", unsafe_allow_html=True)

                if st.button("🔁 Try Again"):
                    st.session_state.quiz_questions = []
                    st.session_state.quiz_answers   = {}
                    st.session_state.quiz_submitted = False
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.messages:
        st.markdown('<div class="card page">', unsafe_allow_html=True)
        st.markdown('<p class="sec-title">💬 Ask a Follow-Up</p>', unsafe_allow_html=True)

        user_input = st.chat_input("Ask anything about this topic...")
        if user_input:
            st.session_state.messages.append({"role":"user","content":user_input})
            try:
                r     = ai_model.generate_content(
                    f"You are EchoLearn. Student:{name}. Subject:{subject}. Topic:{topic}. Answer simply in max 4 sentences: {user_input}"
                )
                reply = r.text
                st.session_state.messages.append({"role":"assistant","content":reply})
                st.session_state.followup_audio = reply
                st.chat_message("user").write(user_input)
                st.chat_message("assistant").write(reply)
            except Exception as e:
                st.error(f"Error: {str(e)}")

        if st.session_state.followup_audio:
            fa, fb = st.columns(2)
            with fa:
                if st.button("▶ Play Answer with Murf AI", key="play_followup"):
                    with st.spinner("Generating voice..."):
                        audio_url = murf_audio(st.session_state.followup_audio)
                        if audio_url:
                            st.audio(audio_url)
                        else:
                            clean = st.session_state.followup_audio.replace("'","").replace('"',"")[:600]
                            st.components.v1.html(f"""<script>
                            var u=new SpeechSynthesisUtterance('{clean}');
                            u.rate=0.9; u.pitch=1.1;
                            window.speechSynthesis.speak(u);
                            </script>""", height=0)
                            st.info("Playing via browser voice!")
            with fb:
                if st.button("⏹ Stop", key="stop_followup"):
                    st.components.v1.html("<script>window.speechSynthesis.cancel();</script>", height=0)

        st.markdown('</div>', unsafe_allow_html=True)
    footer()

# ════════════════════════════════════════════════
# PAGE 7 — HISTORY
# ════════════════════════════════════════════════
elif st.session_state.page == "history":
    show_navbar()
    show_notebook_modal()
    back_button("results")

    name  = st.session_state.user_name
    buddy = st.session_state.buddy_emoji

    st.markdown(f"""
    <div class="hero page">
        <div style="font-size:3rem;">{buddy}</div>
        <h1 style="font-size:2rem;">Learning History</h1>
        <p>Everything you have learned, {name}!</p>
    </div>""", unsafe_allow_html=True)

    history = load_history()
    if not history:
        st.markdown("""
        <div class="card" style="text-align:center;">
            <p style="font-size:3rem;">📭</p>
            <p style="color:rgba(255,255,255,.5);">No lessons yet! Go learn something amazing!</p>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f'<p style="color:rgba(255,255,255,.4);margin-bottom:8px;font-size:.85rem;">📚 {len(history)} lessons completed</p>', unsafe_allow_html=True)
        for item in history:
            with st.expander(f"📖 {item['subject']} — {item['topic']} | {item['date']}"):
                st.write(item["lesson"])

    notes = load_notes()
    if notes:
        st.markdown('<div class="card page">', unsafe_allow_html=True)
        st.markdown('<p class="sec-title">📓 My Notes</p>', unsafe_allow_html=True)
        for n in notes:
            st.markdown(f'<div class="hist-card"><p style="color:#FFFFFF;font-size:.88rem;margin:0;">{n["note"]}</p><p style="color:rgba(255,255,255,.35);font-size:.73rem;margin:3px 0 0;">{n["subject"]} | {n["date"]}</p></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    footer()