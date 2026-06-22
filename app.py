import streamlit as st
import public_home, command_center, setup_wizard, dashboard

# =================================================================
# 1. PAGE CONFIGURATION & GLOBAL STYLES
# =================================================================
st.set_page_config(page_title="FloorCast OS", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #FAFAFA; color: #111827; }
    #MainMenu, header, footer, [data-testid="collapsedControl"], section[data-testid="stSidebar"] {display: none !important;}
    
    .hero-title { font-size: 4rem; font-weight: 800; text-align: center; letter-spacing: -0.03em; margin-top: 5vh; color: #111827; line-height: 1.1; }
    .hero-sub { font-size: 1.25rem; color: #6B7280; text-align: center; margin-bottom: 3rem; font-weight: 400; max-width: 800px; margin-left: auto; margin-right: auto; }
    .bento-card { background-color: #FFFFFF; border-radius: 16px; padding: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.03); border: 1px solid #F3F4F6; height: 100%; transition: transform 0.2s ease; }
    .bento-card:hover { transform: translateY(-3px); box-shadow: 0 12px 30px rgba(0,0,0,0.08); }
    div.stButton > button { background-color: #111827; color: #FFFFFF !important; font-weight: 600; border-radius: 8px; border: none; padding: 0.6rem 1.5rem; transition: all 0.2s ease; }
    div.stButton > button:hover { background-color: #2563EB; }
    .ghost-btn > div > button { background-color: transparent; color: #111827 !important; border: 1px solid #D1D5DB; border-radius: 24px; }
    .ghost-btn > div > button:hover { border: 1px solid #111827; background-color: #FFFFFF; }
    .stTextInput input, .stTextArea textarea { background-color: #FFFFFF !important; color: #111827 !important; border: 1px solid #E5E7EB !important; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 2. SESSION STATE INIT
# =================================================================
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_profile' not in st.session_state: st.session_state.user_profile = None

# =================================================================
# 3. THE WORKSPACE ROUTER
# =================================================================
if not st.session_state.authenticated:
    public_home.render()

else:
    role = st.session_state.user_profile.get('global_role')
    setup_complete = st.session_state.user_profile.get('setup_complete', False)
    
    if role == 'Super Admin':
        command_center.render()
        
    elif role in ['Company Admin', 'Property Admin', 'User']:
        if not setup_complete:
            setup_wizard.render()
        else:
            # THE MAGIC HAPPENS HERE:
            dashboard.render()
