from typing import Dict, Any, Tuple

import pandas as pd
from sqlalchemy import create_engine


# ==============================================================================
# CLASSE 1: GESTION DES DONNÉES (DataProvider)
# ==============================================================================
class DataProvider:
    """
    Responsable de la connexion à la BDD et de la préparation de toutes les
    données nécessaires pour le modèle d'optimisation.
    """

    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self.engine = create_engine(
            f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@"
            f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )

    def load_and_prepare_data(self) -> Dict[str, Any]:
        """
        Charge toutes les données depuis la BDD avec Pandas et les prépare
        dans un format utilisable par le modèle.
        """
        list_amphi_c=[{0: [(11, 23)]},{1: [(0, 7)]},{2: [(0, 7)]},{3: []},{4: [(11, 23)]}] #
        #Il faudrait que l'application puisse gérer le fait d'importer une liste des jours d'amphi, pour le
        #moment on met les infos en dur afin de faire les tests
        print("1. Chargement des données depuis la base de données...")
        week_id=1
        jours = 5
        creneaux_par_jour = 20
        slots = [(d, s) for d in range(jours) for s in range(creneaux_par_jour)]
        fenetre_midi = list(range(8, 11))

        df_salles = pd.read_sql("SELECT name, seat_capacity FROM rooms WHERE id NOT IN (17, 18)", self.engine)
        #df_profs = pd.read_sql(
        #    "SELECT CONCAT(u.first_name, ' ', u.last_name) AS prof_name FROM teachers t JOIN users u ON t.user_id = u.id",
        #    self.engine)
        df_profs_with_id = pd.read_sql(
            """SELECT t.id                                   AS teacher_id,
                      CONCAT(u.first_name, ' ', u.last_name) AS prof_name
               FROM teachers t
                        JOIN users u ON t.user_id = u.id""",
            self.engine
        )
        prof_to_teacher_id = dict(zip(df_profs_with_id['prof_name'], df_profs_with_id['teacher_id']))
        profs = df_profs_with_id['prof_name'].tolist()  # Cette liste est maintenant cohérente
        query_slots = """
                      SELECT s.id, \
                             s.duration, \
                             t.title              AS teaching_title, \
                             p.name               AS promotion_name, \
                             g.name               AS group_name, \
                             sg.name              AS subgroup_name,
                             promo.student_amount AS promo_size, \
                             gr.student_amount    AS group_size, \
                             sub.student_amount   AS subgroup_size, \
                             s.type_id, \
                             s.promotion_id
                      FROM slots s
                               LEFT JOIN teachings t ON s.teaching_id = t.id
                               LEFT JOIN promotions p ON s.promotion_id = p.id
                               LEFT JOIN `groups` g ON s.group_id = g.id
                               LEFT JOIN subgroups sg ON s.subgroup_id = sg.id
                               LEFT JOIN promotions promo ON s.promotion_id = promo.id
                               LEFT JOIN `groups` gr ON s.group_id = gr.id
                               LEFT JOIN subgroups sub ON s.subgroup_id = sub.id  
                      WHERE week_id= %s
                      """
        df_planning = pd.read_sql(query_slots, self.engine, params=(week_id,), index_col='id')
        query_prof_slot = """
            SELECT s.id AS slot_id, CONCAT(u.first_name, ' ', u.last_name) AS prof_name
            FROM slots_teachers st
            JOIN slots s ON st.slot_id = s.id
            JOIN teachers t ON st.teacher_id = t.id
            JOIN users u ON t.user_id = u.id
        """
        # AJOUTE CECI (corrigé et fonctionnel)
        query_dispos = """
                       SELECT teacher_id, day_of_week, start_time, end_time,priority,week_id
                       FROM teacher_constraints
                       WHERE (week_id = %s OR week_id IS NULL)
                           AND active = 1
                       """
        df_dispos = pd.read_sql(query_dispos, self.engine, params=(week_id,))


        # Structure finale : prof_teacher_id → {jour: [(slot_debut, slot_fin), ...]}
        disponibilites_profs = {}  # teacher_id → {day_id: [(slot_start, slot_end)]}
        for _, row in df_dispos.iterrows():
            teacher_id = row['teacher_id']
            day_id = int(row['day_id'])  # 0 = lundi, 4 = vendredi
            debut_str = str(row['date_from'])[-8:]
            fin_str = str(row['date_to'])[-8:]

            debut_slot = self._time_to_slot(debut_str)
            fin_slot = self._time_to_slot(fin_str)

            disponibilites_profs.setdefault(teacher_id, {}).setdefault(day_id, []).append((debut_slot, fin_slot))

        # DEBUG
        print("\n=== DEBUG DISPONIBILITÉS ===")
        print("disponibilites_profs =", disponibilites_profs)
        print("prof_to_teacher_id =", prof_to_teacher_id)
        print("profs =", profs)
        print("===============================\n")
        df_prof_slot = pd.read_sql(query_prof_slot, self.engine)
        profs_par_slot = df_prof_slot.groupby('slot_id')['prof_name'].apply(list).to_dict()
        #profs = df_profs['prof_name'].tolist()

        #cours, duree_cours, taille_groupes, map_groupe_cours = self._build_course_structures(df_planning,profs_par_slot, profs)
        cours, duree_cours, taille_groupes, map_groupe_cours = self._build_course_structures(
            df_planning, profs_par_slot, profs
        )
        salles = df_salles.set_index('name')['seat_capacity'].to_dict()

        print(f"   -> {len(cours)} cours à planifier.")
        print(f"   -> {len(salles)} salles et {len(profs)} professeurs disponibles.")

        # Dans le return
        print("groups_cours_map",map_groupe_cours)
        return {
            "jours": jours, "creneaux_par_jour": creneaux_par_jour, "slots": slots, "nb_slots": len(slots),
            "fenetre_midi": fenetre_midi,
            "cours": cours, "duree_cours": duree_cours, "taille_groupes": taille_groupes,
            "map_groupe_cours": map_groupe_cours,
            "salles": salles, "capacites": list(salles.values()), "profs": profs,
            "profs_par_slot": profs_par_slot,
            "all_groups": list(map_groupe_cours.keys()),
            "disponibilites_profs": disponibilites_profs,
            "prof_to_teacher_id": prof_to_teacher_id,
            "liste_amphi_c": list_amphi_c,
        }

    def _time_to_slot(self, time_str: str) -> int:
        """'13:30:00' → 11 (8h=0, 8h30=1, ..., 13h30=11)"""
        print("time",time_str)
        if pd.isna(time_str):
            return 0
        h, m, _ = map(int, str(time_str).split(':'))
        print("h :",h," m :",m)
        print("slot ",(h - 8) * 2 + (m // 30))
        return (h - 8) * 2 + (m // 30)

    def _build_course_structures(self, df: pd.DataFrame,profs_par_slot: dict, profs: list) -> Tuple:

        cours, duree_cours, taille_groupes, map_groupe_cours = [], {}, {}, {}

        for idx, row in df.iterrows():
            duration_slots = int(row['duration'] * 2)

            if row['type_id'] == 1:  # CM → concerne TOUTE la promotion
                group_name = row['promotion_name']  # "BUT1", "BUT2", etc.
                cid = f"CM_{row['teaching_title']}_{group_name}_s{idx}"
                group_size = row['promo_size']

                # Le CM concerne TOUS les sous-groupes de cette promotion
                affected_groups = [group_name]  # BUT1 lui-même
                group_map = {"BUT1": ["G1", "G2", "G3","G1A", "G2A", "G3A","G1B", "G2B", "G3B"],"BUT2": ["G4", "G5","G4A", "G5A","G4B", "G5B"],"BUT3": ["G7", "G8","G7A", "G7B", "G8A"]}  # à adapter si plus de groupes
                if group_name in group_map:
                    affected_groups.extend(group_map[group_name])

            elif row['type_id'] == 2:  # TD → un seul groupe
                group_name = row['group_name']
                cid = f"TD_{row['teaching_title']}_{group_name}_s{idx}"
                group_size = row['group_size']
                affected_groups = [group_name]

            elif row['type_id'] == 3:  # TP → un seul sous-groupe
                group_name = f"{row['group_name']}{row['subgroup_name']}"
                cid = f"TP_{row['teaching_title']}_{group_name}_s{idx}"
                group_size = row['subgroup_size']
                affected_groups = [group_name]
            elif row['type_id'] == 4:  # SAE → un seul groupe
                group_name = row['group_name']
                cid = f"SAE_{row['teaching_title']}_{group_name}_s{idx}"
                group_size = row['group_size']
                affected_groups = [group_name]
            #TODO gestion Exam
            #TODO gestion Autre -> conférence / Rentrée Autre si nécessaire

            else:
                continue

            # On crée le cours
            profs_autorises = profs_par_slot.get(idx, [])
            indices_profs = [i for i, name in enumerate(profs) if name in profs_autorises]
            if not indices_profs:
                print(f"Warning: Aucun prof autorisé pour {cid}")
                indices_profs = list(range(len(profs)))

            cours.append({
                "id": cid,
                "groups": affected_groups,
                "allowed_prof_indices": indices_profs
            })
            print("cours : ",cours)
            #cours.append({"id": cid, "groups": affected_groups})  # ← plusieurs groupes possibles
            duree_cours[cid] = duration_slots
            taille_groupes[group_name] = int(group_size) if pd.notna(group_size) else 0
            # On l'ajoute dans TOUS les groupes qu'il concerne
            for g in affected_groups:
                if g not in map_groupe_cours:
                    map_groupe_cours[g] = []
                map_groupe_cours[g].append(cid)
        print("lg cours",len(cours))
        print("taille grp :",taille_groupes)
        return cours, duree_cours, taille_groupes, map_groupe_cours