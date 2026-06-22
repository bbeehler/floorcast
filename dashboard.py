import streamlit as st
import pandas as pd
from database import supabase

def render():
    profile = st.session_state.user_profile
    user_role = profile.get('global_role', 'User')

    # ==========================================
    # 1. FETCH CLIENT CONTEXT & SUBSCRIPTIONS
    # ==========================================
    try:
        # Get their company info
        access_res = supabase.table("user_property_access").select("parent_company_id, parent_companies(company_name)").eq("user_email", profile['email']).execute()
        if not access_res.data:
            st.error("No company link found. Contact Support.")
            return
        
        comp_id = access_res.data[0]['parent_company_id']
        comp_name = access_res.data[0]['parent_companies']['company_name']

        # Get ALL modules in the system
        all_mods_res = supabase.table("system_modules").select("*").execute()
        all_modules = {m['module_name']: m for m in all_mods_res.data} if all_mods_res.data else {}

        # Get their ACTIVE subscriptions
        subs_res = supabase.table("company_subscriptions").select("system_modules(module_name)").eq("parent_company_id", comp_id).eq("status", "Active").execute()
        
        # Create a clean list of what they are allowed to see
        active_modules = [s['system_modules']['module_name'] for s in subs_res.data] if subs_res.data else []
        
    except Exception as e:
        st.error(f"Failed to load workspace data: {e}")
        return

    # ==========================================
    # 2. TOP NAVIGATION BAR
    # ==========================================
    nav_c1, nav_c2, nav_c3 = st.columns([6, 2, 1])
    with nav_c1: 
        st.markdown(f"<h3 style='margin-top: 10px; color:#111827;'>🎰 FloorCast OS <span style='color: #6B7280; font-weight: 400; font-size: 1.2rem;'>| {comp_name}</span></h3>", unsafe_allow_html=True)
    with nav_c2: 
        st.markdown(f"<p style='margin-top: 15px; color:#6B7280; font-size: 0.9rem; text-align: right;'>👤 {profile.get('first_name', '')} ({user_role})</p>", unsafe_allow_html=True)
    with nav_c3:
        st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
        if st.button("Sign Out", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # ==========================================
    # 3. DYNAMIC TAB GENERATOR (THE GATES)
    # ==========================================
    # We always give them an Overview tab. Then we add tabs based on their active subscriptions.
    tab_titles = ["📊 Master Overview"]
    
    # Sort active modules so they appear in a logical order if they have them
    if "Core AI & Marketing" in active_modules: tab_titles.append("🧠 Core AI Model")
    if "Hotel Premium" in active_modules: tab_titles.append("🏨 Hotel Engine")
    if "F&B Premium" in active_modules: tab_titles.append("🍔 F&B Engine")
    if "Entertainment Premium" in active_modules: tab_titles.append("🎫 Entertainment")
    
    tab_titles.append("⚙️ Settings")

    # Create the actual Streamlit tabs
    tabs = st.tabs(tab_titles)

    # --- TAB: MASTER OVERVIEW ---
    with tabs[0]:
        st.markdown("### Floor Performance Snapshot")
        st.caption("Aggregated view of today's predictive demand across all unlocked departments.")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Predicted Floor Traffic", "12,450", "+4% vs Last Week")
        
        # Only show the other metrics if they bought the modules!
        if "Hotel Premium" in active_modules:
            c2.metric("Forecasted ADR", "$214.50", "+$12.00")
        else:
            c2.metric("Forecasted ADR", "🔒 Locked", "Requires Hotel Module")
            
        if "F&B Premium" in active_modules:
            c3.metric("F&B Covers (Est)", "1,840", "-2%")
        else:
            c3.metric("F&B Covers", "🔒 Locked", "Requires F&B Module")
            
        c4.metric("Active Marketing Campaigns", "3", "ROI tracking live")
        
        st.write("\n")
        st.info("The interactive AI charts and ledger tables will be integrated here.")

    # --- DYNAMIC MODULE TABS ---
    # We map the tab index dynamically based on what was added to the list
    current_tab_index = 1
    
    if "Core AI & Marketing" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🧠 Core AI & Marketing Attribution")
            st.markdown("Upload marketing spend, view Adstock retention curves, and calculate closed-loop ROI.")
            # Your complex Media Mix Modeling code will go here
        current_tab_index += 1

    if "Hotel Premium" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🏨 Hotel Revenue Engine")
            st.markdown("Pace reports, occupancy forecasting, and dynamic pricing recommendations.")
            # Hotel specific code goes here
        current_tab_index += 1

    if "F&B Premium" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🍔 F&B Operational Engine")
            st.markdown("Inventory burn rates, staff scheduling predictions based on floor traffic.")
            # F&B specific code goes here
        current_tab_index += 1

    if "Entertainment Premium" in active_modules:
        with tabs[current_tab_index]:
            st.markdown("### 🎫 Entertainment Engine")
            st.markdown("Ticket sales velocity and crossover floor traffic analysis.")
            # Entertainment specific code goes here
        current_tab_index += 1

    # --- TAB: SETTINGS & UPSELLS ---
    with tabs[-1]: # The last tab is always settings
        st.markdown("### Property Settings")
        st.markdown("Manage your team, update data feeds, and view active integrations.")
        
        # The Upsell Block - Show them what they are missing!
        missing_modules = [m for m in all_modules.keys() if m not in active_modules]
        if missing_modules:
            st.divider()
            st.markdown("#### 🚀 Unlock More Power")
            st.caption("Contact your FloorCast account executive to activate these premium engines.")
            
            upsell_cols = st.columns(len(missing_modules) if len(missing_modules) < 4 else 3)
            for i, mod_name in enumerate(missing_modules):
                with upsell_cols[i % 3]:
                    st.markdown(f"""
                    <div style='background-color: #F3F4F6; padding: 1.5rem; border-radius: 8px; border: 1px dashed #D1D5DB;'>
                        <h5 style='margin-top: 0;'>🔒 {mod_name}</h5>
                        <p style='color: #6B7280; font-size: 0.9rem;'>{all_modules[mod_name]['description']}</p>
                    </div>
                    """, unsafe_allow_html=True)
