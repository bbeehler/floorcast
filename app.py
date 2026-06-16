# app.py (Frictionless Canva-Style Layout)
import streamlit as st
from supabase import create_client, Client
import stripe

# --- 1. PAGE CONFIGURATION ---
# We force the sidebar to collapse initially, and our CSS will hide the toggle button permanently.
st.set_page_config(page_title="FloorCast OS", layout="wide", initial_sidebar_state="collapsed")

# --- CUSTOM ENTERPRISE CSS (Borderless & Floating) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* True Pitch Black Background & Pure White Text */
    .stApp { background-color: #000000; color: #FFFFFF; }
    
    /* ANNIHILATE THE SIDEBAR AND DEFAULT UI */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="collapsedControl"] {display: none !important;}
    section[data-testid="stSidebar"] {display: none !important;}
    
    /* Top Bar & Hero Typography */
    .top-nav { display: flex; justify-content: space-between; padding: 1rem 0; margin-bottom: 2rem; border-bottom: 1px solid #1A1A1A; }
    .hero-greeting {
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        letter-spacing: -0.02em;
        margin-top: 2vh;
        margin-bottom: 0.5rem;
    }
    .hero-sub {
        font-size: 1.2rem;
        color: #AAAAAA;
        text-align: center;
        margin-bottom: 3rem;
        font-weight: 400;
    }

    /* Style the Horizontal Navigation Radio Buttons */
    div.row-widget.stRadio > div {
        display: flex;
        flex-direction: row;
        justify-content: center;
        gap: 10px;
        flex-wrap: wrap;
    }
    /* Floating Bento Cards */
    [data-testid="stVerticalBlock"] > div > div > div > div > div {
        background-color: #080808;
        border: 1px solid #1A1A1A;
        border-radius: 16px;
        padding: 1.5rem;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    [data-testid="stVerticalBlock"] > div > div > div > div > div:hover {
        border-color: #333333;
    }

    /* Primary CTA Buttons */
    div.stButton > button {
        background-color: #FFFFFF;
        color: #000000 !important;
        font-weight: 600;
        border-radius: 24px; /* Pill shape */
        border: none;
        padding: 0.5rem 1.5rem;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        background-color: #A8C7FA;
    }
    
    /* Ghost Buttons (Nav/Logout) */
    .ghost-btn > div > button {
        background-color: transparent;
        color: #FFFFFF !important;
        border: 1px solid #333333;
    }
    .ghost-btn > div > button:hover {
        border: 1px solid #FFFFFF;
        background-color: #111111;
    }

    /* Input Fields (The Central Prompt) */
    .stTextInput input {
        background-color: #111111 !important;
        color: #FFFFFF !important;
        border: 1px solid #333333 !important;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        font-size: 1.1rem;
    }
    .stTextInput input:focus {
        border: 1px solid #FFFFFF !important;
        box-shadow: none !important;
    }
    
    /* Modal / Dialog Cleanup */
    div[role="dialog"] {
        background-color: #0A0A0A !important;
        border: 1px solid #222222 !important;
        border-radius: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE CONNECTION ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error(f"Critical Error: Missing Database Secrets. {e}")
        st.stop()

supabase = init_connection()

# --- 3. SESSION STATE INITIALIZATION ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_profile' not in st.session_state: st.session_state.user_profile = None
if 'active_modules' not in st.session_state: st.session_state.active_modules = []

# --- THE LOGIN MODAL ---
@st.dialog("Secure Client Portal")
def login_modal():
    st.markdown("<p style='color: #AAAAAA; margin-bottom: 1rem;'>Authenticate to access your workspace.</p>", unsafe_allow_html=True)
    with st.form("saas_login_form", clear_on_submit=True, border=False):
        email = st.text_input("Corporate Email", placeholder="manager@casino.com").strip().lower()
        password = st.text_input("Access Token", type="password", placeholder="••••••••")
        st.write("\n")
        if st.form_submit_button("Authenticate & Enter", use_container_width=True):
            try:
                auth_res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if auth_res.user:
                    profile_res = supabase.table("user_profiles").select("*, tenants(property_name, region)").eq("email", email).execute()
                    if profile_res.data:
                        user_data = profile_res.data[0]
                        tenant_id = user_data['tenant_id']
                        sub_res = supabase.table("tenant_subscriptions").select("module_name").eq("tenant_id", tenant_id).eq("status", "active").execute()
                        modules = [sub['module_name'] for sub in sub_res.data] if sub_res.data else []
                        
                        st.session_state.authenticated = True
                        st.session_state.user_profile = user_data
                        st.session_state.active_modules = modules
                        st.rerun()
                    else:
                        st.error("Account created, but no property assigned. Contact Support.")
            except Exception as e:
                st.error("Invalid credentials.")

# ==========================================
# --- 4. LOGGED OUT: PUBLIC MARKETING PAGE ---
# ==========================================
if not st.session_state.authenticated:
    # Top Bar
    c1, c2 = st.columns([6, 1])
    with c1: st.markdown("<h3 style='margin:0;'>🎰 FloorCast AI</h3>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
        if st.button("Client Login", use_container_width=True): login_modal()
        st.markdown('</div>', unsafe_allow_html=True)

    # Central Focus Hero
    st.markdown('<div class="hero-greeting">Predict. Perform. Profit.</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub" style="max-width: 700px; margin: 0 auto 4rem auto;">FloorCast AI consolidates your gaming, marketing, and lodging data to isolate what truly drives revenue.</div>', unsafe_allow_html=True)

    # Floating Bento Pricing
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<h2 style='text-align:center;'>Core</h2><h3 style='text-align:center;'>$299</h3><p style='text-align:center; color:#888;'>/ month</p><br><p style='text-align:center; color:#CCC;'>✔️ Casino Analytics<br>✔️ Marketing Attribution</p>", unsafe_allow_html=True)
        st.write("\n")
        if st.button("Select Core", key="b1", use_container_width=True): st.info("Routing to Stripe...")
    with c2:
        st.markdown("<h2 style='text-align:center; color:#A8C7FA;'>Premium</h2><h3 style='text-align:center; color:#A8C7FA;'>$350</h3><p style='text-align:center; color:#888;'>/ month</p><br><p style='text-align:center; color:#CCC;'>✔️ Core Features<br>✔️ <b>🧠 AI Advisor</b></p>", unsafe_allow_html=True)
        st.write("\n")
        if st.button("Select Premium", key="b2", use_container_width=True): st.info("Routing to Stripe...")
    with c3:
        st.markdown("<h2 style='text-align:center;'>Enterprise</h2><h3 style='text-align:center;'>$999</h3><p style='text-align:center; color:#888;'>/ month</p><br><p style='text-align:center; color:#CCC;'>✔️ All Features<br>✔️ Full Auxiliary Suite</p>", unsafe_allow_html=True)
        st.write("\n")
        if st.button("Select Enterprise", key="b3", use_container_width=True): st.info("Routing to Stripe...")
    st.stop()

# ==========================================
# --- 5. LOGGED IN: THE ACTIVE WORKSPACE ---
# ==========================================
profile = st.session_state.user_profile
prop_name = profile['tenants']['property_name']
role = profile['user_role']

# Clean Top Navigation Bar
nav_c1, nav_c2, nav_c3 = st.columns([1, 4, 1])
with nav_c1:
    st.markdown("<h4 style='margin-top: 10px;'>🎰 FloorCast OS</h4>", unsafe_allow_html=True)
with nav_c3:
    st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
    if st.button(f"Sign Out ({profile['email']})", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# The Central Focus Axis (Greeting & Prompt)
st.markdown(f'<div class="hero-greeting">Good afternoon, {prop_name}.</div>', unsafe_allow_html=True)

_, search_col, _ = st.columns([1, 2, 1])
with search_col:
    # A fake search/prompt bar purely for the UI aesthetic of a centralized design platform
    st.text_input("", placeholder="Ask FloorCast AI to analyze your property data...", label_visibility="collapsed")
    st.write("\n")

# Horizontal Semantic Navigation (Replaces the Sidebar)
st.write("\n")
nav_options = ["🏠 Overview"]
if "ai_advisor" in st.session_state.active_modules: nav_options.append("🧠 AI Advisor")
if "casino_ops" in st.session_state.active_modules: nav_options.append("🎰 Casino")
if "marketing_pro" in st.session_state.active_modules: nav_options.append("📈 Marketing")
if "pr_media" in st.session_state.active_modules: nav_options.append("📢 PR")
if "hotel_rev" in st.session_state.active_modules: nav_options.append("🛏️ Hotel")
if "fnb" in st.session_state.active_modules: nav_options.append("🍽️ F&B")
if "email_ops" in st.session_state.active_modules: nav_options.append("📨 Email")
if role == "Super Admin": nav_options.append("⚙️ Global Admin")

selected_page = st.radio("Workspace Navigation", nav_options, horizontal=True, label_visibility="collapsed")
st.divider()

# --- PAGE ROUTING ---
if selected_page == "🏠 Overview":
    st.markdown("<h3 style='text-align: center; color: #888; font-weight: 400; margin-top: 4vh;'>Select a module from the menu above to begin your analysis.</h3>", unsafe_allow_html=True)
elif selected_page == "⚙️ Global Admin":
    import admin
    admin.render_admin_page(supabase)
elif selected_page == "🎰 Casino":
    import casino
    casino.render_casino_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "📈 Marketing":
    import marketing
    marketing.render_marketing_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "📢 PR":
    import pr
    pr.render_pr_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "📨 Email":
    import email_ops
    email_ops.render_email_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "🛏️ Hotel":
    import hotel
    hotel.render_hotel_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "🍽️ F&B":
    import fnb
    fnb.render_fnb_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "🧠 AI Advisor":
    import ai_advisor
    ai_advisor.render_advisor_module(supabase, profile['tenant_id'], prop_name)
else:
    st.info("Module under construction.")
