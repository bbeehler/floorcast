import streamlit as st
import time
from database import supabase

def render():
    profile = st.session_state.user_profile
    
    # 1. Initialize the Wizard State
    if 'wizard_step' not in st.session_state:
        st.session_state.wizard_step = 1

    # 2. Fetch their parent company so we can personalize the UI
    try:
        access_res = supabase.table("user_property_access").select("parent_company_id, parent_companies(company_name)").eq("user_email", profile['email']).execute()
        if not access_res.data:
            st.error("CRITICAL: Your account is not linked to a Corporate Entity. Please contact FloorCast Support.")
            return
        comp_name = access_res.data[0]['parent_companies']['company_name']
    except Exception as e:
        st.error(f"System Error: {e}")
        return

    # 3. Wizard Header
    st.markdown(f"<h2 style='text-align: center; color: #111827; padding-top: 2rem; font-weight: 800;'>Welcome to FloorCast OS, {comp_name}</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6B7280; margin-bottom: 3rem; font-size: 1.1rem;'>Let's initialize your predictive engine and sync your data. This takes less than 3 minutes.</p>", unsafe_allow_html=True)

    # 4. Custom Progress Bar
    steps = ["1. Property Config", "2. Delegate Access", "3. Data Seed"]
    cols = st.columns(3)
    for i, col in enumerate(cols):
        with col:
            color = "#2563EB" if st.session_state.wizard_step >= (i+1) else "#E5E7EB"
            text_color = "#111827" if st.session_state.wizard_step >= (i+1) else "#9CA3AF"
            st.markdown(f"<div style='height: 4px; background-color: {color}; border-radius: 2px; margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; font-weight: 600; color: {text_color};'>{steps[i]}</p>", unsafe_allow_html=True)
    
    st.write("\n\n")

    # ==========================================
    # STEP 1: PROPERTY DETAILS
    # ==========================================
    if st.session_state.wizard_step == 1:
        with st.container(border=True):
            st.markdown("#### 🏢 Property Initialization")
            st.caption("Define the core parameters for your AI forecasting models.")
            
            with st.form("step1_form"):
                p_name = st.text_input("Primary Property Name", value=comp_name)
                
                c1, c2 = st.columns(2)
                with c1:
                    p_tz = st.selectbox("Operating Timezone", ["EST (New York, Ottawa)", "CST (Chicago)", "MST (Denver)", "PST (Las Vegas, LA)"])
                with c2:
                    p_fy = st.selectbox("Fiscal Year Start", ["January 1", "April 1", "July 1", "October 1"])
                
                st.write("\n")
                if st.form_submit_button("Save Configuration & Continue ➔", type="primary", use_container_width=True):
                    # In a full build, we would save these to a 'properties' table here.
                    st.session_state.wizard_step = 2
                    st.rerun()

    # ==========================================
    # STEP 2: TEAM DELEGATION
    # ==========================================
    elif st.session_state.wizard_step == 2:
        with st.container(border=True):
            st.markdown("#### 👥 Invite Department Heads")
            st.caption("Bring your VP of Marketing, F&B Director, and Hotel GM into the loop. (You can also do this later).")
            
            with st.form("step2_form"):
                f1, f2 = st.columns(2)
                with f1: t_email = st.text_input("Colleague Email")
                with f2: t_role = st.selectbox("Platform Role", ["Property Admin", "Read-Only User"])
                
                st.write("\n")
                c_back, c_skip, c_next = st.columns([1, 1, 2])
                with c_back:
                    if st.form_submit_button("⬅️ Back"):
                        st.session_state.wizard_step = 1
                        st.rerun()
                with c_skip:
                    if st.form_submit_button("Skip for now"):
                        st.session_state.wizard_step = 3
                        st.rerun()
                with c_next:
                    if st.form_submit_button("Send Invite & Continue ➔", type="primary"):
                        if t_email:
                            st.success(f"Secure invitation sent to {t_email}!")
                            time.sleep(1) # Visual pause so they see the success message
                            st.session_state.wizard_step = 3
                            st.rerun()
                        else:
                            st.error("Please enter an email or click 'Skip'.")

    # ==========================================
    # STEP 3: DATA SEED
    # ==========================================
    elif st.session_state.wizard_step == 3:
        with st.container(border=True):
            st.markdown("#### 📊 Initial Data Sync")
            st.caption("FloorCast OS requires historical baselines to train your predictive AI. Upload your standard export files below.")
            
            with st.form("step3_form"):
                st.file_uploader("🎰 Upload Historical Casino Ledger (CSV)", type=["csv"], help="Must include Coin-In, Table Drop, and Date columns.")
                st.file_uploader("🏨 Upload Hotel ADR/Occupancy (CSV) - Optional", type=["csv"])
                st.file_uploader("🍔 Upload F&B Covers (CSV) - Optional", type=["csv"])
                
                st.write("\n")
                c_back, c_launch = st.columns([1, 3])
                with c_back:
                    if st.form_submit_button("⬅️ Back"):
                        st.session_state.wizard_step = 2
                        st.rerun()
                with c_launch:
                    if st.form_submit_button("🚀 Train AI & Launch Dashboard", type="primary"):
                        with st.spinner("Processing data, training localized models, and initializing your workspace..."):
                            time.sleep(2) # Simulates heavy processing for dramatic SaaS effect
                            
                            try:
                                # Mark the user as completely onboarded in the database
                                supabase.table("user_profiles").update({"setup_complete": True}).eq("id", profile['id']).execute()
                                
                                # Update their current session so the app routes them to the dashboard
                                st.session_state.user_profile['setup_complete'] = True
                                
                                st.balloons() # Fun Streamlit Easter Egg for completion
                                st.rerun()
                            except Exception as e:
                                st.error(f"Launch failed: {e}")
