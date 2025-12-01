# streamlit_app.py
# Sci Club Val d'Ayas · main con pagina login + ruoli

from __future__ import annotations

import streamlit as st

from seed import init_db_and_seed, get_db
from core.models import User
from ui_admin import render_admin_dashboard
from ui_coach import render_coach_dashboard
from ui_parent import render_parent_dashboard


# ---------- UTILS ----------

def get_role_label(role: str) -> str:
    return {
        "admin": "Admin",
        "coach": "Allenatore",
        "parent": "Genitore",
    }.get(role, role)


def get_current_user(db) -> User:
    """
    Gestisce il login:
    - se c'è current_user_id in session_state, restituisce l'utente
    - altrimenti mostra la schermata di login
    """

    # Utente già loggato?
    if "current_user_id" in st.session_state:
        user = db.query(User).get(st.session_state["current_user_id"])
        if user:
            return user
        # se non esiste più, azzero la sessione
        st.session_state.pop("current_user_id", None)

    # --- Schermata di login ---
    st.title("Sci Club Val d'Ayas")
    st.subheader("Accesso")

    users = db.query(User).order_by(User.role, User.name).all()
    if not users:
        st.error("Nessun utente definito. Accedi come admin e crea gli utenti.")
        st.stop()

    options = {f"{u.name} ({get_role_label(u.role)})": u.id for u in users}
    labels = list(options.keys())

    selected_label = st.selectbox("Seleziona utente (demo login)", labels)

    if st.button("Entra"):
        st.session_state["current_user_id"] = options[selected_label]
        st.rerun()  # nuova API, niente experimental

    # finché non clicchi Entra, non c'è un utente corrente
    st.stop()


# ---------- MAIN APP ----------

def main() -> None:
    st.set_page_config(
        page_title="Sci Club Val d'Ayas",
        page_icon="🎿",
        layout="wide",
    )

    # Inizializza DB e dati demo
    init_db_and_seed()
    db = get_db()

    # Login / selezione utente
    current_user = get_current_user(db)

    # Sidebar con info utente + logout
    with st.sidebar:
        st.title("Sci Club Val d'Ayas")
        st.caption(
            f"Accesso come **{current_user.name}** "
            f"({get_role_label(current_user.role)})"
        )
        if st.button("Logout"):
            st.session_state.pop("current_user_id", None)
            st.rerun()

    # Contenuto principale per ruolo
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
