# app.py (Light Mode Enterprise Canvas & Revenue Engine)
import streamlit as st
from supabase import create_client, Client
import stripe

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="FloorCast OS", layout="wide", initial_sidebar_state="collapsed")

# --- CUSTOM ENTERPRISE CSS (Light Mode & Floating) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Clean White Background & Charcoal Text */
    .stApp { background-color: #FFFFFF; color: #111827; }
    
    /* ANNIHILATE THE SIDEBAR AND DEFAULT UI */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="collapsedControl"] {display: none !important;}
    section[data-testid="stSidebar"] {display: none !important;}
    
    /* Top Bar & Hero Typography */
    .top-nav { display: flex; justify-content: space-between; padding: 1rem 0; margin-bottom: 2rem; border-bottom: 1px solid #E5E7EB; }
    .hero-greeting {
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        letter-spacing: -0.02em;
        margin-top: 2vh;
        margin-bottom: 0.5rem;
        color: #111827;
    }
    .hero-sub {
        font-size: 1.2rem;
        color: #4B5563;
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
    
    /* Floating Bento Cards (Light Mode Shadows) */
    [data-testid="stVerticalBlock"] > div > div > div > div > div {
        background-color: #FFFFFF; 
        border: 1px solid #F3F4F6 !important; 
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05); /* Very soft shadow */
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    [data-testid="stVerticalBlock"] > div > div > div > div > div:hover {
        box-shadow: 0 10px 30px rgba(0,0,0,0.1); 
        transform: translateY(-2px); 
    }

    /* Primary CTA Buttons */
    div.stButton > button {
        background-color: #111827;
        color: #FFFFFF !important;
        font-weight: 600;
        border-radius: 24px; /* Pill shape */
        border: none;
        padding: 0.5rem 1.5rem;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        background-color: #2563EB; /* Bright blue on hover */
    }
    
    /* Ghost Buttons (Nav/Logout) */
    .ghost-btn > div > button {
        background-color: transparent;
        color: #111827 !important;
        border: 1px solid #D1D5DB;
    }
    .ghost-btn > div > button:hover {
        border: 1px solid #111827;
        background-color: #F9FAFB;
    }

    /* Input Fields (The Central Prompt) */
    .stTextInput input {
        background-color: #F9FAFB !important;
        color: #111827 !important;
        border: 1px solid #E5E7EB !important; 
        border-radius: 12px;
        padding: 1rem 1.5rem;
        font-size: 1.1rem;
        box-shadow: inset 0 1px 3px rgba(0,0,0,0.02); 
    }
    .stTextInput input:focus {
        background-color: #FFFFFF !important;
        box-shadow: 0 0 0 2px #2563EB !important; /* Blue focus ring */
    }
    
    /* Modal / Dialog Cleanup */
    div[role="dialog"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 20px;
        color: #111827 !important;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1) !important;
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

# --- 4. STRIPE CHECKOUT ENGINE ---
def create_checkout_session(price_id):
    try:
        stripe.api_key = st.secrets["STRIPE_API_KEY"]
        with st.spinner("Connecting to secure payment gateway..."):
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id, 
                    'quantity': 1,
                }],
                mode='subscription',
                metadata={'tier': price_id},
                success_url="https://floorcast.streamlit.app/?success=true",
                cancel_url="https://floorcast.streamlit.app/?canceled=true",
            )
        st.link_button("💳 Proceed to Secure Payment", checkout_session.url, use_container_width=True)
    except Exception as e:
        st.error(f"Payment Gateway Error: {e}")

# --- 5. THE LOGIN MODAL ---
@st.dialog("Secure Client Portal")
def login_modal():
    st.markdown("<p style='color: #4B5563; font-weight: 500; margin-bottom: 1rem;'>Authenticate to access your workspace.</p>", unsafe_allow_html=True)
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
# --- 6. LOGGED OUT: PUBLIC MARKETING PAGE ---
# ==========================================
if not st.session_state.authenticated:
    # Top Bar
    c1, c2 = st.columns([6, 1])
    with c1: st.markdown("<h3 style='margin:0; color:#111827;'>🎰 FloorCast AI</h3>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
        if st.button("Client Login", use_container_width=True): login_modal()
        st.markdown('</div>', unsafe_allow_html=True)

    # Central Focus Hero
    st.markdown('<div class="hero-greeting">Predict. Perform. Profit.</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub" style="max-width: 700px; margin: 0 auto 3rem auto;">FloorCast AI consolidates your gaming, marketing, and lodging data to isolate what truly drives revenue. Stop guessing at attribution.</div>', unsafe_allow_html=True)

    # --- THE MARKETING RUNWAY (Features & Benefits) ---
    st.write("\n")
    m1, m2 = st.columns(2)
    with m1:
        with st.container():
            st.markdown("<h3 style='color:#111827;'>🎰 Total Floor Visibility</h3>", unsafe_allow_html=True)
            st.markdown("<p style='color:#4B5563;'>Stop looking at siloed reports. We merge gaming coin-in, F&B covers, and hotel occupancy into one unified, real-time operational dashboard.</p>", unsafe_allow_html=True)
    with m2:
        with st.container():
            st.markdown("<h3 style='color:#111827;'>🎯 Closed-Loop Attribution</h3>", unsafe_allow_html=True)
            st.markdown("<p style='color:#4B5563;'>End the marketing guessing game. Tie your digital ad spend, PR campaigns, and email blasts directly to on-property guest actions and revenue.</p>", unsafe_allow_html=True)
            
    st.write("\n")
    m3, m4 = st.columns(2)
    with m3:
        with st.container():
            st.markdown("<h3 style='color:#111827;'>🧠 Predictive AI Advisor</h3>", unsafe_allow_html=True)
            st.markdown("<p style='color:#4B5563;'>Fire your static dashboards. Ask our integrated AI questions about your property in plain English and instantly get actionable yield forecasts.</p>", unsafe_allow_html=True)
    with m4:
        with st.container():
            st.markdown("<h3 style='color:#111827;'>🛡️ Enterprise-Grade Vault</h3>", unsafe_allow_html=True)
            st.markdown("<p style='color:#4B5563;'>Built on a strict multi-tenant architecture. Your property's operational data is mathematically isolated, heavily encrypted, and completely private.</p>", unsafe_allow_html=True)

    # --- Floating Bento Pricing ---
    st.markdown("<h2 style='text-align:center; margin-bottom:3rem; margin-top:5rem; color:#111827;'>Choose Your Intelligence Tier</h2>", unsafe_allow_html=True)
    
    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown("<h2 style='text-align:center; color:#111827;'>Core</h2><h3 style='text-align:center; color:#111827;'>$299</h3><p style='text-align:center; color:#6B7280;'>/ month</p><br><p style='text-align:center; color:#4B5563;'>✔️ Casino Analytics<br>✔️ Marketing Attribution</p>", unsafe_allow_html=True)
        st.write("\n")
        if st.button("Select Core", key="b1", use_container_width=True): 
            create_checkout_session("price_YOUR_CORE_ID_HERE")
    with p2:
        st.markdown("<h2 style='text-align:center; color:#2563EB;'>Premium</h2><h3 style='text-align:center; color:#2563EB;'>$350</h3><p style='text-align:center; color:#6B7280;'>/ month</p><br><p style='text-align:center; color:#4B5563;'>✔️ Core Features<br>✔️ <b style='color:#111827;'>🧠 AI Advisor</b></p>", unsafe_allow_html=True)
        st.write("\n")
        if st.button("Select Premium", key="b2", use_container_width=True): 
            create_checkout_session("price_YOUR_PREMIUM_ID_HERE")
    with p3:
        st.markdown("<h2 style='text-align:center; color:#111827;'>Enterprise</h2><h3 style='text-align:center; color:#111827;'>$999</h3><p style='text-align:center; color:#6B7280;'>/ month</p><br><p style='text-align:center; color:#4B5563;'>✔️ All Features<br>✔️ Full Auxiliary Suite</p>", unsafe_allow_html=True)
        st.write("\n")
        if st.button("Select Enterprise", key="b3", use_container_width=True): 
            create_checkout_session("price_YOUR_ENTERPRISE_ID_HERE")
    st.stop()

# ==========================================
# --- 7. LOGGED IN: THE ACTIVE WORKSPACE ---
# ==========================================
profile = st.session_state.user_profile
prop_name = profile['tenants']['property_name']
role = profile['user_role']

# Clean Top Navigation Bar
nav_c1, nav_c2, nav_c3 = st.columns([1, 4, 1])
with nav_c1:
    st.markdown("<h4 style='margin-top: 10px; color:#111827;'>🎰 FloorCast OS</h4>", unsafe_allow_html=True)
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

# --- 8. PAGE ROUTING ---
if selected_page == "🏠 Overview":
    st.markdown("<h3 style='text-align: center; color: #6B7280; font-weight: 400; margin-top: 4vh;'>Select a module from the menu above to begin your analysis.</h3>", unsafe_allow_html=True)
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
