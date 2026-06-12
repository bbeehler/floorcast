# hotel.py
import streamlit as st
import pandas as pd
import datetime

def render_hotel_module(supabase, tenant_id, property_name):
    st.title("🛏️ Hotel & Booking")
    st.write(f"Revenue management and occupancy tracking for **{property_name}**.")

    tabs = st.tabs(["📊 RevPAR Dashboard", "📝 Daily Audit Entry"])

    # --- TAB 1: DASHBOARD ---
    with tabs[0]:
        res = supabase.table("mt_hotel_ledger").select("*").eq("tenant_id", tenant_id).order("audit_date", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            total_rev = df['room_revenue'].sum()
            total_sold = df['rooms_sold'].sum()
            total_avail = df['rooms_available'].sum()

            occ = (total_sold / total_avail * 100) if total_avail > 0 else 0
            adr = (total_rev / total_sold) if total_sold > 0 else 0
            revpar = (total_rev / total_avail) if total_avail > 0 else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("Occupancy", f"{occ:.1f}%")
            c2.metric("ADR (Avg Daily Rate)", f"${adr:.2f}")
            c3.metric("RevPAR", f"${revpar:.2f}")

            st.divider()
            display_df = df[['audit_date', 'rooms_available', 'rooms_sold', 'room_revenue']].copy()
            display_df['room_revenue'] = display_df['room_revenue'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No hotel data found. Run your first daily audit in the next tab.")

    # --- TAB 2: DATA ENTRY ---
    with tabs[1]:
        with st.form("hotel_form", clear_on_submit=True):
            a_date = st.date_input("Audit Date", value=datetime.date.today())
            c1, c2, c3 = st.columns(3)
            with c1: r_avail = st.number_input("Rooms Available", min_value=1, step=10)
            with c2: r_sold = st.number_input("Rooms Sold", min_value=0, step=10)
            with c3: r_rev = st.number_input("Room Revenue ($)", min_value=0.0, step=1000.0)

            if st.form_submit_button("💾 Vault Hotel Data", use_container_width=True):
                payload = {"tenant_id": tenant_id, "audit_date": str(a_date), "rooms_available": r_avail, "rooms_sold": r_sold, "room_revenue": r_rev}
                try:
                    supabase.table("mt_hotel_ledger").upsert(payload, on_conflict="tenant_id, audit_date").execute()
                    st.success("Hotel night audit vaulted!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving: {e}")
