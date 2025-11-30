# core/ui_admin.py
from datetime import date

import streamlit as st
from sqlalchemy.orm import Session

from .models import User, Category, Athlete, Event


def render_admin_dashboard(db: Session, user: User) -> None:
    st.header("Pannello Admin")
    st.write("Dashboard riassuntiva del club")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Utenti", db.query(User).count())
    col2.metric("Categorie", db.query(Category).count())
    col3.metric("Atleti", db.query(Athlete).count())
    col4.metric("Eventi", db.query(Event).count())

    today = date.today()
    events = (
        db.query(Event)
        .filter(Event.date >= today)
        .order_by(Event.date.asc())
        .all()
    )

    st.subheader("Prossimi eventi")
    if not events:
        st.info("Nessun evento futuro.")
        return

    for ev in events:
        st.markdown(f"**{ev.date} — {ev.title}**")
        if ev.description:
            st.caption(ev.description)
        st.divider()
