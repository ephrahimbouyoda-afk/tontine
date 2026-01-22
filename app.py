import flet as ft
import database as db

def main(page: ft.Page):
    page.title = "Tontine Pro"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = "auto"

    db.init_db()

    # --- ÉLÉMENTS UI ---
    txt_solde = ft.Text("0 FCFA", size=40, weight="bold", color="blue900")
    liste_membres_ui = ft.Column()
    input_nom = ft.TextField(label="Nom du membre", width=250)
    drop_membres = ft.Dropdown(label="Choisir le membre", width=250)
    input_montant = ft.TextField(label="Montant (FCFA)", width=250)
    liste_tours_ui = ft.Column()
    table_historique = ft.DataTable(
        columns=[ft.DataColumn(ft.Text("Membre")), ft.DataColumn(ft.Text("Montant")), ft.DataColumn(ft.Text("Date"))],
        rows=[]
    )

    def rafraichir_tout():
        conn = db.get_db_connection()
        cursor = conn.cursor()
        try:
            # 1. Solde
            cursor.execute("SELECT type, montant FROM transactions")
            total = sum(row['montant'] if row['type'] == 'ENTREE' else -row['montant'] for row in cursor.fetchall())
            txt_solde.value = f"{total:,.0f} FCFA".replace(",", " ")

            # 2. Liste Membres
            totaux = db.obtenir_totaux_membres(conn)
            liste_membres_ui.controls = [ft.Text(f"👤 {row['nom']} : {row['total'] or 0} FCFA") for row in totaux]

            # 3. Dropdown
            membres = db.lister_membres(conn)
            drop_membres.options = [ft.dropdown.Option(m) for m in membres]

            # 4. Historique
            historique = db.obtenir_historique_complet(conn)
            table_historique.rows = [
                ft.DataRow(cells=[ft.DataCell(ft.Text(row['nom'])), ft.DataCell(ft.Text(f"{row['montant']} FCFA")), ft.DataCell(ft.Text(row['date']))])
                for row in historique
            ]

            # 5. Calendrier
            cursor.execute("SELECT membres.nom, calendrier.mois FROM calendrier JOIN membres ON calendrier.membre_id = membres.id")
            tours = cursor.fetchall()
            liste_tours_ui.controls = [ft.Text(f"📅 {t['mois']} : {t['nom']}") for t in tours]

        finally:
            conn.close()
            page.update()

    # --- ACTIONS ---
    def ajouter_clic(e):
        if input_nom.value:
            conn = db.get_db_connection()
            db.ajouter_membre(conn, input_nom.value)
            input_nom.value = ""
            conn.close()
            rafraichir_tout()

    def encaisser_clic(e):
        if drop_membres.value and input_montant.value:
            conn = db.get_db_connection()
            db.enregistrer_paiement(conn, drop_membres.value, float(input_montant.value))
            input_montant.value = ""
            conn.close()
            rafraichir_tout()

    # --- AFFICHAGE ---
    page.add(
        ft.Text("TONTINE PRO - DASHBOARD", size=30, weight="bold"),
        txt_solde,
        ft.Divider(),
        ft.Text("AJOUTER MEMBRE"),
        ft.Row([input_nom, ft.ElevatedButton("VALIDER", on_click=ajouter_clic)]),
        ft.Divider(),
        ft.Text("COTISATION"),
        ft.Row([drop_membres, input_montant, ft.ElevatedButton("ENCAISSER", on_click=encaisser_clic)]),
        ft.Divider(),
        ft.Row([
            ft.Column([ft.Text("MEMBRES"), liste_membres_ui]),
            ft.Column([ft.Text("CALENDRIER"), liste_tours_ui]),
            ft.Column([ft.Text("HISTORIQUE"), table_historique]),
        ], vertical_alignment="start")
    )
    rafraichir_tout()

ft.app(target=main)