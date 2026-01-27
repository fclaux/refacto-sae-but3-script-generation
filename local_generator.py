import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta  # ← ajoute timedelta ici aussi

from Front.schedule_generator import generate_schedule

# ==================== CONFIGURATION ====================
DB_CONFIG = {
    'host': '127.0.0.1', 'database': 'provisional_calendar',
    'user': 'root', 'password': 'secret', 'port': 3306
}
engine = create_engine(
            f"mysql+mysqlconnector://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
            f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        )

# Jours de la semaine pour affichage lisible
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# Types de cours (à adapter selon ta table type_id → tu peux me donner la table types si besoin)
TYPES_COURS = {1: "CM", 2: "TD", 3: "TP", 4: "Examen", 5: "Autre"}

class EDTViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Visualiseur d'Emploi du Temps - Tous les cours planifiés")
        self.root.geometry("1600x900")

        # Titre
        tk.Label(root, text="Emploi du Temps Complet - Tous les cours", font=("Helvetica", 18, "bold")).pack(pady=10)

        # Boutons
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)

        tk.Button(btn_frame, text="Actualiser", command=self.charger_donnees, bg="#4CAF50", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Exporter en CSV", command=self.exporter_csv, bg="#FF9800", fg="white", width=20).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Générer EDT Image", command=self.generer_edt_image,
                  bg="#9C27B0", fg="white", width=20, font=("Helvetica", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Générer TOUS les EDT (semaine)",
                  command=self.generer_tous_edt, bg="#E91E63", fg="white",
                  font=("Helvetica", 11, "bold"), width=25).pack(side=tk.LEFT, padx=5)
        # Recherche
        search_frame = tk.Frame(root)
        search_frame.pack(pady=5)
        tk.Label(search_frame, text="Rechercher :").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=50)
        search_entry.pack(side=tk.LEFT, padx=5)
        self.search_var.trace("w", self.filtrer)

        # Tableau
        tree_frame = tk.Frame(root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.tree = ttk.Treeview(tree_frame, show="headings")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.charger_donnees()

    def charger_donnees(self):
        query = """
                SELECT es.id                                    AS edt_id, \
                       es.day_of_week, \
                       es.start_hour, \
                       s.duration, \
                       t.title                                  AS cours, \
                       CONCAT(u1.last_name, ' ', u1.first_name) AS professeur, \
                       r.name                                   AS salle, \
                       p.name                                   AS promotion, \
                       g.name                                   AS groupe, \
                       sg.name                                  AS sous_groupe, \
                       TYPES.acronym                               AS type_cours, \
                       w.week_number                            AS semaine
                FROM edt_slot es
                         JOIN slots s ON es.slot_id = s.id
                         JOIN teachings t ON s.teaching_id = t.id
                         LEFT JOIN rooms r ON es.room_id = r.id
                         LEFT JOIN slots_teachers st ON s.id = st.slot_id
                         LEFT JOIN teachers te ON st.teacher_id = te.id
                         LEFT JOIN users u1 ON te.user_id = u1.id
                         LEFT JOIN promotions p ON s.promotion_id = p.id
                         LEFT JOIN groups g ON s.group_id = g.id
                         LEFT JOIN groups sg ON s.subgroup_id = sg.id
                         LEFT JOIN slot_types TYPES ON s.type_id = TYPES.id
                         LEFT JOIN weeks w ON s.week_id = w.id
                ORDER BY es.id, es.start_hour \
                """

        try:
            df = pd.read_sql(query, engine)

            # === Gestion des professeurs multiples ===
            df_prof = df.groupby('edt_id').agg({
                'professeur': lambda x: ', '.join(
                    sorted([p.strip() for p in x if pd.notna(p) and p.strip()])) or 'Non assigné'
            }).reset_index()

            df = df.drop_duplicates('edt_id').drop(columns=['professeur'], errors='ignore')
            df = df.merge(df_prof, on='edt_id', how='left')

            # === Calcul propre de l'heure de fin en Python ===
            def calculer_horaire(row):
                try:
                    heure_debut = datetime.strptime(row['start_hour'], '%H:%M:%S')
                    duree_heures = float(row['duration'])
                    heure_fin = (heure_debut + timedelta(hours=duree_heures))
                    return f"{heure_debut.strftime('%H:%M')} → {heure_fin.strftime('%H:%M')}"
                except:
                    return f"{row['start_hour'][:5]} → ?"

            df['horaire'] = df.apply(calculer_horaire, axis=1)

            # Jour lisible
            df['jour'] = df['day_of_week']
            # Colonnes finales dans l'ordre souhaité
            df = df[
                ['jour', 'horaire', 'cours', 'professeur', 'salle', 'promotion', 'groupe', 'sous_groupe', 'type_cours',
                 'semaine','duration']]

            self.data_complet = df
            self.afficher_dans_tableau(df)

        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger l'emploi du temps :\n{e}")
            print(e)  # pour debug dans la console

    def afficher_dans_tableau(self, df):
        for i in self.tree.get_children():
            self.tree.delete(i)

        self.tree["columns"] = list(df.columns)
        for col in df.columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            width = 200 if col in ["cours", "professeur"] else 120
            self.tree.column(col, width=width, anchor="center")
        self.tree.column("cours", width=350, anchor="w")
        self.tree.column("professeur", width=250, anchor="w")

        for _, row in df.iterrows():
            self.tree.insert("", "end", values=list(row))

    def filtrer(self, *args):
        terme = self.search_var.get().lower()
        if not terme:
            self.afficher_dans_tableau(self.data_complet)
        else:
            filtre = self.data_complet.apply(lambda row: row.astype(str).str.lower().str.contains(terme).any(), axis=1)
            self.afficher_dans_tableau(self.data_complet[filtre])

    def exporter_csv(self):
        fichier = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if fichier:
            self.data_complet.to_csv(fichier, index=False, encoding='utf-8-sig')
            messagebox.showinfo("Export", f"Exporté avec succès dans\n{fichier}")

    def generer_edt_image(self):
        if not hasattr(self, 'data_complet') or self.data_complet.empty:
            messagebox.showwarning("Aucune donnée", "Charge d'abord les données !")
            return

        # Popup pour choisir promotion et semaine
        popup = tk.Toplevel(self.root)
        popup.title("Générer l'emploi du temps")
        popup.geometry("400x300")
        popup.transient(self.root)
        popup.grab_set()

        tk.Label(popup, text="Promotion :", font=("Helvetica", 12)).pack(pady=10)
        promos = sorted(self.data_complet['promotion'].dropna().unique())
        promo_var = tk.StringVar(value=promos[0] if promos else "")
        ttk.Combobox(popup, textvariable=promo_var, values=promos, state="readonly", width=30).pack(pady=5)

        tk.Label(popup, text="Semaine :", font=("Helvetica", 12)).pack(pady=10)
        semaines = sorted(self.data_complet['semaine'].dropna().unique(),
                          key=lambda x: int(x) if str(x).isdigit() else 999)
        semaine_var = tk.StringVar(value=str(semaines[0]) if semaines else "1")
        ttk.Combobox(popup, values=[str(s) for s in semaines], textvariable=semaine_var, width=10).pack(pady=5)

        tk.Label(popup, text="Groupes (ex: G4,G4A,G5) - optionnel :", font=("Helvetica", 10)).pack(pady=10)
        groupes_var = tk.StringVar()
        tk.Entry(popup, textvariable=groupes_var, width=40).pack(pady=5)

        def lancer_generation():
            promotion = promo_var.get()
            try:
                semaine = int(semaine_var.get())
            except:
                messagebox.showerror("Erreur", "Semaine invalide")
                return

            groupes_str = groupes_var.get().strip()
            groupes = [g.strip() for g in groupes_str.split(",")] if groupes_str else None

            # Conversion du DataFrame → liste de cours
            courses = df_to_courses_list(self.data_complet, promotion, semaine, groupes)

            if not courses:
                messagebox.showinfo("Vide", "Aucun cours trouvé avec ces critères.")
                return

            # Générer l'image
            groupes= ["G1", "G1A", "G1B", "G2", "G2A", "G2B", "G3", "G3A", "G3B",]
            generate_schedule(
                promotion=promotion,
                week=semaine,
                groups=groupes or [],
                courses=courses,
                custom_file_name=f"{promotion}_S{semaine:02d}_{' '.join(groupes) if groupes else 'Tous'}"
            )
            messagebox.showinfo("Succès", f"Emploi du temps généré !\nSemaine {semaine} - {promotion}")
            popup.destroy()

        tk.Button(popup, text="Générer l'image", command=lancer_generation, bg="#4CAF50", fg="white",
                  font=("Helvetica", 12, "bold")).pack(pady=20)

    def generer_tous_edt(self):
        if not hasattr(self, 'data_complet') or self.data_complet.empty:
            messagebox.showwarning("Données manquantes", "Charge d'abord les cours !")
            return

        # Demander la semaine
        semaine_str = tk.simpledialog.askstring("Semaine", "Numéro de semaine à générer :")
        if not semaine_str or not semaine_str.isdigit():
            messagebox.showerror("Erreur", "Semaine invalide")
            return
        semaine = int(semaine_str)

        # Filtrer les données de cette semaine
        df_semaine = self.data_complet[self.data_complet['semaine'].astype(str) == str(semaine)]
        if df_semaine.empty:
            messagebox.showinfo("Vide", f"Aucun cours en semaine {semaine}")
            return

        promotions = df_semaine['promotion'].dropna().unique()

        for promo in promotions:
            config = build_config_from_db(self.data_complet, semaine, promotion_filter=promo)
            if not config:
                continue

            cfg = config[promo]
            print(f"Génération EDT → {promo} - Semaine {semaine} - {len(cfg['cours'])} cours")

            generate_schedule(
                promotion=promo,
                week=semaine,
                groups=cfg["groupes"],
                courses=cfg["cours"],
                custom_file_name=f"{promo}_S{semaine:02d}"
            )

        messagebox.showinfo("Terminé !", f"Tous les EDT de la semaine {semaine} ont été générés dans le dossier Edt/")


from typing import Optional, Any
import os
import gc
import matplotlib.pyplot as plt


# ← Suppose que tu as déjà ces deux fonctions dans un fichier utils_edt.py ou similaire
# from utils_edt import create_template, add_courses

def df_to_courses_list(
        df: pd.DataFrame,
        promotion_filter: Optional[str] = None,
        week_filter: Optional[int] = None,
        group_filter: Optional[list[str]] = None
) -> list[tuple]:
    """
    Convertit le DataFrame propre (comme self.data_complet) en liste de cours
    au format attendu par generate_schedule :

    (jour: str, heure_debut: str, durée_en_demiheures: int, cours: str, prof: str, salle: str, type: str, groupe_spec: list|None)
    """
    courses = []

    # Filtrer si besoin
    filtered = df.copy()
    if promotion_filter:
        filtered = filtered[filtered['promotion'] == promotion_filter]
    if week_filter is not None:
        filtered = filtered[filtered['semaine'].astype(str) == str(week_filter)]
    if group_filter:
        # On garde les cours qui concernent au moins un des groupes demandés
        def matches_group(row):
            if pd.isna(row['groupe']) and pd.isna(row['sous_groupe']):
                return True  # cours commun
            if row['groupe'] in group_filter:
                return True
            if pd.notna(row['sous_groupe']) and row['sous_groupe'] in group_filter:
                return True
            return False

        filtered = filtered[filtered.apply(matches_group, axis=1)]

    for _, row in filtered.iterrows():
        jour = row['jour']
        horaire = row['horaire']  # format "08:00 → 10:00"
        heure_debut = horaire.split(" → ")[0]

        # Calcul de la durée en demi-heures (30 min = 1 unité)
        try:
            h_debut = heure_debut.split(":")
            h_start = int(h_debut[0]) * 60 + int(h_debut[1])
            h_fin_str = horaire.split(" → ")[1]
            h_fin = int(h_fin_str.split(":")[0]) * 60 + int(h_fin_str.split(":")[1])
            duree_minutes = h_fin - h_start
            duree_demiheures = int(duree_minutes // 30)
        except:
            duree_demiheures = 2  # fallback

        cours = row['cours'] or "Cours sans nom"
        prof = row['professeur'] or ""
        salle = row['salle'] or ""
        type_cours = row['type_cours'] or "Inconnu"

        # Gestion du groupe/sous-groupe pour le paramètre groups_structure
        groupe_spec = None
        if pd.notna(row['groupe']) or pd.notna(row['sous_groupe']):
            # On suppose que les groupes sont nommés comme dans ta config (ex: G4, G4A, etc.)
            if pd.notna(row['sous_groupe']):
                # Ex: on veut que [0, 'A'] signifie "G4A" si le groupe principal est G4
                groupe_spec = [0, row['sous_groupe'][-1]]  # dernier caractère = A/B/C
            elif pd.notna(row['groupe']):
                groupe_spec = [row['groupe']]  # groupe entier

        courses.append((
            jour,
            heure_debut,
            duree_demiheures,
            cours,
            prof,
            salle,
            type_cours,
            groupe_spec
        ))
    return courses

def build_config_from_db(
    df: pd.DataFrame,
    week_number: int,
    promotion_filter: Optional[str] = None
) -> dict[str, dict]:
    """
    Retourne un dictionnaire au format EXACTEMENT comme ton config_3_sous_groupes
    Prêt à être utilisé directement avec :
        for promo, cfg in config.items():
            generate_schedule(promo, week_number, cfg["groupes"], cfg["cours"])
    """
    if df.empty:
        return {}

    # Filtrer la promotion et la semaine
    filtered = df.copy()
    if promotion_filter:
        filtered = filtered[filtered['promotion'] == promotion_filter]
    filtered = filtered[filtered['semaine'].astype(str) == str(week_number)]

    if filtered.empty:
        print(f"Aucun cours trouvé pour la semaine {week_number} et promotion {promotion_filter or 'toutes'}")
        return {}

    # === 1. Déterminer la promotion (on prend la première trouvée si plusieurs) ===
    promotion = filtered['promotion'].iloc[0]

    # === 2. Construire la liste des groupes/sous-groupes présents ===
    groupes_set = set()
    sous_groupes_set = set()

    for _, row in filtered.iterrows():
        if pd.notna(row['groupe']):
            groupes_set.add(str(row['groupe']))
        if pd.notna(row['sous_groupe']):
            sous_groupes_set.add(str(row['sous_groupe']))

    # On garde l'ordre logique : groupe principal + ses sous-groupes
    groupes_list = sorted(groupes_set)
    all_groups = groupes_list + sorted(sous_groupes_set - groupes_set)  # évite doublons

    # === 3. Construire la liste des cours au format exact ===
    cours_list = []

    for _, row in filtered.iterrows():
        jour = row['jour']
        heure_debut = row['horaire'].split(" → ")[0]
        duree_heures = row.get('duration', 1.0)  # si tu as encore la colonne duration
        if 'duration' not in row or pd.isna(row['duration']):
            # Recalcul depuis horaire si besoin
            try:
                duree_heures = row['duration']*0.5
            except:
                duree_heures = 2.0
        duree_demiheures = int(round(duree_heures * 2))  # 1h = 2, 1.5h = 3, etc.

        cours = str(row['cours']) if pd.notna(row['cours']) else "Cours sans titre"
        prof = str(row['professeur']) if pd.notna(row['professeur']) else ""
        salle = str(row['salle']) if pd.notna(row['salle']) else ""
        type_cours = str(row['type_cours']) if pd.notna(row['type_cours']) else "Inconnu"

        # === Gestion du groupe_spec (le 8e élément) ===
        groupe_spec = None

        if promotion == "BUT1":
            all_groups = ['G1', 'G1A', 'G1B', 'G2', 'G2A', 'G2B', 'G3', 'G3A', 'G3B']
        elif promotion == "BUT2":
            all_groups = ['G4', 'G4A', 'G4B', 'G5', 'G5A', 'G5B']
        elif promotion == "BUT3":
            all_groups = ['G7', 'G7A', 'G7B','G8', 'G8A']

        if pd.notna(row['sous_groupe']):
            # Ex: G4A → on veut [0, 'A'] si G4 est le groupe principal à l'index 0
            print(groupes_list, " ", all_groups)
            sg = str(row['sous_groupe'])
            if sg in all_groups:
                idx = all_groups.index(next((g for g in groupes_list if sg.startswith(g)), None))
                if idx != -1:
                    lettre = sg[len(all_groups[idx]):]  # ex: "A"
                    groupe_spec = [idx, lettre] if lettre else [idx]
        elif pd.notna(row['groupe']):
            g = str(row['groupe'])
            if g in all_groups:
                idx = all_groups.index(g)
                groupe_spec = [idx]  # groupe entier

        # Si c’est un cours commun à tout le monde → None
        if pd.isna(row['groupe']) and pd.isna(row['sous_groupe']):
            groupe_spec = None

        cours_list.append((
            jour,
            heure_debut,
            duree_demiheures,
            cours,
            prof,
            salle,
            type_cours,
            groupe_spec
        ))

    # === Config finale ===


    config = {
        promotion: {
            "groupes": all_groups,
            "cours": cours_list
        }
    }
    print(config)
    return config

# ==================== LANCEMENT ====================
if __name__ == "__main__":
    root = tk.Tk()
    app = EDTViewerApp(root)
    root.mainloop()