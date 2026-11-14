g = st.sidebar.multiselect("Evidence grade", list("ABCD"), ["A", "B"]); d = df[df.grade.isin(g)]
