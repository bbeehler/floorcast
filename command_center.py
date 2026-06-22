import streamlit as st
import pandas as pd
from database import supabase

# =================================================================
# CONVERSION WIZARD MODAL
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
                    # 1. Create the Parent Company
                    comp_res = supabase.table("parent_companies").insert({
                        "company_name": c_name, 
                        "billing_email": c_email
                    }).execute()
                    
                    new_comp_id = comp_res.data[0]['id']
                    
                    # 2. Create the Auth User (Trigger handles profile creation)
                    auth_res = supabase.auth.sign_up({"email": u_email, "password": u_pass})
                    
                    if auth_res.user:
                        # 3. Update the Profile with real names and 'Company Admin' role
                        supabase.table("user_profiles").update({
                            "first_name": u_first,
                            "last_name": u_last,
                            "global_role": "Company Admin"
                        }).eq("id", auth_res.user.id).execute()
                        
                        # 4. Link the user to the new Parent Company
                        supabase.table("user_property_access").insert({
                            "user_email": u_email,
                            "parent_company_id": new_comp_id,
                            "user_role": "Company Admin"
                        }).execute()
                        
                        # 5. Mark the Lead as Converted
                        supabase.table("leads").update({"status": "Converted"}).eq("id", lead['id']).execute()
                        
                        st.success("✅ Account fully provisioned!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Conversion Failed: {e}")
            else:
                st.error("A temporary password is required to create the account.")


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
    st.markdown('<p style="color: #6B7280; font-size: 1.1rem; margin-bottom: 2rem;">Manage incoming leads, provision parent companies, create user accounts, and track manual billing.</p>', unsafe_allow_html=True)

    tab_leads, tab_companies, tab_users, tab_billing = st.tabs(["🎯 Lead Pipeline", "🏢 Parent Companies", "👥 User Provisioning", "💳 Billing & Invoices"])

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
                                
                                # THIS IS THE NEW BUTTON LOGIC
                                if st.button("🚀 Convert & Provision", key=f"convert_{lead['id']}", type="primary", use_container_width=True):
                                    convert_lead_modal(lead)
            else:
                st.info("The lead pipeline is currently empty.")
        except Exception as e:
            st.error(f"Database Error: {e}")

    # --- TAB 2: PARENT COMPANIES ---
    with tab_companies:
        col_list, col_add = st.columns([2, 1])
        try:
            comp_res = supabase.table("parent_companies").select("*").order("company_name").execute()
            df_comps = pd.DataFrame(comp_res.data) if comp_res.data else pd.DataFrame()
        except:
            df_comps = pd.DataFrame()

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
                    with st.expander(f"🏦 {comp['company_name']}"):
                        st.write(f"**Billing Email:** {comp['billing_email']}")
                        owed_color = "#EF4444" if comp['total_owed'] > 0 else "#10B981"
                        st.markdown(f"**Outstanding Balance:** <span style='color: {owed_color}; font-weight: 600;'>${comp['total_owed']:,.2f}</span>", unsafe_allow_html=True)
            else:
                st.info("No Parent Companies provisioned yet.")

    # --- TAB 3: USER PROVISIONING ---
    with tab_users:
        st.markdown("### 🤵 Concierge Account Creation")
        try:
            active_comps = supabase.table("parent_companies").select("id, company_name").execute()
            comp_dict = {c['company_name']: c['id'] for c in active_comps.data} if active_comps.data else {}
        except:
            comp_dict = {}

        col_form, _ = st.columns([2, 1])
        with col_form:
            with st.form("concierge_setup_form"):
                u_first = st.text_input("First Name *")
                u_last = st.text_input("Last Name *")
                u_email = st.text_input("Client Email *").strip().lower()
                u_pass = st.text_input("Temporary Password *", type="password")
                st.divider()
                u_role = st.selectbox("Platform Role", ["Company Admin", "Property Admin", "User"])
                u_company = st.selectbox("Link to Parent Company", list(comp_dict.keys())) if comp_dict else st.selectbox("Company", ["No Companies Available"])
                
                if st.form_submit_button("🚀 Provision Client Account", type="primary", use_container_width=True):
                    if u_first and u_last and u_email and u_pass and comp_dict:
                        target_comp_id = comp_dict.get(u_company)
                        try:
                            auth_res = supabase.auth.sign_up({"email": u_email, "password": u_pass})
                            if auth_res.user:
                                supabase.table("user_profiles").update({"first_name": u_first, "last_name": u_last, "global_role": u_role}).eq("id", auth_res.user.id).execute()
                                supabase.table("user_property_access").insert({"user_email": u_email, "parent_company_id": target_comp_id, "user_role": u_role}).execute()
                                st.success(f"✅ Success! {u_first} can now log in.")
                        except Exception as e:
                            st.error(f"Provisioning Failed: {e}")

    # --- TAB 4: BILLING & INVOICES ---
    with tab_billing:
        st.markdown("### 💳 Manual Billing Ledger")
        if df_comps.empty:
            st.warning("Provision a Parent Company first.")
        else:
            comp_options = {c['company_name']: c['id'] for _, c in df_comps.iterrows()}
            b_col1, b_col2 = st.columns(2)
            
            with b_col1:
                with st.form("create_invoice_form"):
                    st.markdown("#### 📝 Issue New Invoice")
                    inv_comp = st.selectbox("Parent Company", list(comp_options.keys()))
                    inv_amount = st.number_input("Invoice Amount ($)", min_value=0.0, step=100.0)
                    inv_due = st.date_input("Due Date")
                    if st.form_submit_button("Issue Invoice", use_container_width=True):
                        comp_id = comp_options[inv_comp]
                        supabase.table("invoices").insert({"parent_company_id": comp_id, "invoice_amount": inv_amount, "due_date": str(inv_due)}).execute()
                        current_owed = df_comps[df_comps['id'] == comp_id].iloc[0]['total_owed']
                        supabase.table("parent_companies").update({"total_owed": float(current_owed) + float(inv_amount)}).eq("id", comp_id).execute()
                        st.rerun()

            with b_col2:
                with st.form("log_payment_form"):
                    st.markdown("#### 💰 Log Received Payment")
                    pay_comp = st.selectbox("Paying Company", list(comp_options.keys()))
                    pay_amount = st.number_input("Amount Received ($)", min_value=0.0, step=100.0)
                    pay_method = st.selectbox("Payment Method", ["Wire Transfer", "ACH", "Check", "Credit Card"])
                    if st.form_submit_button("Process Payment", use_container_width=True):
                        comp_id = comp_options[pay_comp]
                        supabase.table("payments").insert({"parent_company_id": comp_id, "amount_paid": pay_amount, "payment_method": pay_method}).execute()
                        current_owed = df_comps[df_comps['id'] == comp_id].iloc[0]['total_owed']
                        new_total = max(0.0, float(current_owed) - float(pay_amount))
                        supabase.table("parent_companies").update({"total_owed": new_total}).eq("id", comp_id).execute()
                        st.rerun()
