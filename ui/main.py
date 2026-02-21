import streamlit as st
from pages import dashboard

st.set_page_config(page_title="Investor Intelligence", layout="wide")
dashboard.render()