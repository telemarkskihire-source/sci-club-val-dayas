# streamlit_app.py
# Sci Club Val d'Ayas · router principale

from __future__ import annotations

import streamlit as st

from seed import init_db_and_seed, get_db
from core.models import User
from ui_admin import render_admin_dashboard
from ui_coach import render_coach_dashboard
from ui_parent import render_parent_dashboard


def get_role_label(role: str) -> str:
    return {
        "admin": "Admin",
        "coach": "Allenatore",
        "parent": "Genitore",
    }.get(role, role)


def main() -> None:
    st.set_page_config(
        page_title="Sci Club Val d'Ayas",
        page_icon="🎿",
        layout="wide",
    )

    init_db_and_seed()
    db = get_db()

    with st.sidebar:
        st.title("Sci Club Val d'Ayas")
        st.write("Seleziona utente (demo):")

        users = db.query(User).order_by(User.role, User.name).all()
        options = {f"{u.name} ({get_role_label(u.role)})": u.id for u in users}
        selected = st.selectbox("Utente", list(options.keys()))
        current_user = db.query(User).get(options[selected])

    st.caption(
        f"Accesso come **{current_user.name}** — Ruolo: **{get_role_label(current_user.role)}**"
    )

    if current_user.role == "admin":
        render_admin_dashboard(db, current_user)
    elif current_user.role == "coach":
        render_coach_dashboard(db, current_user)
    elif current_user.role == "parent":
        render_parent_dashboard(db, current_user)
    else:
        st.error("Ruolo sconosciuto.")

    db.close()


if __name__ == "__main__":
    main()
