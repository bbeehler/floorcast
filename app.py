# app.py (The SaaS Router)
import streamlit as st
from supabase import create_client, Client

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="FloorCast SaaS OS", layout="wide", initial_sidebar_state="expanded")

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
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = None
if 'active_modules' not in st.session_state:
    st.session_state.active_modules = []
if 'show_login' not in st.session_state:
    st.session_state.show_login = False

# --- 4. PUBLIC LANDING PAGE ---
if not st.session_state.authenticated and not st.session_state.show_login:
    # Header & Pitch
    st.markdown("<h1 style='text-align: center; color: #FFCC00;'>🎰 FloorCast</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>The Next Generation of Hospitality & Casino Attribution</h3>", unsafe_allow_html=True)
    st.write("\n")
    
    # Value Proposition
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### Predict. Perform. Profit.")
        st.write(
            "FloorCast transforms raw hospitality and gaming data into high-stakes actionable intelligence. "
            "Built specifically for modern property operators, our secure multi-tenant platform eliminates guesswork "
            "across the gaming floor, marketing loops, and earned media channels."
        )
    with col_b:
        st.markdown("### Why FloorCast?")
        st.markdown("✔️ **Eliminate Data Silos:** Consolidate data from gaming, lodging, and F&B channels.")
        st.markdown("✔️ **AI Scenario Modeling:** Run seasonal forecasting with instant impact variables.")
        st.markdown("✔️ **Strict Data Isolation:** Enterprise-grade security keeps your operation completely private.")

    st.divider()

    # Pricing Tier Cards
    st.markdown("<h3 style='text-align: center;'>Simple, Transparent Architecture Pricing</h3>", unsafe_allow_html=True)
    st.write("\n")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        with st.container(border=True):
            st.markdown("### 🟢 Core Platform")
            st.markdown("#### **$999** / month")
            st.write("The fundamental data engine for modern property operations.")
            st.markdown("---")
            st.markdown("🔹 **🎰 Casino Analytics Module** (Traffic, Coin-In, Signups)")
            st.markdown("🔹 **📈 Marketing & Attribution Module** (MTA Modeling)")
            st.markdown("🔹 **🔮 AI Scenario Simulator** (Predictive Forecasting)")
            st.write("\n")
            if st.button("Subscribe to Core", use_container_width=True):
                st.info("🔄 Initiating secure Stripe checkout session...")
                # Stripe integration point will inject here

    with col_p2:
        with st.container(border=True):
            st.markdown("### ⚡ Enterprise Suite")
            st.markdown("#### **Custom Enterprise Tier**")
            st.write("Complete operational visibility across all premium auxiliary revenue streams.")
            st.markdown("---")
            st.markdown("🔹 **Includes everything in the Core Platform**")
            st.markdown("🔹 **📢 PR Scorecard Module** (Earned Media Performance)")
            st.markdown("🔹 **📨 Email Analytics Module** (Automated Ingestion & Metrics)")
            st.markdown("🔹 **🛏️ Hotel & Booking Module** + **🍽️ F&B Module**")
            if st.button("Contact Sales", use_container_width=True):
                st.success("📩 Request sent! Our enterprise team will follow up within 24 hours.")

    st.divider()
    
    # Login Trigger Footer
    _, col_btn, _ = st.columns([1, 1, 1])
    with col_btn:
        if st.button("Access Dashboard — Secure Login", use_container_width=True):
            st.session_state.show_login = True
            st.rerun()
            
    st.stop()

# --- 5. AUTHENTICATION GATEWAY ---
if not st.session_state.authenticated and st.session_state.show_login:
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        st.markdown("<h1 style='text-align: center;'>FloorCast OS</h1>", unsafe_allow_html=True)
        with st.form("saas_login_form", border=True):
            email = st.text_input("Work Email").strip().lower()
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Secure Login", use_container_width=True):
                try:
                    # 1. Authenticate with Supabase Auth
                    auth_res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    
                    if auth_res.user:
                        # 2. Fetch Multi-Tenant Profile
                        profile_res = supabase.table("user_profiles").select("*, tenants(property_name, region)").eq("email", email).execute()
                        
                        if profile_res.data:
                            user_data = profile_res.data[0]
                            tenant_id = user_data['tenant_id']
                            
                            # 3. Fetch Active Subscriptions for this Tenant
                            sub_res = supabase.table("tenant_subscriptions").select("module_name").eq("tenant_id", tenant_id).eq("status", "active").execute()
                            modules = [sub['module_name'] for sub in sub_res.data] if sub_res.data else []
                            
                            # 4. Lock in Session State
                            st.session_state.authenticated = True
                            st.session_state.user_profile = user_data
                            st.session_state.active_modules = modules
                            st.rerun()
                        else:
                            st.error("Account created, but no property assigned. Contact Support.")
                except Exception as e:
                    st.error("Invalid credentials or database error.")
                    
        if st.button("← Back to Product Page", use_container_width=True):
            st.session_state.show_login = False
            st.rerun()
    st.stop() # Halt execution if not logged in

# --- 6. THE DYNAMIC SHELL (Logged In) ---
profile = st.session_state.user_profile
prop_name = profile['tenants']['property_name']
role = profile['user_role']

with st.sidebar:
    st.markdown(f"**🏢 {prop_name}**")
    st.caption(f"User: {profile['email']} ({role})")
    st.divider()
    
    st.markdown("### 🎛️ Active Modules")
    
    # We build the navigation dynamically based on what they bought
    nav_options = ["🏠 Home / Account"]
    
    if "casino_ops" in st.session_state.active_modules:
        nav_options.append("🎰 Casino Analytics")
    if "marketing_pro" in st.session_state.active_modules:
        nav_options.append("📈 Marketing & Attribution")
    if "pr_media" in st.session_state.active_modules:
        nav_options.append("📢 PR Scorecard")
    if "hotel_rev" in st.session_state.active_modules:
        nav_options.append("🛏️ Hotel & Booking")
    if "fnb" in st.session_state.active_modules:
        nav_options.append("🍽️ Food & Beverage")
    if "email_ops" in st.session_state.active_modules:
        nav_options.append("📨 Email Analytics")
        
    if role == "Super Admin":
        st.divider()
        nav_options.append("⚙️ Global SaaS Admin")
        
    selected_page = st.radio("Navigation", nav_options, label_visibility="collapsed")
    
    st.divider()
    if st.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 7. PAGE ROUTING ---
if selected_page == "🏠 Home / Account":
    st.title(f"Welcome to {prop_name}")
    st.write("Select an active module from the sidebar to begin.")
    
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
    
else:
    st.title(selected_page)
    st.info(f"The {selected_page} module is currently under construction for the new SaaS architecture.")
