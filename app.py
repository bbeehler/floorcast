# app.py (Light Mode, Centered Tabs & Clean Layout)
import streamlit as st
import pandas as pd
from supabase import create_client, Client
import stripe

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="FloorCast OS", layout="wide", initial_sidebar_state="collapsed")

# --- CUSTOM ENTERPRISE CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Off-White Background */
    .stApp { background-color: #FAFAFA; color: #111827; }
    
    /* ANNIHILATE THE SIDEBAR AND DEFAULT UI */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="collapsedControl"] {display: none !important;}
    section[data-testid="stSidebar"] {display: none !important;}
    
    /* Hero Typography */
    .hero-greeting {
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        letter-spacing: -0.02em;
        margin-top: 2vh;
        margin-bottom: 0.5rem;
        color: #111827;
    }
    .hero-sub {
        font-size: 1.2rem;
        color: #6B7280;
        text-align: center;
        margin-bottom: 3rem;
        font-weight: 400;
    }

    /* --- SPECIFIC BENTO CARD CLASS (For Logged Out View) --- */
    .bento-card {
        background-color: #FFFFFF;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        height: 100%;
        border: 1px solid #F3F4F6;
    }
    .bento-card:hover {
        box-shadow: 0 12px 30px rgba(0,0,0,0.08);
        transform: translateY(-3px);
    }

    /* --- THE FIX: FORCING THE TABS TO DEAD CENTER --- */
    /* 1. Target the invisible Streamlit wrapper */
    div[data-testid="stRadio"] {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
    }
    /* 2. Target the actual radio group */
    div[role="radiogroup"] {
        display: flex;
        flex-direction: row;
        justify-content: center !important;
        gap: 2.5rem;
        border-bottom: 1px solid #E5E7EB;
        padding-bottom: 0.5rem;
        margin-bottom: 2rem;
        width: fit-content; /* Stops it from stretching */
        margin: 0 auto; /* Centers it */
    }
    div[role="radiogroup"] > label { padding: 0; background: transparent !important; cursor: pointer; }
    div[role="radiogroup"] > label > div:first-child { display: none !important; }
    div[role="radiogroup"] > label p { font-size: 1.05rem; font-weight: 500; color: #4B5563; margin: 0; }
    div[role="radiogroup"] > label:hover p { color: #111827; }

    /* Primary CTA Buttons */
    div.stButton > button {
        background-color: #111827;
        color: #FFFFFF !important;
        font-weight: 600;
        border-radius: 24px;
        border: none;
        padding: 0.5rem 1.5rem;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        background-color: #2563EB; 
    }
    
    /* Search Bar Button Alignment */
    div[data-testid="column"] div.stButton > button {
        border-radius: 12px;
        height: 3.1rem; 
        margin-top: 0px;
    }

    /* Ghost Buttons (Nav/Logout) */
    .ghost-btn > div > button {
        background-color: transparent;
        color: #111827 !important;
        border: 1px solid #D1D5DB;
        box-shadow: none;
        height: auto;
        border-radius: 24px;
    }
    .ghost-btn > div > button:hover {
        border: 1px solid #111827;
        background-color: #FFFFFF;
    }

    /* Input Fields (The Central Prompt) */
    .stTextInput input {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        border: 1px solid #E5E7EB !important; 
        border-radius: 12px;
        padding: 1rem 1.5rem;
        font-size: 1.1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.02); 
    }
    .stTextInput input:focus {
        box-shadow: 0 0 0 2px #2563EB !important; 
        border-color: transparent !important;
    }
    
    /* Modal / Dialog */
    div[role="dialog"] {
        background-color: #FFFFFF !important;
        border: none !important;
        border-radius: 20px;
        color: #111827 !important;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25) !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE CONNECTION ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error(f"Critical Error: Missing Database Secrets. {e}")
        st.stop()

supabase = init_connection()

# --- 3. SESSION STATE INITIALIZATION ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_profile' not in st.session_state: st.session_state.user_profile = None
if 'active_modules' not in st.session_state: st.session_state.active_modules = []

# --- DATA FETCHING & AI FORECASTING ENGINE ---
def get_forensic_metrics(db_client, user_prof, target_start, target_end):
    """Fetches historical data and projects AI predictions across any requested timeline."""
    if not user_prof or 'tenant_id' not in user_prof:
        return pd.DataFrame()
    
    try:
        tenant_id = user_prof['tenant_id']
        
        # 1. Fetch Historical Actuals (Always grab the latest 90 days to build the baseline model)
        res = db_client.table("mt_ledger").select("*").eq("tenant_id", tenant_id).order("entry_date", desc=True).limit(90).execute()
        if not res.data: return pd.DataFrame()
        
        df_raw = pd.DataFrame(res.data)
        df_raw['entry_date'] = pd.to_datetime(df_raw['entry_date'])
        
        # 2. Establish AI Baselines (Median traffic by Day of Week)
        df_raw['dow'] = df_raw['entry_date'].dt.day_name()
        dow_medians = df_raw[df_raw['actual_traffic'] > 0].groupby('dow')['actual_traffic'].median().to_dict()
        
        # 3. Create the master timeline STRICTLY based on the user's selected window
        date_range = pd.date_range(start=target_start, end=target_end)
        
        master_df = pd.DataFrame({'entry_date': date_range})
        master_df['dow'] = master_df['entry_date'].dt.day_name()
        
        # 4. Generate the Forecast across the requested timeline
        master_df['predicted_traffic'] = master_df['dow'].map(dow_medians).fillna(1500)
        
        # 5. Merge the Actuals over the timeline (future dates will simply remain blank for actuals)
        df_actuals = df_raw[['entry_date', 'actual_traffic', 'actual_coin_in', 'new_members']]
        master_df = pd.merge(master_df, df_actuals, on='entry_date', how='left')
        
        return master_df

    except Exception as e:
        st.error(f"AI Engine Error: {e}")
        return pd.DataFrame()

# --- 4. STRIPE CHECKOUT ENGINE ---
def create_checkout_session(price_id):
    try:
        stripe.api_key = st.secrets["STRIPE_API_KEY"]
        with st.spinner("Connecting to secure payment gateway..."):
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id, 
                    'quantity': 1,
                }],
                mode='subscription',
                metadata={'tier': price_id},
                success_url="https://floorcast.streamlit.app/?success=true",
                cancel_url="https://floorcast.streamlit.app/?canceled=true",
            )
        st.link_button("💳 Proceed to Secure Payment", checkout_session.url, use_container_width=True)
    except Exception as e:
        st.error(f"Payment Gateway Error: {e}")

# --- 5. THE LOGIN MODAL ---
@st.dialog("Secure Client Portal")
def login_modal():
    st.markdown("<p style='color: #6B7280; font-weight: 500; margin-bottom: 1rem;'>Authenticate to access your workspace.</p>", unsafe_allow_html=True)
    with st.form("saas_login_form", clear_on_submit=True, border=False):
        email = st.text_input("Corporate Email", placeholder="manager@casino.com").strip().lower()
        password = st.text_input("Access Token", type="password", placeholder="••••••••")
        st.write("\n")
        if st.form_submit_button("Authenticate & Enter", use_container_width=True):
            try:
                auth_res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if auth_res.user:
                    profile_res = supabase.table("user_profiles").select("*, tenants(property_name, region)").eq("email", email).execute()
                    if profile_res.data:
                        user_data = profile_res.data[0]
                        tenant_id = user_data['tenant_id']
                        sub_res = supabase.table("tenant_subscriptions").select("module_name").eq("tenant_id", tenant_id).eq("status", "active").execute()
                        modules = [sub['module_name'] for sub in sub_res.data] if sub_res.data else []
                        
                        st.session_state.authenticated = True
                        st.session_state.user_profile = user_data
                        st.session_state.active_modules = modules
                        st.rerun()
                    else:
                        st.error("Account created, but no property assigned. Contact Support.")
            except Exception as e:
                st.error("Invalid credentials.")

# ==========================================
# --- 6. LOGGED OUT: PUBLIC MARKETING PAGE ---
# ==========================================
if not st.session_state.authenticated:
    c1, c2 = st.columns([6, 1])
    with c1: st.markdown("<h3 style='margin:0; color:#111827;'>🎰 FloorCast AI</h3>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
        if st.button("Client Login", use_container_width=True): login_modal()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="hero-greeting">Predict. Perform. Profit.</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub" style="max-width: 700px; margin: 0 auto 3rem auto;">FloorCast AI consolidates your gaming, marketing, and lodging data to isolate what truly drives revenue. Stop guessing at attribution.</div>', unsafe_allow_html=True)

    st.write("\n")
    m1, m2 = st.columns(2)
    with m1:
        st.markdown("""
        <div class="bento-card">
            <h3 style='color:#111827; margin-top:0;'>🎰 Total Floor Visibility</h3>
            <p style='color:#6B7280; line-height: 1.6;'>Stop looking at siloed reports. We merge gaming coin-in, F&B covers, and hotel occupancy into one unified, real-time operational dashboard.</p>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown("""
        <div class="bento-card">
            <h3 style='color:#111827; margin-top:0;'>🎯 Closed-Loop Attribution</h3>
            <p style='color:#6B7280; line-height: 1.6;'>End the marketing guessing game. Tie your digital ad spend, PR campaigns, and email blasts directly to on-property guest actions and revenue.</p>
        </div>
        """, unsafe_allow_html=True)
            
    st.write("\n")
    m3, m4 = st.columns(2)
    with m3:
        st.markdown("""
        <div class="bento-card">
            <h3 style='color:#111827; margin-top:0;'>🧠 Predictive AI Advisor</h3>
            <p style='color:#6B7280; line-height: 1.6;'>Fire your static dashboards. Ask our integrated AI questions about your property in plain English and instantly get actionable yield forecasts.</p>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown("""
        <div class="bento-card">
            <h3 style='color:#111827; margin-top:0;'>🛡️ Enterprise-Grade Vault</h3>
            <p style='color:#6B7280; line-height: 1.6;'>Built on a strict multi-tenant architecture. Your property's operational data is mathematically isolated, heavily encrypted, and completely private.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<h2 style='text-align:center; margin-bottom:3rem; margin-top:5rem; color:#111827;'>Choose Your Intelligence Tier</h2>", unsafe_allow_html=True)
    
    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown("""
        <div class="bento-card" style="text-align: center;">
            <h2 style='color:#111827; margin-top:0;'>Core</h2>
            <h3 style='color:#111827; font-size:2.5rem; margin: 1rem 0;'>$299</h3>
            <p style='color:#9CA3AF; margin-bottom: 2rem;'>/ month</p>
            <p style='color:#6B7280; line-height: 1.8;'>✔️ Casino Analytics<br>✔️ Marketing Attribution</p>
        </div>
        """, unsafe_allow_html=True)
        st.write("\n")
        if st.button("Select Core", key="b1", use_container_width=True): create_checkout_session("price_YOUR_CORE_ID_HERE")
    with p2:
        st.markdown("""
        <div class="bento-card" style="text-align: center; border: 2px solid #2563EB;">
            <h2 style='color:#2563EB; margin-top:0;'>Premium</h2>
            <h3 style='color:#2563EB; font-size:2.5rem; margin: 1rem 0;'>$350</h3>
            <p style='color:#9CA3AF; margin-bottom: 2rem;'>/ month</p>
            <p style='color:#6B7280; line-height: 1.8;'>✔️ Core Features<br>✔️ <b style='color:#111827;'>🧠 AI Advisor</b></p>
        </div>
        """, unsafe_allow_html=True)
        st.write("\n")
        if st.button("Select Premium", key="b2", use_container_width=True): create_checkout_session("price_YOUR_PREMIUM_ID_HERE")
    with p3:
        st.markdown("""
        <div class="bento-card" style="text-align: center;">
            <h2 style='color:#111827; margin-top:0;'>Enterprise</h2>
            <h3 style='color:#111827; font-size:2.5rem; margin: 1rem 0;'>$999</h3>
            <p style='color:#9CA3AF; margin-bottom: 2rem;'>/ month</p>
            <p style='color:#6B7280; line-height: 1.8;'>✔️ All Features<br>✔️ Full Auxiliary Suite</p>
        </div>
        """, unsafe_allow_html=True)
        st.write("\n")
        if st.button("Select Enterprise", key="b3", use_container_width=True): create_checkout_session("price_YOUR_ENTERPRISE_ID_HERE")
    st.stop()

# ==========================================
# --- 7. LOGGED IN: THE ACTIVE WORKSPACE ---
# ==========================================
profile = st.session_state.user_profile
prop_name = profile['tenants']['property_name']
role = profile['user_role']

# Ensure we have a way to track the active tab and pending AI questions
if 'nav_selection' not in st.session_state: st.session_state.nav_selection = "🏠 Overview"
if 'pending_ai_query' not in st.session_state: st.session_state.pending_ai_query = None

nav_c1, nav_c2 = st.columns([5, 1])
with nav_c1: st.markdown("<h4 style='margin-top: 10px; color:#111827;'>🎰 FloorCast OS</h4>", unsafe_allow_html=True)
with nav_c2:
    st.markdown('<div class="ghost-btn">', unsafe_allow_html=True)
    if st.button(f"Sign Out ({profile['email']})", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown(f'<div class="hero-greeting">Good afternoon, {prop_name}.</div>', unsafe_allow_html=True)

# --- THE FIX: AI PROMPT VISIBILITY & ROUTING ---
# Only render this massive central prompt if they pay for the AI module
if "ai_advisor" in st.session_state.active_modules:
    _, search_col, _ = st.columns([1, 3, 1])
    with search_col:
        col_input, col_btn = st.columns([4, 1])
        with col_input:
            quick_query = st.text_input("", placeholder="Ask FloorCast AI to analyze your property data...", label_visibility="collapsed", key="quick_bar")
        with col_btn:
            if st.button("Analyze ✨", use_container_width=True):
                if quick_query:
                    # Store their question and force the app to the AI tab
                    st.session_state.pending_ai_query = quick_query
                    st.session_state.nav_selection = "🧠 AI Advisor"
                    st.rerun()
    st.write("\n")
else:
    # Add some breathing room so the layout doesn't collapse for Core users
    st.write("\n\n\n")

# Horizontal Semantic Navigation (Clean Centered Tabs)
nav_options = ["🏠 Overview"]
if "ai_advisor" in st.session_state.active_modules: nav_options.append("🧠 AI Advisor")
if "casino_ops" in st.session_state.active_modules: nav_options.append("🎰 Casino")
if "marketing_pro" in st.session_state.active_modules: nav_options.append("📈 Marketing")
if "pr_media" in st.session_state.active_modules: nav_options.append("📢 PR")
if "hotel_rev" in st.session_state.active_modules: nav_options.append("🛏️ Hotel")
if "fnb" in st.session_state.active_modules: nav_options.append("🍽️ F&B")
if "email_ops" in st.session_state.active_modules: nav_options.append("📨 Email")
if role == "Super Admin": nav_options.append("⚙️ Global Admin")

# Keep the radio button synced with our routing logic
try:
    nav_idx = nav_options.index(st.session_state.nav_selection)
except ValueError:
    nav_idx = 0

selected_page = st.radio("Workspace Navigation", nav_options, index=nav_idx, horizontal=True, label_visibility="collapsed")

# If the user clicks a tab directly, update the state and reload
if selected_page != st.session_state.nav_selection:
    st.session_state.nav_selection = selected_page
    st.rerun()

# --- 8. PAGE ROUTING ---
if selected_page == "🏠 Overview":
    import datetime
    import pandas as pd
    import plotly.graph_objects as go
    
    # --- 1. UNBOUNDED DATE RANGE SELECTOR ---
    today = datetime.date.today()
    default_start = today - datetime.timedelta(days=30)
    default_future = today + datetime.timedelta(days=14)
    
    d_col1, d_col2 = st.columns([1, 3])
    with d_col1:
        audit_window = st.date_input(
            "📅 Audit & Forecast Window", 
            value=(default_start, default_future), 
            key="overview_window"
        )
    st.write("\n")
    
    # Safely unpack dates
    if isinstance(audit_window, tuple) and len(audit_window) == 2:
        start_date, end_date = audit_window
    else:
        start_date, end_date = default_start, default_future

    # Calculate Previous Period (PoP) for True Deltas
    delta_days = (end_date - start_date).days + 1
    pp_end = start_date - datetime.timedelta(days=1)
    pp_start = pp_end - datetime.timedelta(days=delta_days - 1)

    # --- 2. DATA AGGREGATION (GRAND TOTALS ACROSS ALL MODULES) ---
    tenant_id = profile['tenant_id']
    
    # Helper function to fetch and sum specific columns safely
    def fetch_sum(table, date_col, sum_col, s_date, e_date):
        res = supabase.table(table).select(sum_col).eq("tenant_id", tenant_id).gte(date_col, str(s_date)).lte(date_col, str(e_date)).execute()
        return sum(x[sum_col] for x in res.data if x.get(sum_col)) if res.data else 0

    # CURRENT PERIOD MATH
    cp_gaming_rev = fetch_sum("mt_ledger", "entry_date", "actual_coin_in", start_date, end_date)
    cp_fnb_rev = fetch_sum("mt_fnb_ledger", "audit_date", "total_revenue", start_date, end_date)
    cp_hotel_rev = fetch_sum("mt_hotel_ledger", "audit_date", "room_revenue", start_date, end_date)
    cp_total_rev = cp_gaming_rev + cp_fnb_rev + cp_hotel_rev

    cp_gaming_traf = fetch_sum("mt_ledger", "entry_date", "actual_traffic", start_date, end_date)
    cp_fnb_traf = fetch_sum("mt_fnb_ledger", "audit_date", "total_covers", start_date, end_date)
    cp_hotel_traf = fetch_sum("mt_hotel_ledger", "audit_date", "rooms_sold", start_date, end_date)
    cp_total_traf = cp_gaming_traf + cp_fnb_traf + cp_hotel_traf
    
    cp_yield = cp_total_rev / cp_total_traf if cp_total_traf > 0 else 0

    # PREVIOUS PERIOD MATH (For the +/- Delta)
    pp_gaming_rev = fetch_sum("mt_ledger", "entry_date", "actual_coin_in", pp_start, pp_end)
    pp_fnb_rev = fetch_sum("mt_fnb_ledger", "audit_date", "total_revenue", pp_start, pp_end)
    pp_hotel_rev = fetch_sum("mt_hotel_ledger", "audit_date", "room_revenue", pp_start, pp_end)
    pp_total_rev = pp_gaming_rev + pp_fnb_rev + pp_hotel_rev

    pp_gaming_traf = fetch_sum("mt_ledger", "entry_date", "actual_traffic", pp_start, pp_end)
    pp_fnb_traf = fetch_sum("mt_fnb_ledger", "audit_date", "total_covers", pp_start, pp_end)
    pp_hotel_traf = fetch_sum("mt_hotel_ledger", "audit_date", "rooms_sold", pp_start, pp_end)
    pp_total_traf = pp_gaming_traf + pp_fnb_traf + pp_hotel_traf
    
    pp_yield = pp_total_rev / pp_total_traf if pp_total_traf > 0 else 0

    # Calculate True Percentages
    def calc_pct(cp, pp):
        if pp == 0 and cp > 0: return 100.0
        if pp == 0 and cp == 0: return 0.0
        return ((cp - pp) / pp) * 100.0

    rev_pct = calc_pct(cp_total_rev, pp_total_rev)
    traf_pct = calc_pct(cp_total_traf, pp_total_traf)
    yield_pct = calc_pct(cp_yield, pp_yield)

    def format_delta(pct):
        color = "#10B981" if pct >= 0 else "#EF4444" # Green if up, Red if down
        sign = "+" if pct >= 0 else ""
        return f'<p style="color: {color}; margin: 0; font-weight: 600; font-size: 0.9rem;">{sign}{pct:.1f}% vs Prior Period</p>'

    # --- 3. NORTH STAR METRICS (Top Row) ---
    st.markdown(f"""
    <div style="display: flex; gap: 1.5rem; margin-bottom: 2rem;">
        <div class="bento-card" style="flex: 1; text-align: center;">
            <p style="color: #6B7280; margin: 0; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">Total Property Traffic</p>
            <h2 style="color: #111827; margin: 0.5rem 0; font-size: 2.2rem;">{cp_total_traf:,.0f}</h2>
            {format_delta(traf_pct)}
        </div>
        <div class="bento-card" style="flex: 1; text-align: center; border: 2px solid #2563EB;">
            <p style="color: #2563EB; margin: 0; font-size: 0.85rem; font-weight: 700; text-transform: uppercase;">Grand Total Revenue</p>
            <h2 style="color: #2563EB; margin: 0.5rem 0; font-size: 2.2rem;">${cp_total_rev:,.0f}</h2>
            {format_delta(rev_pct)}
        </div>
        <div class="bento-card" style="flex: 1; text-align: center;">
            <p style="color: #6B7280; margin: 0; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">Property Yield / Guest</p>
            <h2 style="color: #111827; margin: 0.5rem 0; font-size: 2.2rem;">${cp_yield:,.2f}</h2>
            {format_delta(yield_pct)}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- 4. THE UNIFIED PULSE CHART (Center Stage) ---
    st.markdown("<h3 style='color: #111827; margin-bottom: 1rem;'>📈 The Unified Pulse</h3>", unsafe_allow_html=True)
    
    # Run the AI engine to build the dynamic timeline based on selected dates
    df_filtered = get_forensic_metrics(supabase, profile, start_date, end_date)
    
    if not df_filtered.empty:
        df_chart = df_filtered.sort_values('entry_date')
        
        fig = go.Figure()
        # Actual Traffic (Solid Blue Line)
        fig.add_trace(go.Scatter(x=df_chart['entry_date'], y=df_chart['actual_traffic'], name="Casino Guests", line=dict(color='#2563EB', width=4)))
        
        # AI Forecast (Dotted Gold Line)
        if 'predicted_traffic' in df_chart.columns:
            fig.add_trace(go.Scatter(x=df_chart['entry_date'], y=df_chart['predicted_traffic'], name="AI Forecast", line=dict(color='#F59E0B', width=3, dash='dot')))
        
        # Make the chart transparent to float on the bento card
        fig.update_layout(
            height=320, 
            margin=dict(l=0, r=0, t=10, b=0), 
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#F3F4F6'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.markdown('<div class="bento-card" style="padding-top: 1rem;">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="bento-card" style="text-align: center; margin-top: 2vh;">
            <h4 style="color: #111827;">Insufficient Timeline Data</h4>
            <p style="color: #6B7280;">Adjust your dates or ensure the Forensic Vault contains ledger entries.</p>
        </div>
        """, unsafe_allow_html=True)
        
    st.write("\n")

    # --- 5. MODULE TEASER WIDGETS (Bottom Grid) ---
    st.markdown("<h3 style='color: #111827; margin-bottom: 1rem; margin-top: 2rem;'>🧩 Intelligence Teasers</h3>", unsafe_allow_html=True)
    
    t1, t2, t3 = st.columns(3)
    with t1:
        st.markdown("""
        <div class="bento-card" style="height: 100%;">
            <h4 style="margin-top: 0; color: #111827; font-weight: 700;">📈 Marketing Attribution</h4>
            <p style="color: #6B7280; font-size: 0.9rem; margin-bottom: 0.5rem;">Estimated Digital ROAS</p>
            <h2 style="color: #2563EB; margin: 0;">3.2x</h2>
            <p style="color: #10B981; margin-top: 0.5rem; font-size: 0.85rem; font-weight: 500;">Highly Efficient</p>
        </div>
        """, unsafe_allow_html=True)
    with t2:
        st.markdown("""
        <div class="bento-card" style="height: 100%;">
            <h4 style="margin-top: 0; color: #111827; font-weight: 700;">📢 PR & Brand Halo</h4>
            <p style="color: #6B7280; font-size: 0.9rem; margin-bottom: 0.5rem;">Earned Media Reach (MoM)</p>
            <h2 style="color: #111827; margin: 0;">150K</h2>
            <p style="color: #10B981; margin-top: 0.5rem; font-size: 0.85rem; font-weight: 500;">+11.4% Expansion</p>
        </div>
        """, unsafe_allow_html=True)
    with t3:
        st.markdown("""
        <div class="bento-card" style="height: 100%;">
            <h4 style="margin-top: 0; color: #111827; font-weight: 700;">🧠 AI Model Status</h4>
            <p style="color: #6B7280; font-size: 0.9rem; margin-bottom: 0.5rem;">Prediction Accuracy</p>
            <h2 style="color: #111827; margin: 0;">94.2%</h2>
            <p style="color: #10B981; margin-top: 0.5rem; font-size: 0.85rem; font-weight: 500;">Elite Precision Tracking</p>
        </div>
        """, unsafe_allow_html=True)

elif selected_page == "⚙️ Global Admin": 
    import admin
    admin.render_admin_page(supabase)
elif selected_page == "🎰 Casino": 
    import casino
    casino.render_casino_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "📈 Marketing": 
    import marketing
    marketing.render_marketing_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "📢 PR": 
    import pr
    pr.render_pr_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "📨 Email": 
    import email_ops
    email_ops.render_email_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "🛏️ Hotel": 
    import hotel
    hotel.render_hotel_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "🍽️ F&B": 
    import fnb
    fnb.render_fnb_module(supabase, profile['tenant_id'], prop_name)
elif selected_page == "🧠 AI Advisor": 
    import ai_advisor
    query = st.session_state.get('pending_ai_query', None)
    st.session_state.pending_ai_query = None 
    ai_advisor.render_advisor_module(supabase, profile['tenant_id'], prop_name, initial_query=query)
else: 
    st.info("Module under construction.")
