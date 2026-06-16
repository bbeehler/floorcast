# ai_advisor.py
import streamlit as st
import pandas as pd
import google.generativeai as genai

def render_advisor_module(supabase, tenant_id, property_name, initial_query=None):
    st.title("🧠 FloorCast AI Advisor")
    st.write(f"Ask questions about your data, trends, and predictive models for **{property_name}**.")

    # 1. Initialize the AI
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error("AI Configuration Error. Please check your API key secrets.")
        return

    # 2. Gather the Property Data (Context Building)
    @st.cache_data(ttl=3600)
    def fetch_property_context(t_id):
        context_string = f"You are the FloorCast AI Advisor for a casino property named {property_name}. "
        context_string += "Analyze the following recent data to answer the user's questions clearly and directly. "
        
        # Pull Casino & Marketing Ledger Data
        res = supabase.table("mt_ledger").select("*").eq("tenant_id", t_id).order("entry_date", desc=True).limit(30).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            total_traffic = df['actual_traffic'].sum()
            total_coin = df['actual_coin_in'].sum()
            context_string += f"Over the last 30 entries, total traffic was {total_traffic} and total coin-in was ${total_coin:,.2f}. "
            context_string += f"Raw daily data: {df.to_dict('records')}"
            
        return context_string

    system_context = fetch_property_context(tenant_id)

    # 3. State Setup
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 4. Handle incoming query from the Home page
    if initial_query and not st.session_state.messages:
        st.session_state.messages.append({"role": "user", "content": initial_query})
        
        # Immediate auto-trigger
        with st.chat_message("assistant"):
            with st.spinner("Analyzing property data..."):
                try:
                    full_prompt = f"{system_context}\n\nUser Question: {initial_query}"
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"Failed to generate response: {e}")

    # 5. Render existing messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 6. Chat Input
    if prompt := st.chat_input("Ask FloorCast AI a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing property data..."):
                try:
                    full_prompt = f"{system_context}\n\nUser Question: {prompt}"
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"Failed to generate response: {e}")
