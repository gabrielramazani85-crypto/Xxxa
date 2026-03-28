import streamlit as st
import sqlite3
from streamlit_autorefresh import st_autorefresh   # <-- importer correctement

# --- Connexion à la base ---
conn = sqlite3.connect("restaurant.db")
c = conn.cursor()

# --- Création des tables ---
c.execute("""CREATE TABLE IF NOT EXISTS menu (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plat TEXT,
    prix REAL,
    photo TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS commandes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plat TEXT,
    quantite INTEGER,
    statut TEXT,
    paiement TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auteur TEXT,
    contenu TEXT,
    role TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,
    contenu TEXT
)""")
conn.commit()

# --- Auto-refresh toutes les 5 secondes ---
st_autorefresh(interval=5000, key="refresh")

# --- Choix du rôle ---
role = st.sidebar.radio("Rôle :", ["Client", "Admin"])

# --- Navigation ---
page = st.sidebar.radio("Navigation :", ["Menu", "Commandes", "Chat", "Statistiques"])

# --- Notifications par catégorie ---
st.sidebar.subheader("🛎️ Notifications")
types = ["Messages", "Commandes", "Paiements", "Menu"]
for t in types:
    notifs = c.execute("SELECT contenu FROM notifications WHERE type=? ORDER BY id DESC LIMIT 3", (t,)).fetchall()
    st.sidebar.write(f"**{t}**")
    for n in notifs:
        st.sidebar.write(f"- {n[0]}")

# --- PAGE MENU ---
if page == "Menu":
    st.title("🍽️ Menu du jour")
    menu_items = c.execute("SELECT * FROM menu").fetchall()
    for item in menu_items:
        st.image(item[3], width=150)
        st.write(f"{item[1]} - {item[2]} $")

    if role == "Admin":
        st.subheader("Gestion du menu")
        plat = st.text_input("Nom du plat")
        prix = st.number_input("Prix", min_value=0.0, step=0.5)
        photo = st.text_input("Chemin/URL de la photo")
        if st.button("Ajouter/Modifier"):
            c.execute("INSERT INTO menu (plat, prix, photo) VALUES (?, ?, ?)", (plat, prix, photo))
            c.execute("INSERT INTO notifications (type, contenu) VALUES (?, ?)", ("Menu", f"Plat ajouté/modifié : {plat}"))
            conn.commit()
            st.success(f"{plat} ajouté au menu 🔔")

# --- PAGE COMMANDES ---
elif page == "Commandes":
    st.title("🛒 Commandes")
    menu_items = c.execute("SELECT * FROM menu").fetchall()
    choix = st.selectbox("Choisissez un plat", [item[1] for item in menu_items])
    quantite = st.number_input("Quantité", min_value=1, step=1)
    if st.button("Commander"):
        c.execute("INSERT INTO commandes (plat, quantite, statut, paiement) VALUES (?, ?, ?, ?)",
                  (choix, quantite, "en attente", None))
        c.execute("INSERT INTO notifications (type, contenu) VALUES (?, ?)", ("Commandes", f"Nouvelle commande : {choix} x{quantite}"))
        conn.commit()
        st.success(f"Commande enregistrée : {choix} x{quantite} 🔔")

    if role == "Admin":
        st.subheader("Gestion des paiements")
        commandes = c.execute("SELECT * FROM commandes").fetchall()
        for cmd in commandes:
            st.write(f"{cmd[0]} - {cmd[1]} x{cmd[2]} | Statut : {cmd[3]} | Paiement : {cmd[4]}")
            mode = st.selectbox("Mode de paiement", ["Mobile Money", "Carte", "Cash"], key=f"pay{cmd[0]}")
            if st.button(f"Valider paiement {cmd[0]}"):
                c.execute("UPDATE commandes SET statut=?, paiement=? WHERE id=?", ("payé", mode, cmd[0]))
                c.execute("INSERT INTO notifications (type, contenu) VALUES (?, ?)", ("Paiements", f"Commande {cmd[0]} payée via {mode}"))
                conn.commit()
                st.success(f"Commande {cmd[0]} payée ✅")

# --- PAGE CHAT ---
elif page == "Chat":
    st.title("💬 Discussion")
    messages = c.execute("SELECT auteur, contenu, role FROM messages ORDER BY id DESC LIMIT 10").fetchall()
    for msg in reversed(messages):
        if msg[2] == "Admin":
            st.markdown(f"**👨‍🍳 {msg[0]} (Admin)** : {msg[1]}")
        else:
            st.markdown(f"**🧑‍💼 {msg[0]} (Client)** : {msg[1]}")

    st.subheader("Envoyer un message")
    auteur = st.text_input("Votre nom")
    contenu = st.text_area("Message")
    if st.button("Envoyer"):
        if auteur and contenu:
            c.execute("INSERT INTO messages (auteur, contenu, role) VALUES (?, ?, ?)", (auteur, contenu, role))
            c.execute("INSERT INTO notifications (type, contenu) VALUES (?, ?)", ("Messages", f"Nouveau message de {auteur}"))
            conn.commit()
            st.success("Message envoyé 🔔")
        else:
            st.warning("Veuillez remplir tous les champs.")

# --- PAGE STATISTIQUES ---
elif page == "Statistiques":
    st.title("📊 Statistiques")
    total = c.execute("""
        SELECT SUM(menu.prix * commandes.quantite)
        FROM commandes
        JOIN menu ON commandes.plat = menu.plat
        WHERE commandes.statut='payé'
    """).fetchone()[0]
    st.metric("💰 Chiffre d'affaires", f"{total if total else 0} $")

    best = c.execute("""
        SELECT plat, SUM(quantite) 
        FROM commandes 
        GROUP BY plat 
        ORDER BY SUM(quantite) DESC LIMIT 1
    """).fetchone()
    if best:
        st.metric("🥇 Plat le plus vendu", f"{best[0]} ({best[1]} ventes)")

    st.subheader("📦 Commandes par statut")
    statuts = c.execute("SELECT statut, COUNT(*) FROM commandes GROUP BY statut").fetchall()
    for s in statuts:
        st.write(f"- {s[0]} : {s[1]}")

    st.subheader("📈 Historique des commandes")
    commandes = c.execute("SELECT id, plat, quantite, statut, paiement FROM commandes ORDER BY id DESC LIMIT 10").fetchall()
    for cmd in commandes:
        st.write(f"{cmd[0]} - {cmd[1]} x{cmd[2]} | Statut : {cmd[3]} | Paiement : {cmd[4]}")