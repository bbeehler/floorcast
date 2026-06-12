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

# --- 4. AUTHENTICATION GATEWAY ---
if not st.session_state.authenticated:
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
    st.stop() # Halt execution if not logged in

# --- 5. THE DYNAMIC SHELL (Logged In) ---
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
    if "hotel_rev" in st.session_state.active_modules:
        nav_options.append("🛏️ Hotel & Booking")
    if "fnb" in st.session_state.active_modules:
        nav_options.append("🍽️ Food & Beverage")
        
    if role == "Super Admin":
        st.divider()
        nav_options.append("⚙️ Global SaaS Admin")
        
    selected_page = st.radio("Navigation", nav_options, label_visibility="collapsed")
    
    st.divider()
    if st.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 6. PAGE ROUTING ---
if selected_page == "🏠 Home / Account":
    st.title(f"Welcome to {prop_name}")
    st.write("Select an active module from the sidebar to begin.")
    
elif selected_page == "⚙️ Global SaaS Admin":
    import admin
    admin.render_admin_page(supabase)
    
elif selected_page == "🎰 Casino Analytics":
    import casino
    casino.render_casino_module(supabase, profile['tenant_id'], prop_name)
    
else:
    st.title(selected_page)
    st.info(f"The {selected_page} module is currently under construction for the new SaaS architecture.")
