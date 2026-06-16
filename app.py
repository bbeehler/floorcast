# app.py (Marketing First & Modal Login)
import streamlit as st
from supabase import create_client, Client
import stripe

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="FloorCast OS", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM ENTERPRISE CSS (High Contrast) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* True Black Background & Pure White Text */
    .stApp { background-color: #000000; color: #FFFFFF; }
    
    /* Hide Streamlit Header/Footer */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Hero & Marketing Typography */
    .hero-greeting {
        font-size: 4.5rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #A8C7FA, #FFFFFF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-top: 4vh;
        margin-bottom: 0.2rem;
        line-height: 1.1;
    }
    .hero-sub {
        font-size: 1.5rem;
        color: #FFFFFF;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 500;
    }
    .hero-promo {
        font-size: 1.2rem;
        color: #CCCCCC;
        text-align: center;
        margin-bottom: 8vh;
        max-width: 900px;
        margin-left: auto;
        margin-right: auto;
        line-height: 1.6;
    }

    /* Primary CTA Buttons (Stripe) */
    div.stButton > button {
        background-color: #A8C7FA;
        color: #000000 !important;
        font-weight: 600;
        border-radius: 8px;
        border: none;
        transition: all 0.2s ease;
        padding: 0.5rem 1rem;
    }
    div.stButton > button:hover {
        background-color: #FFFFFF;
        transform: translateY(-2px);
    }
    
    /* Navbar Login Button (Ghost style) */
    .nav-btn > div > button {
        background-color: transparent;
        color: #FFFFFF !important;
        border: 1px solid #555555;
    }
    .nav-btn > div > button:hover {
        border: 1px solid #FFFFFF;
        background-color: #111111;
    }

    /* Pricing Card Styling */
    [data-testid="stVerticalBlock"] > div > div > div > div > div {
        background-color: #0A0A0A;
        border: 1px solid #333333;
        border-radius: 12px;
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

# --- 4. THE LOGIN MODAL (Pop-up Module) ---
@st.dialog("Secure Client Portal")
def login_modal():
    st.write("Authenticate to access your property dashboard.")
    with st.form("saas_login_form", clear_on_submit=True):
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
                st.error("Invalid credentials or database error.")

# ==========================================
# --- 5. LOGGED OUT: PUBLIC MARKETING PAGE ---
# ==========================================
if not st.session_state.authenticated:
    # Hide sidebar UI entirely when logged out
    st.markdown("""
        <style>
        [data-testid="collapsedControl"] {display: none !important;}
        [data-testid="stSidebar"] {display: none !important;}
        </style>
    """, unsafe_allow_html=True)

    # Top Navigation Bar
    nav_col1, nav_col2 = st.columns([6, 1])
    with nav_col1:
        st.markdown("<h3 style='margin:0; color:#FFFFFF;'>🎰 FloorCast AI</h3>", unsafe_allow_html=True)
    with nav_col2:
        st.markdown('<div class="nav-btn">', unsafe_allow_html=True)
        if st.button("Client Login", use_container_width=True):
            login_modal() # Triggers the pop-up
        st.markdown('</div>', unsafe_allow_html=True)

    # The Hero Section
    st.markdown('<div class="hero-greeting">Predict. Perform. Profit.</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">The ultimate predictive engine for modern property operations.</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-promo">FloorCast AI consolidates your gaming, marketing, and lodging data to isolate what truly drives revenue. Stop guessing at attribution and let AI predict your next best operational move.</div>', unsafe_allow_html=True)

    # The Pricing Section
    st.markdown("<h2 style='text-align:center; margin-bottom:2rem;'>Choose Your Intelligence Tier</h2>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    
    # CORE TIER
    with c1:
        with st.container(border=True):
            st.markdown("<h2 style='text-align:center;'>Core</h2>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align:center;'>$299<span style='font-size:1rem; color:#AAAAAA;'> / mo</span></h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center; color:#AAAAAA;'>or $3,000 / year</p>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("✔️ **Casino Analytics**<br>✔️ **Marketing & Attribution**<br>❌ AI Advisor<br>❌ Auxiliary Modules", unsafe_allow_html=True)
            st.write("\n")
            if st.button("Select Core", key="btn_core", use_container_width=True):
                # Add your Stripe link here for $299
                st.info("Routing to Stripe Checkout...")

    # PREMIUM TIER
    with c2:
        with st.container(border=True):
            st.markdown("<h2 style='text-align:center; color:#A8C7FA;'>Premium</h2>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align:center; color:#A8C7FA;'>$350<span style='font-size:1rem; color:#AAAAAA;'> / mo</span></h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center; color:#AAAAAA;'>or $3,600 / year</p>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("✔️ **Casino Analytics**<br>✔️ **Marketing & Attribution**<br>✔️ **🧠 AI Advisor**<br>❌ Auxiliary Modules", unsafe_allow_html=True)
            st.write("\n")
            if st.button("Select Premium", key="btn_prem", use_container_width=True):
                # Add your Stripe link here for $350
                st.info("Routing to Stripe Checkout...")

    # ENTERPRISE TIER
    with c3:
        with st.container(border=True):
            st.markdown("<h2 style='text-align:center;'>Enterprise</h2>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align:center;'>$999<span style='font-size:1rem; color:#AAAAAA;'> / mo</span></h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align:center; color:#AAAAAA;'>or $10,000 / year</p>", unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("✔️ **All Core & Premium Features**<br>✔️ **PR Scorecard**<br>✔️ **Hotel & Booking**<br>✔️ **Food & Beverage**<br>✔️ **Email Analytics**", unsafe_allow_html=True)
            if st.button("Select Enterprise", key="btn_ent", use_container_width=True):
                # Add your Stripe link here for $999
                st.info("Routing to Stripe Checkout...")

    st.stop() # Halts execution for unauthenticated visitors

# ==========================================
# --- 6. LOGGED IN: THE ACTIVE WORKSPACE ---
# ==========================================
profile = st.session_state.user_profile
prop_name = profile['tenants']['property_name']
role = profile['user_role']

with st.sidebar:
    st.markdown(f"### 🏢 {prop_name}")
    st.caption(f"{profile['email']} ({role})")
    st.divider()
    
    st.markdown("### 🎛️ Active Modules")
    
    nav_options = ["🏠 Control Center"]
    if "ai_advisor" in st.session_state.active_modules: nav_options.append("🧠 AI Advisor")
    if "casino_ops" in st.session_state.active_modules: nav_options.append("🎰 Casino Analytics")
    if "marketing_pro" in st.session_state.active_modules: nav_options.append("📈 Marketing Analytics")
    if "pr_media" in st.session_state.active_modules: nav_options.append("📢 PR Scorecard")
    if "hotel_rev" in st.session_state.active_modules: nav_options.append("🛏️ Hotel & Booking")
    if "fnb" in st.session_state.active_modules: nav_options.append("🍽️ Food & Beverage")
    if "email_ops" in st.session_state.active_modules: nav_options.append("📨 Email Analytics")
        
    if role == "Super Admin":
        st.divider()
        nav_options.append("⚙️ Global SaaS Admin")
        
    selected_page = st.radio("Workspace", nav_options, label_visibility="collapsed")
    
    st.divider()
    if st.button("Sign Out", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 7. PAGE ROUTING ---
if selected_page == "🏠 Control Center":
    st.markdown(f'<div class="hero-greeting" style="text-align:left; font-size:2.5rem; margin-top:2vh;">Good afternoon.</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hero-sub" style="text-align:left; font-size:1.2rem; margin-bottom:3vh;">{prop_name} metrics are synced. Select a module from the sidebar.</div>', unsafe_allow_html=True)
    
elif selected_page == "⚙️ Global SaaS Admin":
    import admin
    admin.render_admin_page(supabase)
elif selected_page == "🎰 Casino Analytics":
    import casino
    casino.render_casino_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "📈 Marketing Analytics":
    import marketing
    marketing.render_marketing_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "📢 PR Scorecard":
    import pr
    pr.render_pr_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "📨 Email Analytics":
    import email_ops
    email_ops.render_email_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "🛏️ Hotel & Booking":
    import hotel
    hotel.render_hotel_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "🍽️ Food & Beverage":
    import fnb
    fnb.render_fnb_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "🧠 AI Advisor":
    import ai_advisor
    ai_advisor.render_advisor_module(supabase, profile['tenant_id'], prop_name)
else:
    st.title(selected_page)
    st.info(f"The {selected_page} module is currently under construction.")
