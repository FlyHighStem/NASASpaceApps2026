import streamlit as st

home = st.Page("home.py", title="Home", default=True)
data = st.Page("pages/data.py", title="Data")
methods = st.Page("pages/methods.py", title="Methods")
crosscheck = st.Page("pages/cross_check.py", title="Cross-check")
credits = st.Page("pages/credits.py", title="Credits")

pg = st.navigation([home, data, methods, crosscheck, credits])
pg.run()
