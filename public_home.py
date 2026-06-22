import streamlit as st
from database import supabase

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

def render():
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
        st.markdown("<div class='bento-card'><h3 style='margin-top:0;'>🎰 Total Floor Visibility</h3><p style='color:#6B7280; line-height: 1.6;'>Merge gaming coin-in, F&B covers, and hotel occupancy into one unified, real-time dashboard.</p></div>", unsafe_allow_html=True)
    with m2:
        st.markdown("<div class='bento-card'><h3 style='margin-top:0;'>🎯 Closed-Loop ROI</h3><p style='color:#6B7280; line-height: 1.6;'>Tie your digital ad spend, PR campaigns, and email blasts directly to on-property guest actions.</p></div>", unsafe_allow_html=True)
    with m3:
        st.markdown("<div class='bento-card'><h3 style='margin-top:0;'>🧠 AI Predictability</h3><p style='color:#6B7280; line-height: 1.6;'>Utilize your historical ledger data and localized physics to accurately forecast daily demand.</p></div>", unsafe_allow_html=True)

    st.write("\n\n")
    st.divider()
    st.write("\n\n")

    # --- Lead Capture Form ---
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
                        payload = {"first_name": l_first, "last_name": l_last, "email": l_email.strip().lower(), "company_name": l_company, "phone": l_phone, "message": l_msg}
                        supabase.table("leads").insert(payload).execute()
                        st.success("✅ Request received! A FloorCast specialist will contact you shortly.")
                    except Exception as e:
                        st.error(f"Submission failed: {e}")
                else:
                    st.error("Please fill in all required (*) fields.")
            st.markdown('</div>', unsafe_allow_html=True)
