# admin.py
import streamlit as st
import pandas as pd

def render_admin_page(supabase):
    st.markdown("<h2 style='color: #111827; margin-bottom: 1rem;'>⚙️ Global SaaS Command Center</h2>", unsafe_allow_html=True)
    st.write("Manage your client properties, AI mathematics, module subscriptions, and users.")

    tabs = st.tabs(["🎛️ AI Calibration", "🏢 Properties", "📦 Subscriptions", "👥 Users", "📊 System Health"])

    # Fetch tenants globally so multiple tabs can use the data
    try:
        res_tenants = supabase.table("tenants").select("*").execute()
        tenants_list = res_tenants.data if res_tenants.data else []
    except Exception:
        tenants_list = []

    # ==========================================
    # TAB 1: AI ENGINE CALIBRATION
    # ==========================================
    with tabs[0]:
        st.markdown("<h4 style='color: #111827;'>Property DNA & Forecasting Coefficients</h4>", unsafe_allow_html=True)
        st.write("Fine-tune the mathematical weights used by the predictive AI and attribution engines.")
        
        if tenants_list:
            tenant_map = {t['property_name']: t['id'] for t in tenants_list}
            
            c_sel, _ = st.columns([1, 2])
            with c_sel:
                target_tenant_name = st.selectbox("Select Target Property:", list(tenant_map.keys()), key="ai_calib_prop")
                target_tenant_id = tenant_map[target_tenant_name]
            
            # Fetch Existing Coefficients
            try:
                res_coeffs = supabase.table("mt_coefficients").select("*").eq("tenant_id", target_tenant_id).execute()
                c_data = res_coeffs.data[0] if res_coeffs.data else {}
            except Exception:
                c_data = {}

            with st.form(f"ai_calibration_form_{target_tenant_id}", border=False):
                st.markdown('<div class="bento-card">', unsafe_allow_html=True)
                
                st.markdown("<h5 style='color: #2563EB; margin-top: 0;'>💰 Financial Benchmarks</h5>", unsafe_allow_html=True)
                b1, b2 = st.columns(2)
                with b1: 
                    n_avg_coin = st.number_input("Target Avg Coin-In ($) per Guest", value=float(c_data.get('Avg_Coin_In', 112.50)))
                with b2: 
                    n_hold = st.number_input("Property Hold %", value=float(c_data.get('Hold_Pct', 10.0)), format="%.1f")

                st.markdown("<hr style='margin: 1.5rem 0;'>", unsafe_allow_html=True)
                
                st.markdown("<h5 style='color: #2563EB;'>🌐 Digital & Media Drivers</h5>", unsafe_allow_html=True)
                d1, d2, d3 = st.columns(3)
                with d1: 
                    n_clicks = st.number_input("Click Weight (Yield per Click)", value=float(c_data.get('Clicks', 0.05)), format="%.3f")
                with d2: 
                    n_social = st.number_input("Social Impression Weight", value=float(c_data.get('Social_Imp', 0.0002)), format="%.4f")
                with d3: 
                    n_decay = st.number_input("Adstock Retention % (Time Decay)", value=int(c_data.get('Ad_Decay', 85)))

                st.markdown("<hr style='margin: 1.5rem 0;'>", unsafe_allow_html=True)
                
                st.markdown("<h5 style='color: #2563EB;'>📡 Branding & Friction Elements</h5>", unsafe_allow_html=True)
                f1, f2, f3 = st.columns(3)
                with f1: 
                    n_broad = st.number_input("Broadcast/Brand Weight", value=int(c_data.get('Broadcast_Weight', 150)))
                with f2: 
                    n_rain = st.number_input("Rain Loss Penalty (per mm)", value=int(c_data.get('Rain_mm', -12)))
                with f3: 
                    n_snow = st.number_input("Snow Loss Penalty (per cm)", value=int(c_data.get('Snow_cm', -45)))

                st.write("\n")
                if st.form_submit_button("🚀 Hard-Save Property DNA to Vault", use_container_width=True):
                    payload = {
                        "tenant_id": target_tenant_id,
                        "Avg_Coin_In": n_avg_coin,
                        "Hold_Pct": n_hold,
                        "Clicks": n_clicks,
                        "Social_Imp": n_social,
                        "Ad_Decay": n_decay,
                        "Broadcast_Weight": n_broad,
                        "Rain_mm": n_rain,
                        "Snow_cm": n_snow
                    }
                    try:
                        supabase.table("mt_coefficients").upsert(payload, on_conflict="tenant_id").execute()
                        st.success(f"✅ AI Engine calibrated successfully for {target_tenant_name}.")
                    except Exception as e:
                        st.error(f"Vault Sync Failure: {e}")
                
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No properties found in the network. Provision a new tenant first.")

    # ==========================================
    # TAB 2: ADD & VIEW PROPERTIES
    # ==========================================
    with tabs[1]:
        st.subheader("Provision New Property")
        with st.form("add_tenant_form", clear_on_submit=True, border=False):
            st.markdown('<div class="bento-card">', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Property Name (e.g., Bellagio Las Vegas)")
            with c2:
                region = st.text_input("Region (e.g., North America)")
                
            if st.form_submit_button("🚀 Create Property", use_container_width=True):
                if name:
                    try:
                        supabase.table("tenants").insert({"property_name": name, "region": region}).execute()
                        st.success(f"Property '{name}' successfully provisioned!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating property: {e}")
                else:
                    st.error("Property name is required.")
            st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        st.subheader("Active Client Roster")
        if tenants_list:
            df_tenants = pd.DataFrame(tenants_list)
            display_df = df_tenants[['property_name', 'region', 'id', 'created_at']]
            st.markdown('<div class="bento-card">', unsafe_allow_html=True)
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No properties found. Provision your first client above.")

    # ==========================================
    # TAB 3: MANAGE SUBSCRIPTIONS
    # ==========================================
    with tabs[2]:
        st.subheader("Manage Active Modules")
        if tenants_list:
            tenants_dict = {t['property_name']: t['id'] for t in tenants_list}
            selected_tenant = st.selectbox("Select Client Property", list(tenants_dict.keys()), key="sub_tenant_select")
            tenant_id = tenants_dict[selected_tenant]

            # Look up what they are currently paying for
            try:
                sub_res = supabase.table("tenant_subscriptions").select("module_name").eq("tenant_id", tenant_id).eq("status", "active").execute()
                active_mods = [s['module_name'] for s in sub_res.data] if sub_res.data else []
            except Exception:
                active_mods = []

            with st.form("sub_form", border=False):
                st.markdown('<div class="bento-card">', unsafe_allow_html=True)
                st.write(f"Configure active modules for **{selected_tenant}**:")
                
                # BASE TIER (Locked On)
                st.markdown("##### 🟢 Core Platform (Included in Base Subscription)")
                st.checkbox("🎰 Casino Analytics", value=True, disabled=True)
                st.checkbox("📈 Marketing & Attribution", value=True, disabled=True)
                
                st.divider()

                # PREMIUM ADD-ONS (Optional)
                st.markdown("##### ⚡ Premium Add-ons")
                mod_pr = st.checkbox("📢 PR Scorecard", value="pr_media" in active_mods)
                mod_hotel = st.checkbox("🛏️ Hotel & Booking", value="hotel_rev" in active_mods)
                mod_fnb = st.checkbox("🍽️ Food & Beverage", value="fnb" in active_mods)
                mod_email = st.checkbox("📨 Email Analytics", value="email_ops" in active_mods)
                mod_ai = st.checkbox("🧠 FloorCast AI Advisor", value="ai_advisor" in active_mods)
                mod_report = st.checkbox("📊 Master Report Builder", value="master_report" in active_mods)

                st.write("\n")
                if st.form_submit_button("💾 Save Subscription Settings", use_container_width=True):
                    try:
                        # 1. Wipe the old subscriptions to start fresh
                        supabase.table("tenant_subscriptions").delete().eq("tenant_id", tenant_id).execute()
                        
                        # 2. Build the new list (Always include the Core Platform)
                        new_subs = [
                            {"tenant_id": tenant_id, "module_name": "casino_ops", "status": "active"},
                            {"tenant_id": tenant_id, "module_name": "marketing_pro", "status": "active"}
                        ]
                        
                        # 3. Add any selected Premium modules
                        if mod_pr: new_subs.append({"tenant_id": tenant_id, "module_name": "pr_media", "status": "active"})
                        if mod_hotel: new_subs.append({"tenant_id": tenant_id, "module_name": "hotel_rev", "status": "active"})
                        if mod_fnb: new_subs.append({"tenant_id": tenant_id, "module_name": "fnb", "status": "active"})
                        if mod_email: new_subs.append({"tenant_id": tenant_id, "module_name": "email_ops", "status": "active"})
                        if mod_ai: new_subs.append({"tenant_id": tenant_id, "module_name": "ai_advisor", "status": "active"})
                        if mod_report: new_subs.append({"tenant_id": tenant_id, "module_name": "master_report", "status": "active"})
                        
                        # 4. Save to database
                        supabase.table("tenant_subscriptions").insert(new_subs).execute()
                        st.success(f"Subscriptions successfully updated for {selected_tenant}!")
                    except Exception as e:
                        st.error(f"Error updating subscriptions: {e}")
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("You must create a property in the first tab before assigning modules.")

    # ==========================================
    # TAB 3: USER DIRECTORY
    # ==========================================
    with tabs[3]:
        st.subheader("Global User Directory")
        try:
            user_res = supabase.table("user_profiles").select("*, tenants(property_name)").execute()
            if user_res.data:
                df_users = pd.DataFrame(user_res.data)
                df_users['Property'] = df_users['tenants'].apply(lambda x: x['property_name'] if isinstance(x, dict) else 'Unassigned')
                display_users = df_users[['email', 'Property', 'user_role', 'created_at']]
                
                st.markdown('<div class="bento-card">', unsafe_allow_html=True)
                st.dataframe(display_users, use_container_width=True, hide_index=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("No users found. Users will appear here once they register.")
        except Exception as e:
            st.error(f"Error fetching users: {e}")

    # ==========================================
    # TAB 4: SYSTEM HEALTH
    # ==========================================
    with tabs[4]:
        st.markdown("<h4 style='color: #111827;'>Database Orchestration Metrics</h4>", unsafe_allow_html=True)
        try:
            prop_count = len(tenants_list)
            # Safe query for users if the previous one failed
            user_count_res = supabase.table("user_profiles").select("id", count="exact").execute()
            user_count = user_count_res.count if user_count_res.count else 0
            
            st.markdown(f"""
            <div style="display: flex; gap: 1.5rem; margin-top: 1rem;">
                <div class="bento-card" style="flex: 1; text-align: center;">
                    <p style="color: #6B7280; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; margin: 0;">Active Tenants</p>
                    <h2 style="color: #2563EB; font-size: 2.5rem; margin: 0.5rem 0;">{prop_count}</h2>
                </div>
                <div class="bento-card" style="flex: 1; text-align: center;">
                    <p style="color: #6B7280; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; margin: 0;">Provisioned Users</p>
                    <h2 style="color: #10B981; font-size: 2.5rem; margin: 0.5rem 0;">{user_count}</h2>
                </div>
                <div class="bento-card" style="flex: 1; text-align: center;">
                    <p style="color: #6B7280; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; margin: 0;">API Status</p>
                    <h2 style="color: #111827; font-size: 2.5rem; margin: 0.5rem 0;">Healthy</h2>
                </div>
            </div>
            """, unsafe_allow_html=True)
        except Exception as e: 
            st.error(f"Health Check Failed: {e}")
