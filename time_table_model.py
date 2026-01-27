# ==============================================================================
# CLASSE 2: LE MODÈLE D'OPTIMISATION (TimetableModel)
# ==============================================================================
from typing import Dict, Any

from ortools.sat.python import cp_model

from function import recup_cours, recup_id_slot_from_str_to_int


class TimetableModel:
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.model = cp_model.CpModel()
        self._vars = {}
        self.temp = []
        self._ordres_a_forcer=[]

    def build_model(self):
        print("2. Construction du modèle d'optimisation...")
        self._create_decision_variables()
        self._add_linking_constraints()
        self._add_structural_constraints()
        self.appliquer_ordre_cm_td_tp()  # ← ICI on les APPLIQUE (variables existent !)
        self._define_objective_function()  # Déplacé avant la résolution
        print("   -> Modèle construit.")

    def solve(self, max_time_seconds: int = 600) -> Dict[str, Any]:
        print("\n3. Lancement de la résolution...")
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max_time_seconds
        solver.parameters.num_search_workers = 8
        status = solver.Solve(self.model)
        print(f"   -> Résolution terminée avec le statut : {solver.StatusName(status)}")
        return {"status": status, "solver": solver,
                "vars": self._vars if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None}

    def _create_decision_variables(self):
        d = self.data
        self._vars.update({'start': {}, 'occupe': {}, 'y_salle': {}, 'z_prof': {}})
        for c in d['cours']:
            cid, duration = c['id'], d['duree_cours'][c['id']]#[cid]
            for s, (day, offset) in enumerate(d['slots']):
                chevauche_midi = any(offset + i in d['fenetre_midi'] for i in range(duration))
                if offset + duration <= d['creneaux_par_jour'] and not chevauche_midi:
                    self._vars['start'][cid, s] = self.model.NewBoolVar(f"start_{cid}_{s}")
                else:
                    self._vars['start'][cid, s] = None
            for t in range(d['nb_slots']): self._vars['occupe'][cid, t] = self.model.NewBoolVar(f"occupe_{cid}_{t}")
            for r in range(len(d['salles'])): self._vars['y_salle'][cid, r] = self.model.NewBoolVar(f"y_salle_{cid}_{r}")
            for p in range(len(d['profs'])): self._vars['z_prof'][cid, p] = self.model.NewBoolVar(f"z_prof_{cid}_{p}")

    def _add_linking_constraints(self):
        d = self.data
        for c in d['cours']:
            cid = c['id']
            valid_starts = [v for v in self._vars['start'].values() if v is not None and v.Name().startswith(f"start_{cid}")]
            self.model.Add(sum(valid_starts) == 1)
            self.model.Add(sum(self._vars['y_salle'][cid, r] for r in range(len(d['salles']))) == 1)
            #self.model.Add(sum(self._vars['z_prof'][cid, p] for p in range(len(d['profs']))) == 1)
            allowed = c.get("allowed_prof_indices", list(range(len(d['profs']))))
            if allowed:
                self.model.Add(sum(self._vars['z_prof'][cid, p] for p in allowed) == 1)
                for p in range(len(d['profs'])):
                    if p not in allowed:
                        self.model.Add(self._vars['z_prof'][cid, p] == 0)
            for t, (day_t, offset_t) in enumerate(d['slots']):
                covering_starts = [self._vars['start'][cid, s] for s, (day_s, offset_s) in enumerate(d['slots']) if
                                   self._vars['start'][cid, s] is not None and day_s == day_t and offset_s <= offset_t < offset_s +
                                   d['duree_cours'][cid]]
                if covering_starts:
                    self.model.Add(sum(covering_starts) == self._vars['occupe'][cid, t])
                else:
                    self.model.Add(self._vars['occupe'][cid, t] == 0)

    def _add_structural_constraints(self):
        d = self.data
        # 1. Contraintes salles
        self.contrainte_salle(d)
        # 2. Contraintes professeurs
        self.contrainte_professeurs(d)

        # 3. CONTRAINTE ÉTUDIANT
        self.contrainte_etudiant(d)
        # =================================================================
        # 4. CONTRAINTE HIÉRARCHIQUE : les sous-groupes bloquent leur groupe parent
        # =================================================================
        self.contrainte_hierarchique(d)
        self.contrainte_disponibilites_professeurs(d)
        self.contrainte_disponibilites_groupes(d)
        self.contrainte_disponibilites_salles_generalisee(d)
        #self.contrainte_disponibilites_amphi_c(d)
        #test
        self.contrainte_ordre_cm_td_tp(d)
        self.appliquer_ordre_cm_td_tp()
        self.penaliser_fin_tardive(d, cout_penalite=500, limite_offset_fin=20)
        self.contrainte_disponibilites_cour_heure(d)


    def contrainte_hierarchique(self, d: dict[str, Any]):
        print("   -> Ajout des contraintes hiérarchiques (sous-groupes ↔ groupe parent)")

        # Définit la relation : sous-groupe → groupe parent
        hierarchie = {
            "G1A": "G1",
            "G1B": "G1",
            "G2A": "G2",
            "G2B": "G2",
            "G3A": "G3",
            "G3B": "G3",
            "G4A": "G4",
            "G4B": "G4",
            "G5A": "G5",
            "G5B": "G5",
            "G7A": "G7",
            "G7B": "G7",
            "G8A": "G8",
        }

        for sous_groupe, groupe_parent in hierarchie.items():
            if sous_groupe not in d['map_groupe_cours'] or groupe_parent not in d['map_groupe_cours']:
                continue

            print(f"      → {sous_groupe} bloque {groupe_parent} (et vice versa)")

            for t in range(d['nb_slots']):
                # Tous les cours du sous-groupe
                cours_sous = [self._vars['occupe'][cid, t]
                              for cid in d['map_groupe_cours'][sous_groupe]
                              if (cid, t) in self._vars['occupe']]
                # Tous les cours du groupe parent
                cours_parent = [self._vars['occupe'][cid, t]
                                for cid in d['map_groupe_cours'][groupe_parent]
                                if (cid, t) in self._vars['occupe']]

                # On retire les cours du sous-groupe pour éviter double comptage
                cours_parent_clean = [v for v in cours_parent
                                      if not any(
                        v.Name().startswith(f"occupe_{cid}") for cid in d['map_groupe_cours'][sous_groupe])]

                all_concerned = cours_sous + cours_parent_clean
                if all_concerned:
                    self.model.Add(sum(all_concerned) <= 1)

    def contrainte_etudiant(self, d: dict[str, Any]):
        for group_name, course_list in d['map_groupe_cours'].items():
            if len(course_list) > 1:  # seulement si risque de chevauchement
                for t in range(d['nb_slots']):
                    active = [self._vars['occupe'][cid, t]
                              for cid in course_list
                              if (cid, t) in self._vars['occupe']]
                    if active:
                        self.model.Add(sum(active) <= 1)

    def contrainte_professeurs(self, d: dict[str, Any]):
        for t in range(d['nb_slots']):
            for p_idx in range(len(d['profs'])):
                p_vars = []
                for c in d['cours']:
                    cid = c['id']
                    z = self.model.NewBoolVar(f"zact_c{cid}_t{t}_p{p_idx}")
                    self.model.AddMultiplicationEquality(z, [
                        self._vars['occupe'][cid, t],
                        self._vars['z_prof'][cid, p_idx]
                    ])
                    p_vars.append(z)
                self.model.Add(sum(p_vars) <= 1)

    def contrainte_salle(self, d: dict[str, Any]):
        for t in range(d['nb_slots']):
            for r_idx in range(len(d['salles'])):
                q_vars = []
                for c in d['cours']:
                    cid = c['id']
                    q = self.model.NewBoolVar(f"q_c{cid}_t{t}_r{r_idx}")
                    self.model.AddMultiplicationEquality(q, [
                        self._vars['occupe'][cid, t],
                        self._vars['y_salle'][cid, r_idx]
                    ])
                    q_vars.append(q)
                self.model.Add(sum(q_vars) <= 1)

    def contrainte_disponibilites_professeurs(self, d):
        print("   -> Application des disponibilités horaires des professeurs")
        dispos = d.get('disponibilites_profs', {})
        prof_to_teacher_id = d.get("prof_to_teacher_id", {})

        for c in d['cours']:
            cid = c['id']
            duration = d['duree_cours'][cid]
            allowed_indices = c.get('allowed_prof_indices', [])
            if not allowed_indices:
                continue

            for s, (day_idx, offset) in enumerate(d['slots']):
                start_var = self._vars['start'].get((cid, s))
                if start_var is None or offset + duration > d['creneaux_par_jour']:
                    continue

                for p_idx in allowed_indices:
                    prof_name = d['profs'][p_idx]
                    teacher_id = prof_to_teacher_id.get(prof_name)
                    if not teacher_id or teacher_id not in dispos:
                        continue

                    plages = dispos[teacher_id].get(day_idx, [])
                    if not plages:
                        z = self._vars['z_prof'].get((cid, p_idx))
                        if z is not None:
                            self.model.AddBoolOr([start_var.Not(), z.Not()])
                        continue

                    if not any(debut <= offset and offset + duration <= fin for debut, fin in plages):
                        z = self._vars['z_prof'].get((cid, p_idx))
                        if z is not None:
                            self.model.AddBoolOr([start_var.Not(), z.Not()])

    def contrainte_disponibilites_salles(self, d):
        print("   -> Application des disponibilités horaires des salles")
        dispos = d.get('disponibilites_salles', {})

        # 🚨 CORRECTION : On itère sur l'indice physique (0, 1, 2, ...) pour correspondre à y_salle
        nb_salles = len(d['salles'])
        salle_id_map = list(d['salles'].keys())  # Liste ordonnée des IDs de salle (ex: [1, 2, 3, ...])
        nb_salles=len(dispos)
        salle_id_map=list(dispos.keys())

        for c in d['cours']:
            cid = c['id']
            duration = d['duree_cours'][cid]

            for s, (day_idx, offset) in enumerate(d['slots']):
                start_var = self._vars['start'].get((cid, s))
                if start_var is None or offset + duration > d['creneaux_par_jour']:
                    continue

                # p_idx est maintenant l'indice physique (0, 1, 2, ...)
                for p_idx in range(nb_salles):

                    # Le nom de la salle à chercher dans 'dispos' est l'ID réel
                    salle_name = salle_id_map[p_idx]  # Récupère l'ID réel (ex: 1, 2, 3...)

                    # Assurez-vous que salle_name est du bon type (entier ou chaîne) pour 'dispos'
                    # Si dispos utilise des chaînes : salle_name = str(salle_name)

                    if not salle_name or salle_name not in dispos:
                        continue

                    plages = dispos[salle_name].get(day_idx, [])

                    # p_idx est l'indice physique (0, 1, 2...) et correspond à l'indexation de y_salle
                    z = self._vars['y_salle'].get((cid, p_idx))

                    # Si la salle est indisponible (plages vide ou plage non couverte)
                    indisponible = (not plages) or \
                                   (not any(debut <= offset and offset + duration <= fin for debut, fin in plages))

                    if indisponible:
                        if z is not None:
                            self.model.AddBoolOr([start_var.Not(), z.Not()])
                            # Le print est maintenant plus clair :
                            # print(f"BLOQUÉ: Cours {cid} ne peut pas démarrer à {s} ET utiliser salle ID {salle_name} (Indice {p_idx}) Jour {day_idx}")

    from typing import Any

    def contrainte_disponibilites_groupes(self, d: dict[str, Any]):
        """
        Applique les contraintes de disponibilité horaire pour les groupes d'étudiants.

        Un cours ne peut démarrer à un créneau (s) si l'un de ses groupes associés
        n'est pas disponible pendant toute la durée du cours à ce créneau.
        """
        print("   -> Application des disponibilités horaires des groupes")
        # Structure de 'disponibilites_groupes' :
        # { 'GROUPE_ID': { jour_idx: [(debut_creneau, fin_creneau), ...] } }
        dispos = d.get('disponibilites_groupes', {})

        for c in d['cours']:
            cid = c['id']
            duration = d['duree_cours'][cid]
            # map_cours_groupes: { cid: [GROUPE_ID_1, GROUPE_ID_2, ...] }
            groupes_cours = d.get('map_cours_groupes', {}).get(cid, [])

            if not groupes_cours:
                # Si le cours n'a pas de groupe associé, on ne peut pas appliquer cette contrainte
                continue

            for s, (day_idx, offset) in enumerate(d['slots']):
                start_var = self._vars['start'].get((cid, s))
                if start_var is None or offset + duration > d['creneaux_par_jour']:
                    continue

                # Vérifier l'indisponibilité pour CHAQUE groupe associé au cours
                for groupe_id in groupes_cours:

                    # On ne peut imposer de contrainte que si la disponibilité est définie
                    if groupe_id not in dispos:
                        continue

                    # Récupérer les plages horaires disponibles pour ce groupe ce jour-là
                    plages = dispos[groupe_id].get(day_idx, [])

                    # Conditions d'indisponibilité :
                    # 1. Aucune plage n'est définie pour ce jour (plages est vide)
                    # 2. OU aucune des plages définies ne couvre entièrement le cours
                    is_indisponible = (not plages) or \
                                      (not any(debut <= offset and offset + duration <= fin
                                               for debut, fin in plages))

                    if is_indisponible:
                        # Si le groupe est indisponible à ce créneau, le cours NE PEUT PAS y démarrer.
                        # On désactive la variable start(c, s).
                        # 'start' est une variable booléenne qui vaut 1 si le cours c démarre au slot s.
                        self.model.Add(start_var == False)
                        # Note : Add(start_var.Not()) est équivalent à Add(start_var == False)
                        # print(f"BLOQUÉ: Cours {cid} ne peut pas démarrer à {s} (Jour {day_idx}, Offset {offset}) car Groupe {groupe_id} est indisponible.")
                        break  # Un seul groupe indisponible suffit pour bloquer le cours au slot s

    def contrainte_disponibilites_salles_generalisee(self, d):
        print("   -> Application générale des disponibilités horaires des salles (Robuste)")
        dispos = d.get('disponibilites_salles', {})
        print("dispos salles :",dispos)
        if not dispos:
            # Aucune contrainte de disponibilité spécifique à appliquer
            print("      → Aucune disponibilité spécifique trouvée, skipping.")
            return

        # 1. Créer le MAPPING ID_SALLE -> INDICE_PHYSIQUE
        # Ceci est la clé pour lier l'ID de 'dispos' à l'indexation de 'y_salle'
        salle_id_to_idx = {name: i for i, name in enumerate(d['salles'].keys())}
        # Note : Si d['salles'] est une simple liste [ID1, ID2, ...], utilisez:
        # salle_id_to_idx = {name: i for i, name in enumerate(d['salles'])}

        # 2. Itérer sur TOUTES les salles qui ont des contraintes spécifiques
        # On boucle sur l'ID de la salle (la clé du dictionnaire 'dispos')
        for salle_id, contraintes_par_jour in dispos.items():

            # 3. Récupérer l'indice physique (p_idx) pour cette salle
            salle_idx = salle_id_to_idx.get(salle_id)

            if salle_idx is None:
                # La salle dans 'dispos' n'existe pas dans la liste globale des salles du modèle.
                print(f"      → Avertissement : Salle ID {salle_id} dans 'dispos' non trouvée. Ignorée.")
                continue

            # 4. Itérer sur tous les cours et créneaux (S, jour, offset)
            for c in d['cours']:
                cid = c['id']
                duration = d['duree_cours'][cid]

                for s, (day_idx, offset) in enumerate(d['slots']):
                    start_var = self._vars['start'].get((cid, s))
                    if start_var is None or offset + duration > d['creneaux_par_jour']:
                        continue

                    # y_salle[cid, salle_idx] est la variable booléenne qui nous intéresse
                    z_salle = self._vars['y_salle'].get((cid, salle_idx))
                    if z_salle is None:
                        continue

                        # 5. Appliquer la logique de contrainte
                    plages_jour = contraintes_par_jour.get(day_idx, [])
                    if not plages_jour:
                        self.model.AddBoolOr([start_var.Not(), z_salle.Not()])
                        continue
                    # Vérifier si le cours rentre dans l'une des plages disponibles
                    rentre_dans_plage = False
                    for debut, fin in plages_jour:
                        if debut <= offset and offset + duration <= fin:
                            rentre_dans_plage = True
                            break

                    # La salle est indisponible si :
                    # a) il n'y a pas de plages pour ce jour (plages_jour est vide)
                    # b) ou si aucune plage existante ne couvre l'intégralité du cours
                    if not rentre_dans_plage:
                        # Contrainte d'élimination : (start(C, S) est faux) OU (y_salle(C, R) est faux)
                        self.model.AddBoolOr([start_var.Not(), z_salle.Not()])
                        # print(f"BLOQUÉ: Cours {cid} ne peut pas démarrer à {s} ET utiliser salle ID {salle_id}")

    def contrainte_disponibilites_cour_heure(self, d):
        print("   -> Application des horaires obligatoires pour les slots/salles")
        # On utilise 'obligations_slots' pour clarifier l'intention
        obligations = d.get('obligations_slots', {})

        if not obligations:
            print("      → Aucune contrainte d'horaire obligatoire spécifique trouvée, skipping.")
            return

        # 1. Itérer sur TOUS les SLOTS/SALLES qui ont des contraintes d'horaire obligatoires
        for slot_id, contraintes_par_jour in obligations.items():  # Le slot_id est la clé du dictionnaire (e.g., 23000000)
            # 2. Itérer sur tous les cours
            for c in d['cours']:
                cid = c['id']
                id_slot_cour = recup_id_slot_from_str_to_int(cid)  # La fonction qui associe le cours à son slot/salle
                # --- MODIFICATION CLÉ 1 : Cibler UNIQUEMENT les cours associés à ce slot ---
                # Si le cours n'est pas censé utiliser ce slot/salle, on passe au suivant.
                if id_slot_cour != slot_id:
                    continue

                duration = d['duree_cours'][cid]

                # 3. Itérer sur tous les créneaux de temps (S, jour, offset)
                for s, (day_idx, offset) in enumerate(d['slots']):
                    start_var = self._vars['start'].get((cid, s))
                    if start_var is None or offset + duration > d['creneaux_par_jour']:
                        continue
                    # 4. Déterminer si cet horaire (jour, offset) est OBLIGATOIRE
                    creneaux_obligatoires_jour = contraintes_par_jour.get(day_idx, [])
                    # Le cours DOIT commencer à cette heure s'il est affecté à ce slot.
                    # Dans le cas où un jour n'a aucune obligation, le cours n'est PAS autorisé ce jour-là.
                    # C'est une interprétation stricte de "obligatoire".

                    est_horaire_obligatoire = False
                    for debut, fin in creneaux_obligatoires_jour:
                        # Vérifier si le cours (offset, offset + duration) est PARFAITEMENT ÉGAL
                        # à l'un des créneaux obligatoires (debut, fin).
                        # Pour être "obligatoire", on peut exiger une correspondance exacte.
                        # Si c'est juste "doit commencer dans la plage", utiliser :
                        # if debut <= offset and offset + duration <= fin:

                        # Pour l'horaire OBLIGATOIRE, je recommande une correspondance stricte:
                        if debut == offset and fin == offset + duration:
                            est_horaire_obligatoire = True
                            break

                    # --- MODIFICATION CLÉ 2 : Logique Inversée ---
                    # Si le cours est affecté à ce slot (déjà vérifié par 'id_slot_cour == slot_id')
                    # MAIS que l'horaire (s) N'EST PAS l'un des horaires obligatoires
                    if not est_horaire_obligatoire:
                        # Nous BLOQUONS le démarrage du cours à ce slot/créneau.
                        # Contrainte : start(C, S) est faux
                        self.model.AddBoolOr([start_var.Not()])
                        # print(f"BLOQUÉ: Cours {cid} DOIT utiliser slot {slot_id} mais l'horaire {s} n'est pas obligatoire.")

    def contrainte_disponibilites_amphi_c(self, d):
        print("   -> Application des disponibilités de l'Amphi C (version ROBUSTE)")

        liste_amphi_c = d.get("liste_amphi_c")
        if not liste_amphi_c:
            return

        # Trouver l'indice de l'Amphi C
        try:
            amphi_c_idx = next(i for i, name in enumerate(d['salles']) if name == "AmphiC" or name == 16)
            print(f"      → Amphi C trouvé → indice {amphi_c_idx}")
        except StopIteration:
            print("      → Amphi C non trouvé dans les salles")
            return

        for c in d['cours']:
            cid = c['id']
            duration = d['duree_cours'][cid]

            for s, (day_idx, offset) in enumerate(d['slots']):
                start_var = self._vars['start'].get((cid, s))
                if start_var is None:
                    continue
                if offset + duration > d['creneaux_par_jour']:
                    continue

                y_amphi = self._vars['y_salle'][(cid, amphi_c_idx)]

                # Récupérer les plages autorisées ce jour
                plages_jour = liste_amphi_c[day_idx].get(day_idx, [])

                # CAS 1 : pas dispo du tout ce jour → interdit si on veut l'Amphi C
                if not plages_jour:
                    self.model.AddBoolOr([start_var.Not(), y_amphi.Not()])
                    continue

                # CAS 2 : vérifier que le cours rentre dans une plage
                rentre_dans_plage = False
                for debut, fin in plages_jour:
                    if debut <= offset and offset + duration <= fin:
                        rentre_dans_plage = True
                        break

                if not rentre_dans_plage:
                    self.model.AddBoolOr([start_var.Not(), y_amphi.Not()])

    def contrainte_ordre_cm_td_tp(self, d):
        print("   → FORÇAGE ORDRE CM → TD → TP : VERSION QUI MARCHE VRAIMENT")

        # On va extraire proprement le nom de la matière (tout entre le type et le _sXXXXX final)
        cours_par_matiere = {}

        for c in d['cours']:
            cid = c['id']

            # On enlève le dernier élément (_s12345) et on reconstruit la clé matière + groupe
            # Ex: "Sensibilisation à la programmation multimédia BUT3"
            typ,matiere = recup_cours(cid)
            if matiere not in cours_par_matiere:
                cours_par_matiere[matiere] = {"CM": [], "TD": [], "TP": []}
            if typ == "CM":
                cours_par_matiere[matiere]["CM"] = cid
            elif typ == "TD":
                cours_par_matiere[matiere]["TD"].append(cid)
            elif typ == "TP":
                cours_par_matiere[matiere]["TP"].append(cid)

        # Stocke pour application plus tard
        ordres = []
        for key, cours in cours_par_matiere.items():
            cm = cours["CM"]
            for td in cours["TD"]:
                if cm:
                    ordres.append((cm, td))
            for tp in cours["TP"]:
                if cm:
                    ordres.append((cm, tp))
                for td in cours["TD"]:
                    ordres.append((td, tp))
        self._ordres_a_forcer = ordres
        print(f"      → {len(ordres)} relations d'ordre détectées et prêtes (CM→TD→TP)")

    def appliquer_ordre_cm_td_tp(self):
        print("ordre : ",self._ordres_a_forcer)
        if not hasattr(self, '_ordres_a_forcer') or not self._ordres_a_forcer:
            print("      → Aucune contrainte d'ordre à appliquer")
            return
        print(f"   → APPLICATION DES {len(self._ordres_a_forcer)} CONTRAINTES D'ORDRE (CM avant TD avant TP)")
        total_ajoutees = 0

        for cid_avant, cid_apres in self._ordres_a_forcer:
            # Récupère tous les starts valides pour chaque cours
            starts_avant = [(s, var) for (c, s), var in self._vars['start'].items() if
                            c == cid_avant and var is not None]
            starts_apres = [(s, var) for (c, s), var in self._vars['start'].items() if
                            c == cid_apres and var is not None]

            for s1, v1 in starts_avant:
                for s2, v2 in starts_apres:
                    if s1 >= s2:
                        self.model.AddBoolOr([v1.Not(), v2.Not()])
                        total_ajoutees += 1

        print(f"      → {total_ajoutees} contraintes d'interdiction ajoutées → ORDRE FORCÉ À 100%")

    def penaliser_fin_tardive(self, d, cout_penalite: int = 500, limite_offset_fin: int = 20):
        """
        Crée des variables de pénalité booléennes (penalty_late_end) pour tout cours (C)
        qui, s'il démarre à un slot (S), finit après la limite_offset_fin.
        Ces variables seront ajoutées à l'objectif de minimisation.
        """
        print(
            f"   -> Application de la préférence : Pénaliser les fins après le slot {limite_offset_fin} (Coût: {cout_penalite})")

        self.penalites_fin_tardive = []  # Liste pour stocker les variables de pénalité

        for c in d['cours']:
            cid = c['id']
            duration = d['duree_cours'][cid]

            for s, (day_idx, offset) in enumerate(d['slots']):

                start_var = self._vars['start'].get((cid, s))
                if start_var is None:
                    continue

                end_offset = offset + duration

                # Si l'heure de fin dépasse la limite (i.e., finit au slot 21 ou après)
                if end_offset > limite_offset_fin:
                    # Créer une variable booléenne qui est VRAIE si la pénalité est appliquée
                    b_late_end = self.model.NewBoolVar(f'penalty_late_end_{cid}_{s}')

                    # Contrainte d'implication :
                    # Si start(C, S) est VRAI, alors b_late_end DOIT être VRAI
                    # start(C, S) => b_late_end
                    # L'écriture AddBoolOr([start_var.Not(), b_late_end]) est équivalente à l'implication.
                    self.model.AddImplication(start_var, b_late_end)

                    # Stocker la pénalité. On stocke le terme (variable * poids)
                    self.penalites_fin_tardive.append(b_late_end * cout_penalite)

        print(f"      → {len(self.penalites_fin_tardive)} départs de cours tardifs potentiels détectés.")
    def _define_objective_function(self):
        """Définit les contraintes souples et l'objectif de minimisation."""
        d = self.data
        penalites_capacite = []

        # TRANSFORMATION DE LA CONTRAINTE DE CAPACITÉ EN CONTRAINTE SOUPLE
        print("   -> Application de la contrainte de capacité en mode 'souple'.")
        for c in d['cours']:
            cid, group_name = c['id'], c['groups'][0]
            taille_groupe = d['taille_groupes'].get(group_name, 0)

            for r_idx, capacite_salle in enumerate(d['capacites']):
                if taille_groupe > capacite_salle:
                    # Ce cours ne devrait pas être dans cette salle.
                    # On crée une variable de pénalité.
                    penalite = self.model.NewBoolVar(f"penalite_capacite_{cid}_salle_{r_idx}")

                    # Si le cours est assigné à cette salle (y_salle == 1), la pénalité doit être de 1.
                    self.model.Add(self._vars['y_salle'][cid, r_idx] == 1).OnlyEnforceIf(penalite)
                    self.model.Add(self._vars['y_salle'][cid, r_idx] == 0).OnlyEnforceIf(penalite.Not())

                    penalites_capacite.append(penalite)

        self._vars['penalites_capacite'] = penalites_capacite
        print(f"   -> Objectif : Minimiser {len(penalites_capacite)} violations de capacité potentielles.")
        self.model.Minimize(sum(penalites_capacite))
        #self.penaliser_trous_profs(self.data)  # ← nouvelle fonction

        # Objectif final
        obj = sum(penalites_capacite)
        if hasattr(self, 'penalites_trous'):
            obj += sum(self.penalites_trous) * 100  # plus important que la capacité
        self.model.Minimize(obj)

        self._vars['penalites_capacite'] = penalites_capacite

        # --- NOUVEAU : Récupération des pénalités de fin tardive ---
        penalites_tardives = getattr(self, 'penalites_fin_tardive', [])

        # --- Calcul de l'objectif total (Minimisation) ---

        # 1. Pénalités de capacité
        obj_capacite = sum(penalites_capacite) * 1000000  # Multiplier par un poids si vous voulez que ce soit plus coûteux

        # 2. Pénalités de fin tardive
        # Les variables sont déjà multipliées par le cout_penalite (ex: 500)
        obj_tardif = sum(penalites_tardives)

        # 3. (Optionnel) Pénalités de trous (si vous l'ajoutez)
        # obj_trous = sum(self.penalites_trous) * 100

        # Objectif final : Minimiser la somme de tous les coûts
        total_obj = obj_capacite + obj_tardif  # + obj_trous

#        print(
 #           f"   -> Objectif : Minimiser les coûts (Capacité: {len(penalites_capacite)}, Fin Tardive: {len(self.penalites_fin_tardive)} potentiels).")
        self.model.Minimize(total_obj)
