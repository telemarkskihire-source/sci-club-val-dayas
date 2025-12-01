def _render_events_view(db: Session, user: User, athletes, cat_ids):
    today = date.today()
    events = (
        db.query(Event)
        .filter(Event.category_id.in_(cat_ids), Event.date >= today)
        .order_by(Event.date.asc())
        .all()
    )

    if not events:
        st.subheader("Prossimi eventi per i tuoi figli")
        st.info("Nessun evento futuro.")
        return

    st.subheader("Prossimi eventi per i tuoi figli")

    categories = db.query(Category).filter(Category.id.in_(cat_ids)).all()
    cat_map = {c.id: c for c in categories}

    for ev in events:
        cat = cat_map.get(ev.category_id)
        is_race = ev.type == "race"

        with st.expander(
            f"{ev.date} · {ev.title} "
            f"({cat.name if cat else '-'}) "
            f"- {'Gara' if is_race else 'Allenamento'}",
            expanded=False,
        ):
            if ev.description:
                st.caption(ev.description)
            if ev.location:
                st.caption(f"Località: {ev.location}")

            if ev.ask_skiroom:
                st.caption("👉 L'allenatore ha chiesto di lasciare gli sci in ski-room.")
            if is_race and ev.ask_carpool:
                st.caption("👉 L'allenatore ha chiesto di indicare se siete automuniti.")

            for ath in athletes:
                if ath.category_id != ev.category_id:
                    continue

                att = (
                    db.query(EventAttendance)
                    .filter(
                        EventAttendance.event_id == ev.id,
                        EventAttendance.athlete_id == ath.id,
                    )
                    .first()
                )

                if att is None:
                    att = EventAttendance(
                        event_id=ev.id,
                        athlete_id=ath.id,
                        status="undecided",
                    )
                    db.add(att)
                    db.commit()

                st.markdown(f"#### {ath.name}")

                col1, col2 = st.columns([2, 1])

                current_status_label = status_label_map.get(
                    att.status, "Da confermare"
                )

                with col1:
                    chosen_label = st.radio(
                        "Presenza",
                        options=list(status_label_map.values()),
                        index=list(status_label_map.values()).index(
                            current_status_label
                        ),
                        key=f"status_{ev.id}_{ath.id}",
                        horizontal=True,
                    )

                    # Sci in ski-room solo se il coach lo ha richiesto
                    skis_flag = att.skis_in_skiroom
                    if ev.ask_skiroom:
                        skis_flag = st.checkbox(
                            "Sci in ski-room",
                            value=att.skis_in_skiroom,
                            key=f"skiroom_{ev.id}_{ath.id}",
                        )

                # Auto solo per gare + richiesta coach
                car_flag = att.car_available
                car_seats = att.car_seats or 0

                if is_race and ev.ask_carpool:
                    with col2:
                        car_flag = st.checkbox(
                            "Automunito",
                            value=att.car_available,
                            key=f"car_{ev.id}_{ath.id}",
                        )
                        if car_flag:
                            car_seats = st.number_input(
                                "Posti liberi auto",
                                min_value=0,
                                max_value=8,
                                step=1,
                                value=car_seats,
                                key=f"seats_{ev.id}_{ath.id}",
                            )
                        else:
                            car_seats = 0
                else:
                    car_flag = False
                    car_seats = 0

                if st.button("Salva", key=f"save_{ev.id}_{ath.id}"):
                    att.status = reverse_status_map[chosen_label]
                    att.skis_in_skiroom = skis_flag
                    att.car_available = car_flag if (is_race and ev.ask_carpool) else False
                    att.car_seats = car_seats if (is_race and ev.ask_carpool) else 0

                    att.updated_by = user.id
                    att.updated_at = datetime.utcnow()

                    db.commit()
                    st.success("Dati aggiornati per questo atleta.")

            st.markdown("---")
