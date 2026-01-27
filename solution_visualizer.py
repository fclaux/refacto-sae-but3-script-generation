from typing import Dict, Any

from Front import schedule_generator as sg


# ==============================================================================
# CLASSE 3: AFFICHAGE DES RÉSULTATS (SolutionVisualizer)
# ==============================================================================
class SolutionVisualizer:
    def __init__(self, solution: Dict[str, Any], data: Dict[str, Any]):
        self.temp = []
        self.solver = solution['solver']
        self._vars = solution['vars']
        self.data = data
        self.planning = self._build_planning_from_solution()

    def display(self,DataProviderInsert,week_id):
        print("\n4. Affichage de la solution trouvée :")
        self._print_schedule_to_console()
        #self._check_violations()  # Affiche les violations

        self._generate_graphical_schedule(DataProviderInsert,week_id)

    def _build_planning_from_solution(self):
        planning, self.actual_starts = {s: [] for s in range(self.data['nb_slots'])}, {}
        for c in self.data['cours']:
            cid = c['id']
            s_idx = next((s for s, v in self._vars['start'].items() if
                          v is not None and v.Name().startswith(f"start_{cid}") and self.solver.Value(v)), (None, None))[1]
            r_idx = next((r for r, v in self._vars['y_salle'].items() if
                          v.Name().startswith(f"y_salle_{cid}") and self.solver.Value(v)), (None, None))[1]
            p_idx = next((p for p, v in self._vars['z_prof'].items() if
                          v.Name().startswith(f"z_prof_{cid}") and self.solver.Value(v)), (None, None))[1]
            if s_idx is not None and r_idx is not None and p_idx is not None:
                self.actual_starts[cid] = s_idx
                salle_str, prof_str = list(self.data['salles'].keys())[r_idx], self.data['profs'][p_idx]
                for offset in range(self.data['duree_cours'][cid]):
                    planning[s_idx + offset].append((cid, salle_str, prof_str))
        return planning

    def _check_violations(self):
        print("\n--- Vérification des violations ---")
        violations = [v.Name() for v in self._vars.get('penalites_capacite', []) if self.solver.Value(v) == 1]
        if violations:
            print(f"🔴 {len(violations)} VIOLATION(S) DE CAPACITÉ DÉTECTÉE(S) :")
            for v_name in violations: print(f"   - {v_name}")
        else:
            print("🟢 Aucune violation de contrainte souple détectée. La solution est valide !")
        print("---------------------------------")

    def _print_schedule_to_console(self):
        def slot_to_time(t: int):
            h, m = 8 + (t // 2), 30 * (t % 2)
            h_end, m_end = 8 + ((t + 1) // 2), 30 * ((t + 1) % 2)
            return f"{h:02d}:{m:02d}-{h_end:02d}:{m_end:02d}"
        self.temp = []  # Liste qui contiendra tous les cours avec infos et durée

        for d_idx in range(self.data['jours']):
            print(f"\n=== Day {d_idx + 1} ===")

            cours_en_cours = {}

            for t_in_day in range(self.data['creneaux_par_jour']):
                global_t = d_idx * self.data['creneaux_par_jour'] + t_in_day

                entries = self.planning.get(global_t, [])
                time_str = slot_to_time(t_in_day)

                if entries:
                    for (cid, room_str, teacher_str) in entries:
                        if self.actual_starts.get(cid) == global_t:
                            print(f"  {time_str} : {cid} (Room: {room_str}, Teacher: {teacher_str}) Début")

                            dict_infos_schedule_gen = {
                                "day": d_idx,
                                "start_hour": time_str.split('-')[0],
                                "duration": 1,
                                "name": cid,
                                "teacher": teacher_str,
                                "room": room_str,
                                "course_type": None,
                                "course_group": None
                            }
                            cours_en_cours[cid] = dict_infos_schedule_gen

                        else:
                            print(f"  {time_str} : {cid} (Room: {room_str}, Teacher: {teacher_str})")
                            cours_en_cours[cid]["duration"] += 1
                    for cours_dict in cours_en_cours.values():
                        if cours_dict not in self.temp:
                            self.temp.append(cours_dict)
                else:
                    if not self.data['fenetre_midi'] or t_in_day not in self.data['fenetre_midi']:
                        print(f"  {time_str} : --")
            print("-" * 20)
            #pass

    def _generate_graphical_schedule(self,DataProviderInsert,week_id):
        print("\n5. Generating graphical schedules...")
        # Example for generating schedules (adapt to your needs)
        # You must adjust the parameters of recup.recup_edt
        try:
            t: Dict[str, Dict[str, list]] = {"A1": {"groupes": ["G1", "G2", "G3","G1A", "G2A", "G3A","G1B", "G2B", "G3B"]}}
            list_room=DataProviderInsert.get_list_room()
            DataProviderInsert.convert_courses_dict_to_list_insert(self.temp)
            courses_list_B1,courses_list_B2,courses_list_B3 = convert_courses_dict_to_list_room_name(self.temp,list_room)
            sg.generate_schedule("A1", week_id, t["A1"]["groupes"],courses_list_B1 )
            t = {"A2": {"groupes": ["G4", "G5","G4A", "G5A","G4B", "G5B"]}}
            sg.generate_schedule("A2", week_id, t["A2"]["groupes"], courses_list_B2)

            t = {"A3": {"groupes": ["G7", "G8","G7A","G7B","G8A"]}}
            sg.generate_schedule("A3", week_id, t["A3"]["groupes"], courses_list_B3)


            sg.plt.show()  # Display all plots
            print("   -> Graphics generated successfully.")
        except Exception as e:
            print(f"   -> ERROR during graphical generation: {e}")

# Remplace toute la fonction par ça :
GROUPE_TO_LIST = {
    # BUT1
    "BUT1": "B1", "G1": "B1", "G2": "B1", "G3": "B1",
    "G1A": "B1", "G1B": "B1", "G2A": "B1", "G2B": "B1", "G3A": "B1", "G3B": "B1",
    # BUT2
    "BUT2": "B2", "G4": "B2", "G5": "B2", "G6": "B2",
    "G4A": "B2", "G4B": "B2", "G5A": "B2", "G5B": "B2", "G6A": "B2", "G6B": "B2",
    # BUT3 → tout le reste
}

def convert_courses_dict_to_list_room_name(courses_dict_list,list_room):
    jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    B1, B2, B3 = [], [], []

    for c in courses_dict_list:
        name = c['name']
        day_name = jours[c['day']]
        groupe = name.split('_')[-2] if '_' in name else "UNKNOWN"
        target = GROUPE_TO_LIST.get(groupe, "B3")  # défaut = BUT3

        tuple_cours = (
            day_name,
            c['start_hour'],
            c['duration'],
            name.split('_')[1],
            c['teacher'],
            list_room[c['room']-1],
            name.split('_')[0],  # type
            groupe_to_indices(groupe)
        )
        if target == "B1":
            B1.append(tuple_cours)
        elif target == "B2":
            B2.append(tuple_cours)
        else:
            B3.append(tuple_cours)
    return B1, B2, B3

def groupe_to_indices(groupe: str):
    # Si le groupe commence par BUT → renvoie juste [0]
    if groupe.startswith("BUT"):
        return None
    # Exemple : G1, G2, G3, G1A, G2B, G3A...
    # Le premier chiffre : index = int - 1
    base = (int(groupe[1]) - 1)%3   # ex : G1 → 1-1 = 0

    # S'il y a une lettre supplémentaire (A, B, C…)
    if len(groupe) > 2:
        suffix = groupe[2:]   # "A", "B", "C"...
        return [base, suffix]

    return [base]