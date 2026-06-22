# app.py (Phase 1: The Gateway & CRM Capture)
import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

# =================================================================
# 1. PAGE CONFIGURATION & STYLING
# =================================================================
st.set_page_config(page_title="FloorCast OS", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #FAFAFA; color: #111827; }
    
    /* Hide Default UI */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="collapsedControl"] {display: none !important;}
    section[data-testid="stSidebar"] {display: none !important;}
    
    /* Typography */
    .hero-title { font-size: 4rem; font-weight: 800; text-align: center; letter-spacing: -0.03em; margin-top: 5vh; color: #111827; line-height: 1.1; }
    .hero-sub { font-size: 1.25rem; color: #6B7280; text-align: center; margin-bottom: 3rem; font-weight: 400; max-width: 800px; margin-left: auto; margin-right: auto; }
    
    /* Bento Cards */
    .bento-card { background-color: #FFFFFF; border-radius: 16px; padding: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.03); border: 1px solid #F3F4F6; height: 100%; transition: transform 0.2s ease; }
    .bento-card:hover { transform: translateY(-3px); box-shadow: 0 12px 30px rgba(0,0,0,0.08); }
    
    /* Buttons */
    div.stButton > button { background-color: #111827; color: #FFFFFF !important; font-weight: 600; border-radius: 8px; border: none; padding: 0.6rem 1.5rem; transition: all 0.2s ease; }
    div.stButton > button:hover { background-color: #2563EB; }
    
    /* Ghost Buttons (Nav/Login) */
    .ghost-btn > div > button { background-color: transparent; color: #111827 !important; border: 1px solid #D1D5DB; border-radius: 24px; }
    .ghost-btn > div > button:hover { border: 1px solid #111827; background-color: #FFFFFF; }
    
    /* Inputs */
    .stTextInput input, .stTextArea textarea { background-color: #FFFFFF !important; color: #111827 !important; border: 1px solid #E5E7EB !important; border-radius: 8px; }
    .stTextInput input:focus, .stTextArea textarea:focus { box-shadow: 0 0 0 2px #2563EB !important; border-color: transparent !important; }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 2. DATABASE CONNECTION & SESSION STATE
# =================================================================
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error("Critical System Error: Connection secrets missing.")
        st.stop()

supabase = init_connection()

if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_profile' not in st.session_state: st.session_state.user_profile = None

# =================================================================
# 3. AUTHENTICATION (LOGIN MODAL)
# =================================================================
@st.dialog("Secure Client Portal")
def login_modal():
    st.markdown("<p style='color: #6B7280; margin-bottom: 1.5rem;'>Authenticate to access your workspace.</p>", unsafe_allow_html=True)
    with st.form("client_login_form", border=False):
        email = st.text_input("Corporate Email").strip().lower()
        password = st.text_input("Access Token", type="password")
        if st.form_submit_button("Authenticate & Enter", use_container_width=True):
            try:
                auth_res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if auth_res.user:
                    profile_res = supabase.table("user_profiles").select("*").eq("id", auth_res.user.id).execute()
                    if profile_res.data:
                        st.session_state.authenticated = True
                        st.session_state.user_profile = profile_res.data[0]
                        st.rerun()
                    else:
                        st.error("Profile not found in directory. Contact Support.")
            except Exception as e:
                st.error("Invalid credentials.")

# =================================================================
# 4. LOGGED OUT: MARKETING & LEAD CAPTURE
# =================================================================
if not st.session_state.authenticated:
    
    # --- Top Nav ---
    c1, c2 = st.columns([6, 1])
    with c1: st.markdown("<h3 style='margin:0; color:#111827; padding-top: 10px;'>🎰 FloorCast OS</h3>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
        if st.button("Client Login", use_container_width=True): login_modal()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Hero Section ---
    st.markdown('<div class="hero-title">Predict. Perform. Profit.</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">The ultimate AI-driven operational and marketing attribution engine for enterprise casinos and resorts. Stop guessing what drives floor traffic.</div>', unsafe_allow_html=True)

    # --- Feature Grid ---
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("""
        <div class="bento-card">
            <h3 style='margin-top:0;'>🎰 Total Floor Visibility</h3>
            <p style='color:#6B7280; line-height: 1.6;'>Merge gaming coin-in, F&B covers, and hotel occupancy into one unified, real-time dashboard.</p>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown("""
        <div class="bento-card">
            <h3 style='margin-top:0;'>🎯 Closed-Loop ROI</h3>
            <p style='color:#6B7280; line-height: 1.6;'>Tie your digital ad spend, PR campaigns, and email blasts directly to on-property guest actions.</p>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown("""
        <div class="bento-card">
            <h3 style='margin-top:0;'>🧠 AI Predictability</h3>
            <p style='color:#6B7280; line-height: 1.6;'>Utilize your historical ledger data and localized physics to accurately forecast daily demand.</p>
        </div>
        """, unsafe_allow_html=True)

    st.write("\n\n")
    st.divider()
    st.write("\n\n")

    # --- Lead Capture Form (Replaces Self-Serve Checkout) ---
    st.markdown("<h2 style='text-align:center; margin-bottom: 0.5rem;'>Request Enterprise Access</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color: #6B7280; margin-bottom: 3rem;'>FloorCast OS is deployed via concierge onboarding. Submit your details below to schedule a platform review.</p>", unsafe_allow_html=True)
    
    col_space1, col_form, col_space2 = st.columns([1, 2, 1])
    with col_form:
        with st.form("lead_capture_form", clear_on_submit=True):
            st.markdown('<div class="bento-card">', unsafe_allow_html=True)
            
            f1, f2 = st.columns(2)
            with f1: l_first = st.text_input("First Name *")
            with f2: l_last = st.text_input("Last Name *")
            
            l_email = st.text_input("Corporate Email *")
            
            c1, c2 = st.columns(2)
            with c1: l_company = st.text_input("Company / Property Name *")
            with c2: l_phone = st.text_input("Phone Number")
            
            l_msg = st.text_area("Tell us about your operational goals")
            
            st.write("\n")
            if st.form_submit_button("Submit Request", use_container_width=True):
                if l_first and l_last and l_email and l_company:
                    try:
                        payload = {
                            "first_name": l_first, "last_name": l_last,
                            "email": l_email.strip().lower(), "company_name": l_company,
                            "phone": l_phone, "message": l_msg
                        }
                        supabase.table("leads").insert(payload).execute()
                        st.success("✅ Request received! A FloorCast specialist will contact you shortly.")
                    except Exception as e:
                        st.error(f"Submission failed: {e}")
                else:
                    st.error("Please fill in all required (*) fields.")
            st.markdown('</div>', unsafe_allow_html=True)
            
    st.stop() # Stops execution for logged-out users

# =================================================================
# 5. LOGGED IN: THE WORKSPACE ROUTER & CRM
# =================================================================
profile = st.session_state.user_profile
global_role = profile.get('global_role', 'User')

# --- Workspace Navigation Bar ---
nav_c1, nav_c2, nav_c3 = st.columns([6, 1, 1])
with nav_c1: 
    st.markdown("<h4 style='margin-top: 10px; color:#111827;'>🎰 FloorCast OS</h4>", unsafe_allow_html=True)
with nav_c2:
    st.markdown(f"<p style='margin-top: 15px; color:#6B7280; font-size: 0.9rem; text-align: right;'>{profile.get('first_name', '')} ({global_role})</p>", unsafe_allow_html=True)
with nav_c3:
    st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
    if st.button("Sign Out", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# =================================================================
# 5A. SUPER ADMIN CRM 
# =================================================================
if global_role == 'Super Admin':
    st.markdown('<div class="hero-title" style="text-align: left; font-size: 2.5rem; margin-top: 0;">🛡️ Command Center</div>', unsafe_allow_html=True)
    st.markdown('<p style="color: #6B7280; font-size: 1.1rem; margin-bottom: 2rem;">Manage incoming leads, provision parent companies, create user accounts, and track manual billing.</p>', unsafe_allow_html=True)

    tab_leads, tab_companies, tab_users, tab_billing = st.tabs(["🎯 Lead Pipeline", "🏢 Parent Companies", "👥 User Provisioning", "💳 Billing & Invoices"])

    # -----------------------------------------------------------
    # TAB 1: LEAD PIPELINE
    # -----------------------------------------------------------
    with tab_leads:
        st.markdown("### 📥 Inbound Enterprise Requests")
        try:
            leads_res = supabase.table("leads").select("*").order("created_at", desc=True).execute()
            if leads_res.data:
                df_leads = pd.DataFrame(leads_res.data)
                
                # Metrics
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Leads", len(df_leads))
                c2.metric("New Leads", len(df_leads[df_leads['status'] == 'New Lead']))
                c3.metric("Converted", len(df_leads[df_leads['status'] == 'Converted']))
                
                st.write("\n")
                
                # Lead Cards
                for _, lead in df_leads.iterrows():
                    with st.container(border=True):
                        col_info, col_action = st.columns([3, 1])
                        with col_info:
                            status_color = "#10B981" if lead['status'] == 'Converted' else "#F59E0B" if lead['status'] == 'New Lead' else "#6B7280"
                            st.markdown(f"**{lead['company_name']}** — {lead['first_name']} {lead['last_name']}")
                            st.markdown(f"📧 {lead['email']} | 📞 {lead.get('phone', 'N/A')}")
                            st.caption(f"Status: <span style='color: {status_color}; font-weight: 600;'>{lead['status']}</span> | Submitted: {str(lead['created_at'])[:10]}", unsafe_allow_html=True)
                            if lead.get('message'):
                                st.info(f"**Goal:** {lead['message']}")
                        
                        with col_action:
                            if lead['status'] != 'Converted':
                                if st.button("✔️ Mark Contacted", key=f"contact_{lead['id']}", use_container_width=True):
                                    supabase.table("leads").update({"status": "Contacted"}).eq("id", lead['id']).execute()
                                    st.rerun()
                                if st.button("🚀 Convert to Account", key=f"convert_{lead['id']}", type="primary", use_container_width=True):
                                    # Move to Parent Companies table
                                    payload = {
                                        "company_name": lead['company_name'],
                                        "billing_email": lead['email'],
                                        "account_status": "Active"
                                    }
                                    try:
                                        supabase.table("parent_companies").insert(payload).execute()
                                        supabase.table("leads").update({"status": "Converted"}).eq("id", lead['id']).execute()
                                        st.success(f"Created Parent Company: {lead['company_name']}")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Conversion Error: {e}")
            else:
                st.info("The lead pipeline is currently empty.")
        except Exception as e:
            st.error(f"Database Error: {e}")

    # -----------------------------------------------------------
    # TAB 2: PARENT COMPANIES
    # -----------------------------------------------------------
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
                    else:
                        st.error("Fields required.")

        with col_list:
            st.markdown("### 🏢 Active Corporate Accounts")
            if not df_comps.empty:
                for _, comp in df_comps.iterrows():
                    with st.expander(f"🏦 {comp['company_name']}"):
                        st.write(f"**Billing Email:** {comp['billing_email']}")
                        owed_color = "#EF4444" if comp['total_owed'] > 0 else "#10B981"
                        st.markdown(f"**Total Outstanding Balance:** <span style='color: {owed_color}; font-size: 1.2rem; font-weight: 600;'>${comp['total_owed']:,.2f}</span>", unsafe_allow_html=True)
                        st.caption(f"Status: {comp['account_status']} | Company ID: {comp['id']}")
            else:
                st.info("No Parent Companies provisioned yet.")

    # -----------------------------------------------------------
    # TAB 3: USER PROVISIONING (The Concierge Tool)
    # -----------------------------------------------------------
    with tab_users:
        st.markdown("### 🤵 Concierge Account Creation")
        st.caption("Generate secure credentials for your clients and assign them to their Parent Company.")
        
        # Fetch active companies so you can link the new user directly to them
        try:
            active_comps = supabase.table("parent_companies").select("id, company_name").execute()
            comp_dict = {c['company_name']: c['id'] for c in active_comps.data} if active_comps.data else {"No Companies Available": None}
        except:
            comp_dict = {"Error fetching companies": None}

        col_form, col_space = st.columns([2, 1])
        with col_form:
            with st.form("concierge_setup_form"):
                u_first = st.text_input("First Name *")
                u_last = st.text_input("Last Name *")
                u_email = st.text_input("Client Email *").strip().lower()
                u_pass = st.text_input("Temporary Password *", type="password", help="The client will use this to log in for the first time.")
                
                st.divider()
                
                u_role = st.selectbox("Platform Role", ["Company Admin", "Property Admin", "User"])
                u_company = st.selectbox("Link to Parent Company", list(comp_dict.keys()))
                
                if st.form_submit_button("🚀 Provision Client Account", type="primary", use_container_width=True):
                    target_comp_id = comp_dict.get(u_company)
                    
                    if u_first and u_last and u_email and u_pass and target_comp_id:
                        try:
                            # 1. Create the secure login (Trigger automatically builds the profile)
                            auth_res = supabase.auth.sign_up({"email": u_email, "password": u_pass})
                            
                            if auth_res.user:
                                # 2. Update their profile with their real name and role
                                supabase.table("user_profiles").update({
                                    "first_name": u_first,
                                    "last_name": u_last,
                                    "global_role": u_role
                                }).eq("id", auth_res.user.id).execute()
                                
                                # 3. Link them to the Parent Company so they can access their properties
                                supabase.table("user_property_access").insert({
                                    "user_email": u_email,
                                    "parent_company_id": target_comp_id,
                                    "user_role": u_role
                                }).execute()
                                
                                st.success(f"✅ Success! {u_first} {u_last} can now log in to {u_company}.")
                        except Exception as e:
                            st.error(f"Provisioning Failed: {e}")
                    else:
                        st.error("Please fill in all required fields and ensure a Parent Company is selected.")

    # -----------------------------------------------------------
    # TAB 4: BILLING & INVOICES
    # -----------------------------------------------------------
    with tab_billing:
        st.markdown("### 💳 Manual Billing Ledger")
        
        if df_comps.empty:
            st.warning("You must provision a Parent Company before you can generate invoices.")
        else:
            comp_options = {c['company_name']: c['id'] for _, c in df_comps.iterrows()}
            
            b_col1, b_col2 = st.columns(2)
            
            # --- CREATE INVOICE ---
            with b_col1:
                with st.form("create_invoice_form"):
                    st.markdown("#### 📝 Issue New Invoice")
                    inv_comp = st.selectbox("Select Parent Company", list(comp_options.keys()))
                    inv_amount = st.number_input("Invoice Amount ($)", min_value=0.0, step=100.0)
                    inv_due = st.date_input("Due Date")
                    
                    if st.form_submit_button("Issue Invoice", use_container_width=True):
                        if inv_amount > 0:
                            comp_id = comp_options[inv_comp]
                            try:
                                # 1. Create Invoice
                                supabase.table("invoices").insert({
                                    "parent_company_id": comp_id,
                                    "invoice_amount": inv_amount,
                                    "due_date": str(inv_due)
                                }).execute()
                                
                                # 2. Update Company Total Owed
                                current_owed = df_comps[df_comps['id'] == comp_id].iloc[0]['total_owed']
                                new_total = float(current_owed) + float(inv_amount)
                                supabase.table("parent_companies").update({"total_owed": new_total}).eq("id", comp_id).execute()
                                
                                st.success("Invoice issued & balance updated.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Billing Error: {e}")
                        else:
                            st.error("Amount must be greater than zero.")

            # --- LOG PAYMENT ---
            with b_col2:
                with st.form("log_payment_form"):
                    st.markdown("#### 💰 Log Received Payment")
                    pay_comp = st.selectbox("Select Paying Company", list(comp_options.keys()), key="pay_comp")
                    pay_amount = st.number_input("Amount Received ($)", min_value=0.0, step=100.0)
                    pay_method = st.selectbox("Payment Method", ["Wire Transfer", "ACH", "Check", "Credit Card"])
                    pay_notes = st.text_input("Transaction / Check # (Optional)")
                    
                    if st.form_submit_button("Process Payment", use_container_width=True):
                        if pay_amount > 0:
                            comp_id = comp_options[pay_comp]
                            try:
                                # 1. Log Payment
                                supabase.table("payments").insert({
                                    "parent_company_id": comp_id,
                                    "amount_paid": pay_amount,
                                    "payment_method": pay_method,
                                    "notes": pay_notes
                                }).execute()
                                
                                # 2. Reduce Company Total Owed
                                current_owed = df_comps[df_comps['id'] == comp_id].iloc[0]['total_owed']
                                new_total = max(0.0, float(current_owed) - float(pay_amount))
                                supabase.table("parent_companies").update({"total_owed": new_total}).eq("id", comp_id).execute()
                                
                                st.success("Payment logged & balance reduced.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Payment Error: {e}")
                        else:
                            st.error("Amount must be greater than zero.")
            
            # --- OUTSTANDING INVOICES ---
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
                    st.info("No pending invoices. All accounts are settled.")
            except:
                st.info("Unable to fetch invoices.")

# =================================================================
# 5B. CLIENT WORKSPACE (WIZARD & DASHBOARD)
# =================================================================
elif global_role in ['User', 'Company Admin', 'Property Admin']:
    st.info("🚀 Welcome to FloorCast OS.")
    st.markdown("The **Self-Serve Setup Wizard** will be built here in the next phase. This will guide clients through adding properties, toggling modules, setting the fiscal year, and uploading initial data.")

st.title(f"Welcome back, {profile.get('first_name', 'User')}.")
st.info("The Logged-In Workspace router will be built here in Phase 2.")
