# app.py (The Gemini-Style Router)
import streamlit as st
from supabase import create_client, Client
import stripe

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="FloorCast OS", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM ENTERPRISE CSS (Gemini Dark Mode Palette) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Gemini Dark Mode Colors */
    .stApp { background-color: #131314; color: #E3E3E3; }
    
    /* Hide Streamlit Header/Footer */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Center the main greeting */
    .hero-greeting {
        font-size: 3.5rem;
        font-weight: 500;
        background: -webkit-linear-gradient(45deg, #A8C7FA, #FFFFFF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-top: 5vh;
        margin-bottom: 0.5rem;
    }
    .hero-sub {
        font-size: 1.5rem;
        color: #C4C7C5;
        text-align: center;
        margin-bottom: 5vh;
    }

    /* Style the Login/Auth Box like a prompt input */
    [data-testid="stForm"] {
        background-color: #1E1F20;
        border: 1px solid #444746;
        border-radius: 24px;
        padding: 2rem;
        max-width: 600px;
        margin: 0 auto;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* Upgrade Buttons */
    div.stButton > button {
        background-color: #A8C7FA;
        color: #041E49 !important;
        font-weight: 600;
        border-radius: 20px;
        border: none;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        background-color: #D3E3FD;
        transform: scale(1.02);
    }
    
    /* Secondary/Ghost Button styling for the pricing link */
    .ghost-btn > div > button {
        background-color: transparent;
        color: #A8C7FA !important;
        border: 1px solid #444746;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE CONNECTION ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Critical Error: Missing Database Secrets. {e}")
        st.stop()

supabase = init_connection()

# --- 3. SESSION STATE INITIALIZATION ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_profile' not in st.session_state: st.session_state.user_profile = None
if 'active_modules' not in st.session_state: st.session_state.active_modules = []
if 'show_pricing' not in st.session_state: st.session_state.show_pricing = False

# --- 4. TOP NAVIGATION BAR (Logged Out) ---
if not st.session_state.authenticated:
    st.sidebar.empty() # Keep sidebar hidden when logged out
    
    nav_col1, nav_col2 = st.columns([4, 1])
    with nav_col1:
        st.markdown("<h3 style='margin:0;'>🎰 FloorCast AI</h3>", unsafe_allow_html=True)
    with nav_col2:
        st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
        if st.button("View Enterprise Pricing", use_container_width=True):
            st.session_state.show_pricing = not st.session_state.show_pricing
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- 5. LOGGED OUT: PRICING OVERLAY ---
if not st.session_state.authenticated and st.session_state.show_pricing:
    st.markdown("<h2 style='text-align:center; margin-top:2rem;'>Core Platform Access</h2>", unsafe_allow_html=True)
    _, p_col, _ = st.columns([1, 2, 1])
    with p_col:
        with st.container(border=True):
            st.markdown("<h1 style='text-align:center;'>$999<span style='font-size:1rem; color:#888;'>/mo</span></h1>", unsafe_allow_html=True)
            st.write("Full access to Casino Analytics, Marketing Attribution, and the AI Scenario Simulator.")
            if st.button("Initialize Stripe Checkout", use_container_width=True):
                try:
                    stripe.api_key = st.secrets["STRIPE_API_KEY"]
                    with st.spinner("Connecting to secure payment gateway..."):
                        checkout_session = stripe.checkout.Session.create(
                            payment_method_types=['card'],
                            line_items=[{'price_data': {'currency': 'usd', 'unit_amount': 99900, 'product_data': {'name': 'FloorCast Core Platform'}}, 'quantity': 1}],
                            mode='subscription',
                            success_url="https://floorcast.streamlit.app/?success=true",
                            cancel_url="https://floorcast.streamlit.app/?canceled=true",
                        )
                    st.link_button("💳 Proceed to Secure Payment", checkout_session.url, use_container_width=True)
                except Exception as e:
                    st.error(f"Payment Gateway Error: Make sure your Stripe API key is in your Streamlit Secrets. Details: {e}")
    st.stop()

# --- 6. LOGGED OUT: THE GEMINI ENTRY GATEWAY ---
if not st.session_state.authenticated and not st.session_state.show_pricing:
    # The Massive Greeting
    st.markdown('<div class="hero-greeting">Hello.</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Sign in to unlock FloorCast AI and optimize your property.</div>', unsafe_allow_html=True)
    
    # The Centralized Login
    _, auth_col, _ = st.columns([1, 2, 1])
    with auth_col:
        with st.form("saas_login_form", clear_on_submit=True):
            email = st.text_input("Corporate Email", placeholder="manager@casino.com").strip().lower()
            password = st.text_input("Access Token (Password)", type="password", placeholder="••••••••")
            
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
    st.stop()

# ==========================================
# --- 7. LOGGED IN: THE ACTIVE WORKSPACE ---
# ==========================================
profile = st.session_state.user_profile
prop_name = profile['tenants']['property_name']
role = profile['user_role']

# The Sidebar Appears
with st.sidebar:
    st.markdown(f"### 🏢 {prop_name}")
    st.caption(f"{profile['email']} ({role})")
    st.divider()
    
    st.markdown("### 🎛️ Active Modules")
    
    nav_options = ["🏠 Control Center"]
    if "casino_ops" in st.session_state.active_modules: nav_options.append("🎰 Casino Analytics")
    if "marketing_pro" in st.session_state.active_modules: nav_options.append("📈 Marketing & Attribution")
    if "pr_media" in st.session_state.active_modules: nav_options.append("📢 PR Scorecard")
    if "hotel_rev" in st.session_state.active_modules: nav_options.append("🛏️ Hotel & Booking")
    if "fnb" in st.session_state.active_modules: nav_options.append("🍽️ Food & Beverage")
    if "email_ops" in st.session_state.active_modules: nav_options.append("📨 Email Analytics")
    if "ai_advisor" in st.session_state.active_modules: nav_options.append("🧠 AI Advisor")
        
    if role == "Super Admin":
        st.divider()
        nav_options.append("⚙️ Global SaaS Admin")
        
    selected_page = st.radio("Workspace", nav_options, label_visibility="collapsed")
    
    st.divider()
    if st.button("Sign Out", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 8. PAGE ROUTING ---
if selected_page == "🏠 Control Center":
    # Logged-in Greeting matches the aesthetic
    st.markdown(f'<div class="hero-greeting" style="text-align:left; font-size:2.5rem; margin-top:2vh;">Good afternoon.</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hero-sub" style="text-align:left; font-size:1.2rem; margin-bottom:3vh;">{prop_name} metrics are synced. Select a module from the sidebar.</div>', unsafe_allow_html=True)
    
elif selected_page == "⚙️ Global SaaS Admin":
    import admin
    admin.render_admin_page(supabase)
    
elif selected_page == "🎰 Casino Analytics":
    import casino
    casino.render_casino_module(supabase, profile['tenant_id'], prop_name)

elif selected_page == "📈 Marketing & Attribution":
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
    st.info(f"The {selected_page} module is currently under construction for the new SaaS architecture.")
