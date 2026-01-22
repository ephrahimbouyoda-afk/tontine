import sqlite3
from datetime import datetime


def get_db_connection():
    conn = sqlite3.connect("tontine_pro.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS membres (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT UNIQUE NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, membre_id INTEGER, montant REAL NOT NULL, type TEXT NOT NULL, date TEXT NOT NULL)")
    conn.commit()
    conn.close()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calendrier (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            membre_id INTEGER,
            mois TEXT NOT NULL,
            annee TEXT NOT NULL,
            FOREIGN KEY(membre_id) REFERENCES membres(id)
        )
    """)

def ajouter_membre(conn, nom):
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO membres (nom) VALUES (?)", (nom,))
        conn.commit()
        return True
    except:
        return False

def lister_membres(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT nom FROM membres ORDER BY nom")
    return [row['nom'] for row in cursor.fetchall()]

def enregistrer_paiement(conn, membre_nom, montant):
    cursor = conn.cursor()
    # 1. On récupère l'ID du membre via son nom
    cursor.execute("SELECT id FROM membres WHERE nom = ?", (membre_nom,))
    membre = cursor.fetchone()
    if membre:
        # 2. On insère la transaction
        date_auj = datetime.now().strftime("%d/%m/%Y")
        cursor.execute("INSERT INTO transactions (membre_id, montant, type, date) VALUES (?, ?, ?, ?)",
                       (membre['id'], montant, 'ENTREE', date_auj))
        conn.commit()
        return True
    return False

def obtenir_totaux_membres(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT membres.nom, SUM(transactions.montant) as total
        FROM membres
        LEFT JOIN transactions ON membres.id = transactions.membre_id
        GROUP BY membres.nom
        ORDER BY total DESC
    """)
    return cursor.fetchall()

def obtenir_historique(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT membres.nom, transactions.montant, transactions.date
        FROM transactions
        JOIN membres ON transactions.membre_id = membres.id
        ORDER BY transactions.id DESC
        LIMIT 10
    """)
    return cursor.fetchall()

def obtenir_historique_complet(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT membres.nom, transactions.montant, transactions.type, transactions.date
        FROM transactions
        JOIN membres ON transactions.membre_id = membres.id
        ORDER BY transactions.id DESC
    """)
    return cursor.fetchall()

def enregistrer_retrait(conn, membre_nom, montant):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM membres WHERE nom = ?", (membre_nom,))
    membre = cursor.fetchone()
    if membre:
        date_auj = datetime.now().strftime("%d/%m/%Y")
        # On insère une SORTIE
        cursor.execute("INSERT INTO transactions (membre_id, montant, type, date) VALUES (?, ?, ?, ?)",
                       (membre['id'], montant, 'SORTIE', date_auj))
        conn.commit()
        return True
    return False

# Dans database.py
def enregistrer_retrait(conn, membre_nom, montant):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM membres WHERE nom = ?", (membre_nom,))
    membre = cursor.fetchone()
    if membre:
        from datetime import datetime
        date_auj = datetime.now().strftime("%d/%m/%Y")
        # On enregistre une SORTIE pour que rafraichir() fasse une soustraction
        cursor.execute("INSERT INTO transactions (membre_id, montant, type, date) VALUES (?, ?, ?, ?)",
                       (membre['id'], montant, 'SORTIE', date_auj))
        conn.commit()
        return True
    return False

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # On ajoute la table calendrier
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calendrier (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            membre_id INTEGER,
            mois TEXT NOT NULL,
            FOREIGN KEY(membre_id) REFERENCES membres(id)
        )
    """)
    conn.commit()
    conn.close()

def definir_tour(conn, membre_nom, mois):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM membres WHERE nom = ?", (membre_nom,))
    m = cursor.fetchone()
    if m:
        cursor.execute("INSERT INTO calendrier (membre_id, mois) VALUES (?, ?)", (m['id'], mois))
        conn.commit()