# admin.py
import streamlit as st
import pandas as pd

def render_admin_page(supabase):
    st.markdown("### ⚙️ Global SaaS Command Center")
    st.write("Manage your client properties, module subscriptions, and users.")

    # Create three isolated tabs for organization
    tabs = st.tabs(["🏢 Properties (Tenants)", "📦 Subscriptions", "👥 Users"])

    # --- TAB 1: ADD & VIEW PROPERTIES ---
    with tabs[0]:
        st.subheader("Provision New Property")
        with st.form("add_tenant_form", clear_on_submit=True):
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
                    except Exception as e:
                        st.error(f"Error creating property: {e}")
                else:
                    st.error("Property name is required.")

        st.divider()
        st.subheader("Active Client Roster")
        try:
            res = supabase.table("tenants").select("*").execute()
            if res.data:
                df_tenants = pd.DataFrame(res.data)
                display_df = df_tenants[['property_name', 'region', 'id', 'created_at']]
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.info("No properties found. Provision your first client above.")
        except Exception as e:
            st.error(f"Database error: {e}")

    # --- TAB 2: MANAGE SUBSCRIPTIONS ---
    with tabs[1]:
        st.subheader("Manage Active Modules")
        if 'res' in locals() and res.data:
            tenants_dict = {t['property_name']: t['id'] for t in res.data}
            selected_tenant = st.selectbox("Select Client Property", list(tenants_dict.keys()))
            tenant_id = tenants_dict[selected_tenant]

            # Look up what they are currently paying for
            sub_res = supabase.table("tenant_subscriptions").select("module_name").eq("tenant_id", tenant_id).eq("status", "active").execute()
            active_mods = [s['module_name'] for s in sub_res.data] if sub_res.data else []

            with st.form("sub_form"):
                st.write(f"Configure active modules for **{selected_tenant}**:")
                
                # Checkboxes default to True if the module is in their active list
                mod_casino = st.checkbox("🎰 Casino Analytics", value="casino_ops" in active_mods)
                mod_marketing = st.checkbox("📈 Marketing & Attribution", value="marketing_pro" in active_mods)
                mod_hotel = st.checkbox("🛏️ Hotel & Booking", value="hotel_rev" in active_mods)
                mod_fnb = st.checkbox("🍽️ Food & Beverage", value="fnb" in active_mods)

                if st.form_submit_button("💾 Save Subscription Settings", use_container_width=True):
                    try:
                        # 1. Wipe the old subscriptions to start fresh
                        supabase.table("tenant_subscriptions").delete().eq("tenant_id", tenant_id).execute()
                        
                        # 2. Build the new list based on the checkboxes
                        new_subs = []
                        if mod_casino: new_subs.append({"tenant_id": tenant_id, "module_name": "casino_ops", "status": "active"})
                        if mod_marketing: new_subs.append({"tenant_id": tenant_id, "module_name": "marketing_pro", "status": "active"})
                        if mod_hotel: new_subs.append({"tenant_id": tenant_id, "module_name": "hotel_rev", "status": "active"})
                        if mod_fnb: new_subs.append({"tenant_id": tenant_id, "module_name": "fnb", "status": "active"})
                        
                        # 3. Save to database
                        if new_subs:
                            supabase.table("tenant_subscriptions").insert(new_subs).execute()
                        
                        st.success("Subscriptions successfully updated!")
                    except Exception as e:
                        st.error(f"Error updating subscriptions: {e}")
        else:
            st.info("You must create a property in the first tab before assigning modules.")

    # --- TAB 3: USER DIRECTORY ---
    with tabs[2]:
        st.subheader("Global User Directory")
        try:
            user_res = supabase.table("user_profiles").select("*, tenants(property_name)").execute()
            if user_res.data:
                df_users = pd.DataFrame(user_res.data)
                df_users['Property'] = df_users['tenants'].apply(lambda x: x['property_name'] if isinstance(x, dict) else 'Unassigned')
                display_users = df_users[['email', 'Property', 'user_role', 'created_at']]
                st.dataframe(display_users, use_container_width=True, hide_index=True)
            else:
                st.info("No users found. Users will appear here once they register.")
        except Exception as e:
            st.error(f"Error fetching users: {e}")
