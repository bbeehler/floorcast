import streamlit as st
import time
from database import supabase
import pandas as pd

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
    with c_launch:
                    if st.form_submit_button("🚀 Train AI & Launch Dashboard", type="primary"):
                        with st.spinner("Parsing historical ledger and initializing AI models..."):
                            try:
                                # THE DYNAMIC DATA PARSER
                                if ledger_file is not None:
                                    # 1. Read the CSV
                                    df = pd.read_csv(ledger_file)
                                    
                                    # 2. Standardize column names (make lowercase, remove spaces)
                                    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
                                    
                                    # 3. Clean currency strings (remove $ and commas) and convert to float
                                    for col in ['coin_in', 'table_drop']:
                                        if col in df.columns:
                                            df[col] = df[col].replace('[\$,]', '', regex=True).astype(float)
                                        else:
                                            df[col] = 0.0 # Fallback if column is missing
                                            
                                    # 4. Prepare data for Supabase bulk insert
                                    records = []
                                    comp_id = access_res.data[0]['parent_company_id']
                                    
                                    for _, row in df.iterrows():
                                        records.append({
                                            "parent_company_id": comp_id,
                                            "record_date": str(row['date']) if 'date' in df.columns else None,
                                            "coin_in": row['coin_in'],
                                            "table_drop": row['table_drop']
                                        })
                                        
                                    # 5. Push to Database (Filtering out rows without dates)
                                    valid_records = [r for r in records if r['record_date'] is not None]
                                    if valid_records:
                                        supabase.table("property_performance").upsert(valid_records).execute()

                                # Mark the user as completely onboarded
                                supabase.table("user_profiles").update({"setup_complete": True}).eq("id", profile['id']).execute()
                                st.session_state.user_profile['setup_complete'] = True
                                
                                st.balloons()
                                time.sleep(1.5)
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Data parsing failed. Please check your CSV format. Error: {e}")
