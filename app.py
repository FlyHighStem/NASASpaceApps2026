import streamlit as st

home = st.Page(
    "home.py",
    title="Home",
    default=True
)

data = st.Page(
    "pages/data.py",
    title="Data"
)

credits = st.Page(
    "pages/credits.py",
    title="Credits"
)

methods = st.Page(
    "pages/methods.py",
        title="Methods"
)

pg = st.navigation([home, data, methods, credits])
pg.run()