import streamlit as st
import pandas as pd
import time
from database import supabase

# =================================================================
# MODALS & DIALOGS
# =================================================================
@st.dialog("🚀 Convert Lead & Provision Account")
def convert_lead_modal(lead):
    st.markdown(f"Automated onboarding for **{lead['company_name']}**")
    
    with st.form("conversion_form"):
        st.markdown("#### 1. Corporate Account")
        c_name = st.text_input("Parent Company Name", value=lead['company_name'])
        c_email = st.text_input("Billing Email", value=lead['email'])
        st.divider()
        st.markdown("#### 2. Master Admin Login")
        u_first = st.text_input("First Name", value=lead['first_name'])
        u_last = st.text_input("Last Name", value=lead['last_name'])
        u_email = st.text_input("Login Email", value=lead['email'])
        u_pass = st.text_input("Temporary Password *", type="password", help="The GM will use this to log in the first time.")
        
        if st.form_submit_button("Create Company & Provision Admin", type="primary", use_container_width=True):
            if u_pass:
                try:
                    comp_res = supabase.table("parent_companies").insert({"company_name": c_name, "billing_email": c_email}).execute()
                    new_comp_id = comp_res.data[0]['id']
                    auth_res = supabase.auth.sign_up({"email": u_email, "password": u_pass})
                    if auth_res.user:
                        supabase.table("user_profiles").update({"first_name": u_first, "last_name": u_last, "global_role": "Company Admin"}).eq("id", auth_res.user.id).execute()
                        supabase.table("user_property_access").insert({"user_email": u_email, "parent_company_id": new_comp_id, "user_role": "Company Admin"}).execute()
                        supabase.table("leads").update({"status": "Converted"}).eq("id", lead['id']).execute()
                        st.success("✅ Account fully provisioned!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Conversion Failed: {e}")
            else:
                st.error("A temporary password is required.")

@st.dialog("✏️ Edit Company Details")
def edit_company_modal(comp):
    with st.form(f"edit_form_{comp['id']}"):
        new_name = st.text_input("Company Name", value=comp['company_name'])
        new_email = st.text_input("Billing Email", value=comp['billing_email'])
        new_status = st.selectbox("Account Status", ["Active", "Suspended", "Churned"], index=["Active", "Suspended", "Churned"].index(comp.get('account_status', 'Active')))
        
        if st.form_submit_button("Save Changes", type="primary", use_container_width=True):
            try:
                supabase.table("parent_companies").update({
                    "company_name": new_name,
                    "billing_email": new_email,
                    "account_status": new_status
                }).eq("id", comp['id']).execute()
                st.success("Company details updated.")
                st.rerun()
            except Exception as e:
                st.error(f"Update failed: {e}")

@st.dialog("⚠️ Delete Parent Company")
def delete_company_modal(comp):
    st.error(f"Are you sure you want to delete **{comp['company_name']}**?")
    st.warning("This will permanently remove the company, sever access for all its users, and delete associated subscriptions and pending invoices.")
    confirm = st.text_input(f"Type '{comp['company_name']}' to confirm:")
    
    if st.button("Permanently Delete Company", type="primary", use_container_width=True):
        if confirm == comp['company_name']:
            try:
                supabase.table("parent_companies").delete().eq("id", comp['id']).execute()
                st.success("Company deleted.")
                st.rerun()
            except Exception as e:
                st.error(f"Deletion failed. Error: {e}")
        else:
            st.error("Confirmation name does not match.")

@st.dialog("✏️ Edit Module Details")
def edit_module_modal(mod):
    with st.form(f"edit_mod_{mod['id']}"):
        m_name = st.text_input("Module Name", value=mod['module_name'])
        m_desc = st.text_area("Description", value=mod.get('description', ''))
        m_price = st.number_input("Base Price / Month ($)", value=float(mod['base_price']), step=50.0)
        
        if st.form_submit_button("Save Module", type="primary", use_container_width=True):
            try:
                supabase.table("system_modules").update({
                    "module_name": m_name, "description": m_desc, "base_price": m_price
                }).eq("id", mod['id']).execute()
                st.success("Module updated.")
                st.rerun()
            except Exception as e:
                st.error(f"Update failed: {e}")

@st.dialog("⚠️ Delete Module")
def delete_module_modal(mod):
    st.error(f"Delete **{mod['module_name']}** from your global catalog?")
    st.warning("This will instantly cancel this subscription for ANY client currently using it.")
    
    if st.button("Permanently Delete Module", type="primary", use_container_width=True):
        try:
            supabase.table("system_modules").delete().eq("id", mod['id']).execute()
            st.success("Module deleted.")
            st.rerun()
        except Exception as e:
            st.error(f"Deletion failed: {e}")


# =================================================================
# MAIN COMMAND CENTER RENDER
# =================================================================
def render():
    profile = st.session_state.user_profile
    global_role = profile.get('global_role', 'User')

    # --- Workspace Navigation Bar ---
    nav_c1, nav_c2, nav_c3 = st.columns([6, 1, 1])
    with nav_c1: st.markdown("<h4 style='margin-top: 10px; color:#111827;'>🎰 FloorCast OS</h4>", unsafe_allow_html=True)
    with nav_c2: st.markdown(f"<p style='margin-top: 15px; color:#6B7280; font-size: 0.9rem; text-align: right;'>{profile.get('first_name', '')} ({global_role})</p>", unsafe_allow_html=True)
    with nav_c3:
        st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
        if st.button("Sign Out", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    if global_role != 'Super Admin':
        st.error("Unauthorized Access.")
        return

    st.markdown('<div class="hero-title" style="text-align: left; font-size: 2.5rem; margin-top: 0;">🛡️ Command Center</div>', unsafe_allow_html=True)
    st.markdown('<p style="color: #6B7280; font-size: 1.1rem; margin-bottom: 2rem;">Manage leads, provision accounts, assign modules, and automate billing.</p>', unsafe_allow_html=True)

    tab_leads, tab_companies, tab_users, tab_subs, tab_billing = st.tabs(["🎯 Lead Pipeline", "🏢 Parent Companies", "👥 User Management", "📦 Subscriptions", "💳 Billing & Invoices"])

    # --- FETCH GLOBAL DATA ---
    try:
        comp_res = supabase.table("parent_companies").select("*").order("company_name").execute()
        df_comps = pd.DataFrame(comp_res.data) if comp_res.data else pd.DataFrame()
        comp_dict = {c['company_name']: c['id'] for _, c in df_comps.iterrows()} if not df_comps.empty else {}
    except:
        df_comps = pd.DataFrame()
        comp_dict = {}

    # --- TAB 1: LEAD PIPELINE ---
    with tab_leads:
        st.markdown("### 📥 Inbound Enterprise Requests")
        try:
            leads_res = supabase.table("leads").select("*").order("created_at", desc=True).execute()
            if leads_res.data:
                df_leads = pd.DataFrame(leads_res.data)
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Leads", len(df_leads))
                c2.metric("New Leads", len(df_leads[df_leads['status'] == 'New Lead']))
                c3.metric("Converted", len(df_leads[df_leads['status'] == 'Converted']))
                st.write("\n")
                
                for _, lead in df_leads.iterrows():
                    with st.container(border=True):
                        col_info, col_action = st.columns([3, 1])
                        with col_info:
                            status_color = "#10B981" if lead['status'] == 'Converted' else "#F59E0B" if lead['status'] == 'New Lead' else "#6B7280"
                            st.markdown(f"**{lead['company_name']}** — {lead['first_name']} {lead['last_name']}")
                            st.markdown(f"📧 {lead['email']} | 📞 {lead.get('phone', 'N/A')}")
                            st.caption(f"Status: <span style='color: {status_color}; font-weight: 600;'>{lead['status']}</span>", unsafe_allow_html=True)
                        with col_action:
                            if lead['status'] != 'Converted':
                                if st.button("✔️ Mark Contacted", key=f"contact_{lead['id']}", use_container_width=True):
                                    supabase.table("leads").update({"status": "Contacted"}).eq("id", lead['id']).execute()
                                    st.rerun()
                                if st.button("🚀 Convert & Provision", key=f"convert_{lead['id']}", type="primary", use_container_width=True):
                                    convert_lead_modal(lead)
            else:
                st.info("The lead pipeline is currently empty.")
        except Exception as e:
            st.error(f"Database Error: {e}")

    # --- TAB 2: PARENT COMPANIES ---
    with tab_companies:
        col_list, col_add = st.columns([2, 1])
        with col_add:
            st.markdown("### ➕ Manual Provision")
            with st.form("add_parent_company"):
                new_c_name = st.text_input("Company Name *")
                new_c_email = st.text_input("Billing Email *")
                if st.form_submit_button("Create Parent Account", use_container_width=True):
                    if new_c_name and new_c_email:
                        supabase.table("parent_companies").insert({"company_name": new_c_name, "billing_email": new_c_email}).execute()
                        st.success("Company created.")
                        st.rerun()

        with col_list:
            st.markdown("### 🏢 Active Corporate Accounts")
            if not df_comps.empty:
                for _, comp in df_comps.iterrows():
                    with st.expander(f"🏦 {comp['company_name']} - {comp.get('account_status', 'Active')}"):
                        st.write(f"**Billing Email:** {comp['billing_email']}")
                        owed_color = "#EF4444" if comp['total_owed'] > 0 else "#10B981"
                        st.markdown(f"**Outstanding Balance:** <span style='color: {owed_color}; font-weight: 600;'>${comp['total_owed']:,.2f}</span>", unsafe_allow_html=True)
                        
                        c_edit, c_del = st.columns(2)
                        with c_edit:
                            if st.button("✏️ Edit Details", key=f"edit_{comp['id']}", use_container_width=True):
                                edit_company_modal(comp)
                        with c_del:
                            if st.button("🗑️ Delete Company", key=f"del_{comp['id']}", use_container_width=True):
                                delete_company_modal(comp)
            else:
                st.info("No Parent Companies provisioned yet.")

    # --- TAB 3: USER MANAGEMENT ---
    with tab_users:
        u_col_form, u_col_list = st.columns([1, 1])
        
        with u_col_form:
            st.markdown("### 🤵 Concierge Account Creation")
            with st.form("concierge_setup_form"):
                u_first = st.text_input("First Name *")
                u_last = st.text_input("Last Name *")
                u_email = st.text_input("Account Email *").strip().lower()
                u_pass = st.text_input("Temporary Password *", type="password")
                st.divider()
                
                u_role = st.selectbox("Platform Role", ["Super Admin", "Company Admin", "Property Admin", "User"])
                comp_options = list(comp_dict.keys()) if comp_dict else ["No Companies Available"]
                u_company = st.selectbox("Link to Parent Company", comp_options, disabled=(u_role == "Super Admin"))
                
                if st.form_submit_button("🚀 Provision Account", type="primary", use_container_width=True):
                    if u_first and u_email and u_pass:
                        try:
                            auth_res = supabase.auth.sign_up({"email": u_email, "password": u_pass})
                            if auth_res.user:
                                supabase.table("user_profiles").update({
                                    "first_name": u_first, "last_name": u_last, "global_role": u_role
                                }).eq("id", auth_res.user.id).execute()
                                
                                if u_role != "Super Admin" and comp_dict:
                                    target_comp_id = comp_dict.get(u_company)
                                    supabase.table("user_property_access").insert({
                                        "user_email": u_email, "parent_company_id": target_comp_id, "user_role": u_role
                                    }).execute()
                                
                                st.success(f"✅ {u_role} account created for {u_email}!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Provisioning Failed: {e}")
                    else:
                        st.error("Please fill in required fields.")

        with u_col_list:
            st.markdown("### 📋 Active User Directory")
            try:
                users_res = supabase.table("user_profiles").select("*").execute()
                if users_res.data:
                    df_users = pd.DataFrame(users_res.data)
                    for _, u in df_users.iterrows():
                        with st.expander(f"👤 {u['first_name']} {u['last_name']} ({u['global_role']})"):
                            st.write(f"**Email:** {u['email']}")
                            if st.button("🚫 Revoke System Access", key=f"revoke_{u['id']}", use_container_width=True):
                                supabase.table("user_profiles").delete().eq("id", u['id']).execute()
                                st.success("Access revoked. User profile deleted.")
                                st.rerun()
                else:
                    st.info("No users found.")
            except Exception as e:
                st.error("Could not load user directory.")

    # --- TAB 4: SUBSCRIPTIONS & CATALOG ---
    with tab_subs:
        sub_tab_clients, sub_tab_catalog = st.tabs(["🤝 Client Subscriptions", "📚 Global Catalog"])
        
        try:
            mods_res = supabase.table("system_modules").select("*").order("module_name").execute()
            mod_data = {m['module_name']: m for m in mods_res.data} if mods_res.data else {}
        except:
            mod_data = {}

        # 4A: CLIENT SUBSCRIPTIONS
        with sub_tab_clients:
            if not comp_dict:
                st.warning("Provision a Parent Company first.")
            else:
                sub_col1, sub_col2 = st.columns([1, 2])
                with sub_col1:
                    selected_comp_sub = st.selectbox("Select Company to Manage", list(comp_dict.keys()), key="sub_comp_select")
                    target_id = comp_dict[selected_comp_sub]

                    with st.form("add_subscription_form"):
                        st.markdown("#### Assign Module")
                        if mod_data:
                            selected_mod = st.selectbox("Select Module", list(mod_data.keys()))
                            b_freq = st.selectbox("Billing Frequency", ["Monthly", "Yearly"])
                            custom_price = st.number_input("Contract Price ($)", value=0.00, step=100.0, help="Enter the total amount billed per period (e.g., $2500 for Monthly, $24000 for Yearly).")
                            
                            if st.form_submit_button("➕ Activate Subscription", use_container_width=True):
                                try:
                                    supabase.table("company_subscriptions").insert({
                                        "parent_company_id": target_id, 
                                        "module_id": mod_data[selected_mod]['id'], 
                                        "agreed_price": custom_price,
                                        "billing_frequency": b_freq
                                    }).execute()
                                    st.success("Subscription Activated!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed (Already subscribed?): {e}")
                        else:
                            st.info("No modules found in catalog.")

                with sub_col2:
                    st.markdown(f"#### Active Subscriptions for {selected_comp_sub}")
                    try:
                        subs_res = supabase.table("company_subscriptions").select("*, system_modules(module_name)").eq("parent_company_id", target_id).eq("status", "Active").execute()
                        if subs_res.data:
                            df_subs = pd.DataFrame(subs_res.data)
                            df_subs['Module'] = df_subs['system_modules'].apply(lambda x: x['module_name'])
                            df_subs = df_subs[['Module', 'billing_frequency', 'agreed_price', 'created_at', 'id']]
                            
                            for _, sub in df_subs.iterrows():
                                with st.container(border=True):
                                    c_info, c_action = st.columns([4, 1])
                                    with c_info:
                                        st.markdown(f"**{sub['Module']}**")
                                        st.caption(f"Billed {sub['billing_frequency']} at ${sub['agreed_price']:,.2f}")
                                    with c_action:
                                        if st.button("Cancel", key=f"canc_{sub['id']}", type="secondary", use_container_width=True):
                                            supabase.table("company_subscriptions").delete().eq("id", sub['id']).execute()
                                            st.rerun()
                        else:
                            st.info("No active subscriptions.")
                    except Exception as e:
                        st.error(f"Unable to load subscriptions. {e}")

        # 4B: GLOBAL CATALOG
        with sub_tab_catalog:
            cat_col_form, cat_col_list = st.columns([1, 2])
            
            with cat_col_form:
                st.markdown("#### Add New Module")
                with st.form("create_module_form"):
                    new_m_name = st.text_input("Module Name *")
                    new_m_desc = st.text_area("Description")
                    new_m_price = st.number_input("Base Monthly Price ($)", min_value=0.0, step=50.0)
                    if st.form_submit_button("Create Module", type="primary", use_container_width=True):
                        if new_m_name:
                            try:
                                supabase.table("system_modules").insert({"module_name": new_m_name, "description": new_m_desc, "base_price": new_m_price}).execute()
                                st.success("Module added to catalog.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Creation failed: {e}")
                        else:
                            st.error("Module name is required.")
            
            with cat_col_list:
                st.markdown("#### Platform Catalog")
                if mod_data:
                    for mod_name, mod in mod_data.items():
                        with st.expander(f"📦 {mod_name} - Base: ${mod['base_price']:,.2f}/mo"):
                            st.write(mod.get('description', 'No description provided.'))
                            mc1, mc2 = st.columns(2)
                            with mc1:
                                if st.button("✏️ Edit Module", key=f"m_edit_{mod['id']}", use_container_width=True):
                                    edit_module_modal(mod)
                            with mc2:
                                if st.button("🗑️ Delete Module", key=f"m_del_{mod['id']}", use_container_width=True):
                                    delete_module_modal(mod)
                else:
                    st.info("Your module catalog is empty.")

    # --- TAB 5: BILLING & INVOICES ---
    with tab_billing:
        st.markdown("### 💳 Automated Billing Ledger")
        if not comp_dict:
            st.warning("Provision a Parent Company first.")
        else:
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                with st.form("auto_invoice_form"):
                    st.markdown("#### 📝 Generate Invoice")
                    inv_comp = st.selectbox("Select Parent Company", list(comp_dict.keys()), key="inv_select")
                    inv_type = st.selectbox("Invoice Type", ["Monthly Subscriptions", "Yearly Subscriptions", "Custom Manual Entry"])
                    
                    calc_amount = 0.0
                    comp_id = comp_dict[inv_comp] if comp_dict else None
                    
                    if inv_type != "Custom Manual Entry" and comp_id:
                        freq_filter = "Monthly" if "Monthly" in inv_type else "Yearly"
                        subs_res = supabase.table("company_subscriptions").select("agreed_price").eq("parent_company_id", comp_id).eq("status", "Active").eq("billing_frequency", freq_filter).execute()
                        if subs_res.data:
                            calc_amount = sum(float(s['agreed_price']) for s in subs_res.data)
                    
                    st.info(f"Calculated Total: **${calc_amount:,.2f}**")
                    custom_override = st.number_input("Override/Custom Amount ($)", value=0.0, step=100.0, help="Use this if calculating manually or applying a one-time charge.")
                    
                    final_amount = custom_override if custom_override > 0 else calc_amount
                    inv_due = st.date_input("Due Date")
                    
                    if st.form_submit_button("Issue Invoice", use_container_width=True):
                        if final_amount > 0:
                            try:
                                supabase.table("invoices").insert({"parent_company_id": comp_id, "invoice_amount": final_amount, "due_date": str(inv_due)}).execute()
                                current_owed = df_comps[df_comps['id'] == comp_id].iloc[0]['total_owed']
                                supabase.table("parent_companies").update({"total_owed": float(current_owed) + float(final_amount)}).eq("id", comp_id).execute()
                                st.success(f"Issued invoice for ${final_amount:,.2f}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Billing Error: {e}")
                        else:
                            st.error("Cannot issue a $0.00 invoice.")

            with b_col2:
                with st.form("log_payment_form"):
                    st.markdown("#### 💰 Log Received Payment")
                    pay_comp = st.selectbox("Paying Company", list(comp_dict.keys()), key="pay_select")
                    pay_amount = st.number_input("Amount Received ($)", min_value=0.0, step=100.0)
                    pay_method = st.selectbox("Payment Method", ["Wire Transfer", "ACH", "Check", "Credit Card"])
                    if st.form_submit_button("Process Payment", use_container_width=True):
                        if pay_amount > 0:
                            comp_id = comp_dict[pay_comp]
                            try:
                                supabase.table("payments").insert({"parent_company_id": comp_id, "amount_paid": pay_amount, "payment_method": pay_method}).execute()
                                current_owed = df_comps[df_comps['id'] == comp_id].iloc[0]['total_owed']
                                new_total = max(0.0, float(current_owed) - float(pay_amount))
                                supabase.table("parent_companies").update({"total_owed": new_total}).eq("id", comp_id).execute()
                                st.success("Payment logged & balance reduced.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Payment Error: {e}")
                        else:
                            st.error("Amount must be greater than zero.")
            
            st.divider()
            st.markdown("#### 🧾 Outstanding Invoices")
            try:
                inv_res = supabase.table("invoices").select("*, parent_companies(company_name)").eq("status", "Pending").order("due_date").execute()
                if inv_res.data:
                    df_inv = pd.DataFrame(inv_res.data)
                    df_inv['Company'] = df_inv['parent_companies'].apply(lambda x: x['company_name'])
                    df_inv = df_inv[['Company', 'invoice_amount', 'due_date', 'status']]
                    st.dataframe(df_inv, use_container_width=True, hide_index=True)
                else:
                    st.info("No pending invoices.")
            except:
                st.info("Unable to fetch invoices.")
