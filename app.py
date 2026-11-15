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

# x = st.Page()

pg = st.navigation([home, data, credits])
pg.run()