# property_settings.py
import streamlit as st

def render_settings_module(supabase, tenant_id, property_name):
    st.markdown(f"<h2 style='color: #111827; margin-bottom: 1rem;'>⚙️ Property Settings</h2>", unsafe_allow_html=True)
    st.write(f"Calibrate the AI predictability engine and operational physics for **{property_name}**.")

    st.markdown("<h4 style='color: #111827; margin-top: 2rem;'>AI Engine Calibration</h4>", unsafe_allow_html=True)
    
    # Fetch Existing Coefficients for this specific property
    try:
        res_coeffs = supabase.table("mt_coefficients").select("*").eq("tenant_id", tenant_id).execute()
        c_data = res_coeffs.data[0] if res_coeffs.data else {}
    except Exception:
        c_data = {}

    with st.form("local_ai_calibration_form", border=False):
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
        if st.form_submit_button("💾 Save DNA to Property Vault", use_container_width=True):
            payload = {
                "tenant_id": tenant_id,
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
                # Upsert ensures it updates their record without creating duplicates
                supabase.table("mt_coefficients").upsert(payload, on_conflict="tenant_id").execute()
                st.success("✅ AI Engine calibrated successfully. All future predictions will use these weights.")
            except Exception as e:
                st.error(f"Vault Sync Failure: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
