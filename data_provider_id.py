from typing import Dict, Any, Tuple

import pandas as pd
from sqlalchemy import create_engine

from function import get_availabilityProf_From_Unavailable, get_availabilityRoom_From_Unavailable, \
    get_availabilityGroup_From_Unavailable, convert_days_int_to_string, get_availabilitySlot_From_Unavailable


# ==============================================================================
# CLASSE 1: GESTION DES DONNÉES (DataProvider)
# ==============================================================================
class DataProviderID:
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

    def load_and_prepare_data(self,week_id:int) -> Dict[str, Any]:
        """
        Charge toutes les données depuis la BDD avec Pandas et les prépare
        dans un format utilisable par le modèle.
        """
        list_amphi_c=[{0: [(11, 23)]},{1: [(0, 7)]},{2: [(0, 7)]},{3: []},{4: [(11, 23)]}] #
        #Il faudrait que l'application puisse gérer le fait d'importer une liste des jours d'amphi, pour le
        #moment on met les infos en dur afin de faire les tests
        print("1. Chargement des données depuis la base de données...")
        jours = 5
        creneaux_par_jour = 23
        slots = [(d, s) for d in range(jours) for s in range(creneaux_par_jour)]
        fenetre_midi = list(range(8, 11))

        df_salles = pd.read_sql("SELECT id as name, seat_capacity FROM rooms WHERE id NOT IN (17, 18)", self.engine)
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
                       SELECT tc.teacher_id, tc.day_of_week, tc.start_time, tc.end_time, tc.priority, tc.week_id
                       FROM teacher_constraints tc
                       WHERE tc.active = 1
                         AND (tc.week_id = %(week_id)s OR tc.week_id IS NULL)
                         AND (
                           tc.week_id = %(week_id)s
                               OR (tc.week_id IS NULL
                               AND NOT EXISTS (SELECT 1 \
                                               FROM teacher_constraints tc2 \
                                               WHERE tc2.teacher_id = tc.teacher_id \
                                                 AND tc2.day_of_week = tc.day_of_week \
                                                 AND tc2.week_id = %(week_id)s \
                                                 AND tc2.active = 1)
                               )
                           ) \
                       """
        df_dispos = pd.read_sql(query_dispos, self.engine, params={"week_id": week_id})
        disponibilites_profs=get_availabilityProf_From_Unavailable(df_dispos,creneaux_par_jour)
        query_dispos = """
                       SELECT rc.room_id, rc.day_of_week, rc.start_time, rc.end_time, rc.priority, rc.week_id
                       FROM room_constraints rc
                       WHERE rc.active = 1
                         AND (rc.week_id = %(week_id)s OR rc.week_id IS NULL)
                         AND (
                           rc.week_id = %(week_id)s
                               OR (rc.week_id IS NULL
                               AND NOT EXISTS (SELECT 1 \
                                               FROM room_constraints rc2 \
                                               WHERE rc2.room_id = rc.room_id \
                                                 AND rc2.day_of_week = rc.day_of_week \
                                                 AND rc2.week_id = %(week_id)s \
                                                 AND rc2.active = 1)
                               )
                           ) \
                       """
        df_dispos_salles = pd.read_sql(query_dispos, self.engine, params={"week_id": week_id})
        disponibilites_salles=get_availabilityRoom_From_Unavailable(df_dispos_salles,creneaux_par_jour)

        query_dispos = """
                       SELECT gc.group_id, gc.day_of_week, gc.start_time, gc.end_time, gc.priority, gc.week_id
                       FROM group_constraints gc
                       WHERE gc.active = 1
                         AND (gc.week_id = %(week_id)s OR gc.week_id IS NULL)
                         AND (
                           gc.week_id = %(week_id)s
                               OR (gc.week_id IS NULL
                               AND NOT EXISTS (SELECT 1 \
                                               FROM group_constraints gc2 \
                                               WHERE gc2.group_id = gc.group_id \
                                                 AND gc2.day_of_week = gc.day_of_week \
                                                 AND gc2.week_id = %(week_id)s \
                                                 AND gc2.active = 1)
                               )
                           ) \
                       """
        df_dispos_groupes = pd.read_sql(query_dispos, self.engine, params={"week_id": week_id})
        disponibilites_groupes=get_availabilityGroup_From_Unavailable(df_dispos_groupes,20)

        query_dispos = """
                       SELECT sc.slot_id, sc.day_of_week, sc.start_time, sc.end_time, sc.priority, sc.week_id
                       FROM slot_constraints sc
                       WHERE sc.active = 1
                         AND (sc.week_id = %(week_id)s OR sc.week_id IS NULL)
                         AND (
                           sc.week_id = %(week_id)s
                               OR (sc.week_id IS NULL
                               AND NOT EXISTS (SELECT 1 \
                                               FROM slot_constraints sc2 \
                                               WHERE sc2.slot_id = sc.slot_id \
                                                 AND sc2.day_of_week = sc.day_of_week \
                                                 AND sc2.week_id = %(week_id)s \
                                                 AND sc2.active = 1)
                               )
                           ) \
                       """
        df_dispos_slots = pd.read_sql(query_dispos, self.engine, params={"week_id": week_id})
        disponibilites_slots=get_availabilitySlot_From_Unavailable(df_dispos_slots,20)
        # DEBUG
        df_prof_slot = pd.read_sql(query_prof_slot, self.engine)
        profs_par_slot = df_prof_slot.groupby('slot_id')['prof_name'].apply(list).to_dict()
        print("profs par slot : ",profs_par_slot)
        #profs = df_profs['prof_name'].tolist()

        #cours, duree_cours, taille_groupes, map_groupe_cours = self._build_course_structures(df_planning,profs_par_slot, profs)
        cours, duree_cours, taille_groupes, map_groupe_cours = self._build_course_structures(
            df_planning, profs_par_slot, profs
        )
        salles = df_salles.set_index('name')['seat_capacity'].to_dict()

        print(f"   -> {len(cours)} cours à planifier.")
        print(f"   -> {len(salles)} salles et {len(profs)} professeurs disponibles.")

        # Dans le return
        group_to_dispo_key = {
            # Promotions de niveau BUTx
            'BUT1': 1,
            #'BUT2': 2,
            #'BUT3': 3,

            # Groupes principaux Gx (clés simples)
            'G1': 1, 'G2': 2, 'G3': 3,
            # Si vous avez des groupes G4, G5, G7, G8 avec des contraintes spécifiques :
            'G4': 4, 'G5': 5, 'G7': 7, 'G8': 8,  # ⚠️ À adapter si BUT2 et BUT3 n'ont pas de clé propre

            # Sous-groupes (ils héritent souvent de la clé du groupe principal)
            'G1A': 1, 'G1B': 1,
            'G2A': 2, 'G2B': 2,
            'G3A': 3, 'G3B': 3,
            # ... Ajoutez les autres sous-groupes ici ...
        }
        return {
            "jours": jours, "creneaux_par_jour": creneaux_par_jour, "slots": slots, "nb_slots": len(slots),
            "fenetre_midi": fenetre_midi,
            "cours": cours, "duree_cours": duree_cours, "taille_groupes": taille_groupes,
            "map_groupe_cours": map_groupe_cours,
            "salles": salles, "capacites": list(salles.values()), "profs": profs,
            "profs_par_slot": profs_par_slot,
            "all_groups": list(map_groupe_cours.keys()),
            "disponibilites_profs": disponibilites_profs,
            "disponibilites_salles": disponibilites_salles,
            "disponibilites_groupes": disponibilites_groupes,
            "obligations_slots": disponibilites_slots,
            "prof_to_teacher_id": prof_to_teacher_id,
            "liste_amphi_c": list_amphi_c,
            "group_to_dispo_key": group_to_dispo_key  # 🚨 Utilisation du mapping complet        }
        }

    def get_list_room(self):
        list_room=[]
        query_dispos = """SELECT name FROM rooms """
        df_salles = pd.read_sql(query_dispos, self.engine)
        for i in df_salles['name']:
            list_room.append(i)
        return list_room

    def get_availabilityProf_From_Unavailable(self,df_dispos):
        disponibilites_profs = {}
        for _, row in df_dispos.iterrows():


            for _, row in df_dispos.iterrows():
                teacher_id = row['teacher_id']
                day_id = self.convert_daystring_to_int((row['day_of_week']))  # 0 = lundi, 4 = vendredi

                debut_slot = self.get_start_time(row)
                fin_slot = self.get_end_time(row)

                disponibilites_profs.setdefault(teacher_id, {}).setdefault(day_id, []).append((debut_slot, fin_slot))


    def get_end_time(self,row)->str:
        if pd.isna(row['end_time']):
            return ""
        return row['end_time']
    def get_start_time(self,row)->str:
        if pd.isna(row['start_time']):
            return ""
        return row['start_time']

    def convert_daystring_to_int(self, day:str)->int:
        days=['Lundi','Mardi','Mercredi','Jeudi','Vendredi']
        return days.index(day)

    def _time_to_slot(self, time_str: str) -> int:
        """'13:30:00' → 11 (8h=0, 8h30=1, ..., 13h30=11)"""
        if pd.isna(time_str):
            return 0
        h, m, _ = map(int, str(time_str).split(':'))
        return (h - 8) * 2 + (m // 30)

    def _build_course_structures(self, df: pd.DataFrame,profs_par_slot: dict, profs: list) -> Tuple:

        cours, duree_cours, taille_groupes, map_groupe_cours = [], {}, {}, {}
        group_map = {"BUT1": ["G1", "G2", "G3", "G1A", "G2A", "G3A", "G1B", "G2B", "G3B"],
                     "BUT2": ["G4", "G5", "G4A", "G5A", "G4B", "G5B"],
                     "BUT3": ["G7", "G8", "G7A", "G7B", "G8A"]}  # à adapter si plus de groupes
        cpt_no_profs = 0
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
                if group_name== None:
                    group_name = row['promotion_name']
                    group_map = {"BUT1": ["G1", "G2", "G3", "G1A", "G2A", "G3A", "G1B", "G2B", "G3B"],
                                 "BUT2": ["G4", "G5", "G4A", "G5A", "G4B", "G5B"],
                                 "BUT3": ["G7", "G8", "G7A", "G7B", "G8A"]}  # à adapter si plus de groupes
                affected_groups = [group_name]  # BUT1 lui-même
                group_size = row['group_size']
                if group_name in group_map:
                    affected_groups.extend(group_map[group_name])
                    group_size = row['promo_size']
                cid = f"SAE_{row['teaching_title']}_{group_name}_s{idx}"
            #TODO gestion Exam
            #TODO gestion Autre -> conférence / Rentrée Autre si nécessaire

            else:
                continue

            # On crée le cours
            profs_autorises = profs_par_slot.get(idx, [])
            indices_profs = [i for i, name in enumerate(profs) if name in profs_autorises]
            if not indices_profs:
                print(f"Warning: Aucun prof autorisé pour {cid}")
                profs.append("None_"+str(cpt_no_profs))
                index=profs.index("None_"+str(cpt_no_profs))
                indices_profs = [index]#list(range(len(profs)))
                print("indices profs",indices_profs)
                cpt_no_profs+=1
            cours.append({
                "id": cid,
                "groups": affected_groups,
                "allowed_prof_indices": indices_profs
            })
            duree_cours[cid] = duration_slots
            taille_groupes[group_name] = int(group_size) if pd.notna(group_size) else 0
            # On l'ajoute dans TOUS les groupes qu'il concerne
            for g in affected_groups:
                if g not in map_groupe_cours:
                    map_groupe_cours[g] = []
                map_groupe_cours[g].append(cid)
        return cours, duree_cours, taille_groupes, map_groupe_cours

    def convert_courses_dict_to_list_insert(self,courses_dict_list):
        cours_input = []

        for c in courses_dict_list:
            name = c['name']
            day_name = convert_days_int_to_string(c['day'])
            tuple_cours = (
                c['start_hour'],
                name.split('_')[-1][1:],  # type
                c['room'],
                day_name,
            )
            cours_input.append(tuple_cours)
        df_insert = pd.DataFrame(cours_input, columns=['start_hour', 'slot_id', 'room_id','day_of_week'])
        table="edt_slot"
        self.insert_data_with_pandas(df_insert, table)
        return cours_input

    def insert_data_with_pandas(self, df_to_insert, table_name):
        try:
            # Insertion dans la base de données
            # 'if_exists' peut être 'fail', 'replace' ou 'append'
            # 'index=False' pour ne pas insérer l'index du DataFrame comme colonne
            rows_inserted = df_to_insert.to_sql(
                name=table_name,
                con=self.engine,  # Votre moteur de base de données
                if_exists='append',  # Ajoute les lignes à la table existante
                index=False
            )
            print(f"✅ {rows_inserted} lignes insérées dans la table '{table_name}'.")
        except Exception as e:
            print(f"❌ Erreur lors de l'insertion : {e}")