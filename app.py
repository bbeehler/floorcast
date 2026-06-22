# app.py (Phase 1: The Gateway & CRM Capture)
import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# =================================================================
# 1. PAGE CONFIGURATION & STYLING
# =================================================================
st.set_page_config(page_title="FloorCast OS", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #FAFAFA; color: #111827; }
    
    /* Hide Default UI */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="collapsedControl"] {display: none !important;}
    section[data-testid="stSidebar"] {display: none !important;}
    
    /* Typography */
    .hero-title { font-size: 4rem; font-weight: 800; text-align: center; letter-spacing: -0.03em; margin-top: 5vh; color: #111827; line-height: 1.1; }
    .hero-sub { font-size: 1.25rem; color: #6B7280; text-align: center; margin-bottom: 3rem; font-weight: 400; max-width: 800px; margin-left: auto; margin-right: auto; }
    
    /* Bento Cards */
    .bento-card { background-color: #FFFFFF; border-radius: 16px; padding: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.03); border: 1px solid #F3F4F6; height: 100%; transition: transform 0.2s ease; }
    .bento-card:hover { transform: translateY(-3px); box-shadow: 0 12px 30px rgba(0,0,0,0.08); }
    
    /* Buttons */
    div.stButton > button { background-color: #111827; color: #FFFFFF !important; font-weight: 600; border-radius: 8px; border: none; padding: 0.6rem 1.5rem; transition: all 0.2s ease; }
    div.stButton > button:hover { background-color: #2563EB; }
    
    /* Ghost Buttons (Nav/Login) */
    .ghost-btn > div > button { background-color: transparent; color: #111827 !important; border: 1px solid #D1D5DB; border-radius: 24px; }
    .ghost-btn > div > button:hover { border: 1px solid #111827; background-color: #FFFFFF; }
    
    /* Inputs */
    .stTextInput input, .stTextArea textarea { background-color: #FFFFFF !important; color: #111827 !important; border: 1px solid #E5E7EB !important; border-radius: 8px; }
    .stTextInput input:focus, .stTextArea textarea:focus { box-shadow: 0 0 0 2px #2563EB !important; border-color: transparent !important; }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 2. DATABASE CONNECTION & SESSION STATE
# =================================================================
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error("Critical System Error: Connection secrets missing.")
        st.stop()

supabase = init_connection()

if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_profile' not in st.session_state: st.session_state.user_profile = None

# =================================================================
# 3. AUTHENTICATION (LOGIN MODAL)
# =================================================================
@st.dialog("Secure Client Portal")
def login_modal():
    st.markdown("<p style='color: #6B7280; margin-bottom: 1.5rem;'>Authenticate to access your workspace.</p>", unsafe_allow_html=True)
    with st.form("client_login_form", border=False):
        email = st.text_input("Corporate Email").strip().lower()
        password = st.text_input("Access Token", type="password")
        if st.form_submit_button("Authenticate & Enter", use_container_width=True):
            try:
                auth_res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if auth_res.user:
                    profile_res = supabase.table("user_profiles").select("*").eq("id", auth_res.user.id).execute()
                    if profile_res.data:
                        st.session_state.authenticated = True
                        st.session_state.user_profile = profile_res.data[0]
                        st.rerun()
                    else:
                        st.error("Profile not found in directory. Contact Support.")
            except Exception as e:
                st.error("Invalid credentials.")

# =================================================================
# 4. LOGGED OUT: MARKETING & LEAD CAPTURE
# =================================================================
if not st.session_state.authenticated:
    
    # --- Top Nav ---
    c1, c2 = st.columns([6, 1])
    with c1: st.markdown("<h3 style='margin:0; color:#111827; padding-top: 10px;'>🎰 FloorCast OS</h3>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
        if st.button("Client Login", use_container_width=True): login_modal()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Hero Section ---
    st.markdown('<div class="hero-title">Predict. Perform. Profit.</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">The ultimate AI-driven operational and marketing attribution engine for enterprise casinos and resorts. Stop guessing what drives floor traffic.</div>', unsafe_allow_html=True)

    # --- Feature Grid ---
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("""
        <div class="bento-card">
            <h3 style='margin-top:0;'>🎰 Total Floor Visibility</h3>
            <p style='color:#6B7280; line-height: 1.6;'>Merge gaming coin-in, F&B covers, and hotel occupancy into one unified, real-time dashboard.</p>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown("""
        <div class="bento-card">
            <h3 style='margin-top:0;'>🎯 Closed-Loop ROI</h3>
            <p style='color:#6B7280; line-height: 1.6;'>Tie your digital ad spend, PR campaigns, and email blasts directly to on-property guest actions.</p>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown("""
        <div class="bento-card">
            <h3 style='margin-top:0;'>🧠 AI Predictability</h3>
            <p style='color:#6B7280; line-height: 1.6;'>Utilize your historical ledger data and localized physics to accurately forecast daily demand.</p>
        </div>
        """, unsafe_allow_html=True)

    st.write("\n\n")
    st.divider()
    st.write("\n\n")

    # --- Lead Capture Form (Replaces Self-Serve Checkout) ---
    st.markdown("<h2 style='text-align:center; margin-bottom: 0.5rem;'>Request Enterprise Access</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color: #6B7280; margin-bottom: 3rem;'>FloorCast OS is deployed via concierge onboarding. Submit your details below to schedule a platform review.</p>", unsafe_allow_html=True)
    
    col_space1, col_form, col_space2 = st.columns([1, 2, 1])
    with col_form:
        with st.form("lead_capture_form", clear_on_submit=True):
            st.markdown('<div class="bento-card">', unsafe_allow_html=True)
            
            f1, f2 = st.columns(2)
            with f1: l_first = st.text_input("First Name *")
            with f2: l_last = st.text_input("Last Name *")
            
            l_email = st.text_input("Corporate Email *")
            
            c1, c2 = st.columns(2)
            with c1: l_company = st.text_input("Company / Property Name *")
            with c2: l_phone = st.text_input("Phone Number")
            
            l_msg = st.text_area("Tell us about your operational goals")
            
            st.write("\n")
            if st.form_submit_button("Submit Request", use_container_width=True):
                if l_first and l_last and l_email and l_company:
                    try:
                        payload = {
                            "first_name": l_first, "last_name": l_last,
                            "email": l_email.strip().lower(), "company_name": l_company,
                            "phone": l_phone, "message": l_msg
                        }
                        supabase.table("leads").insert(payload).execute()
                        st.success("✅ Request received! A FloorCast specialist will contact you shortly.")
                    except Exception as e:
                        st.error(f"Submission failed: {e}")
                else:
                    st.error("Please fill in all required (*) fields.")
            st.markdown('</div>', unsafe_allow_html=True)
            
    st.stop() # Stops execution for logged-out users

# =================================================================
# 5. LOGGED IN: THE WORKSPACE ROUTER
# =================================================================
profile = st.session_state.user_profile
global_role = profile.get('global_role', 'User')

# Temporary Navigation Placeholder to prove login works
st.sidebar.markdown(f"**User:** {profile.get('first_name', 'User')}")
st.sidebar.caption(f"Global Role: {global_role}")

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()

st.title(f"Welcome back, {profile.get('first_name', 'User')}.")
st.info("The Logged-In Workspace router will be built here in Phase 2.")
