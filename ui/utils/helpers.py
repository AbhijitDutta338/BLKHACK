import streamlit as st


def render_response(status, data):
    st.write("Status Code:", status)

    if status >= 400:
        st.error("Request failed")
    else:
        st.success("Request successful")

    st.json(data)