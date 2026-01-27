from ortools.sat.python import cp_model
import mysql.connector

import recup
from Front import schedule_generator as sg
def connect_db():
    return mysql.connector.connect(
        host='127.0.0.1',
        database='edt_app',
        user='edt_user',
        password='userpassword',
        port=3306
    )
connection = connect_db()

cursor = connection.cursor(dictionary=True)

#cursor.execute("SELECT id FROM years WHERE name = '2023-2024'")
cursor.execute("SELECT id FROM years WHERE name = %s", ("2025-2026",))
year = cursor.fetchone()
year_id = year['id'] if year else None
print("year_id : ", year_id)

cursor.execute("SELECT semester_number FROM semesters WHERE year_id = %s", (year_id,))
semesters = cursor.fetchall()
semester=[]
for s in semesters:
    semester.append(s['semester_number'])
print("semestres : ", semester)

cursor.execute("SELECT name FROM promotions WHERE year_id = %s", (year_id,))
promotions = cursor.fetchall()
promotion=[]
for p in promotions:
    promotion.append(p['name'])
print("promotions : ", promotion)

#cursor.execute("SELECT id, name, promotion_id FROM groups")
#groups = cursor.fetchall()
cursor.execute("SELECT name FROM `groups`")
groups = cursor.fetchall()
group=[]
for g in groups:
    group.append(g['name'])
print("groupes : ", group)

cursor.execute("""
    SELECT id, title, apogee_code, tp_hours_initial, td_hours_initial, cm_hours 
    FROM teachings 
    WHERE title IN ('Initiation au management d’une équipe de projet informatique', 'Projet personnel et professionnel')
""")
teachings = cursor.fetchall()

#print(teachings)

cursor.execute("""
    SELECT u.acronym, u.first_name, u.last_name 
    FROM teachers t 
    JOIN users u ON t.user_id = u.id
""")
teachers = cursor.fetchall()

cursor.execute("SELECT name, seat_capacity FROM rooms")
rooms = cursor.fetchall()
room=[]
for r in rooms:
    room.append(r['name'])
print("salles : ", room)

cursor.execute("SELECT week_number, start_date, end_date FROM weeks WHERE year_id = %s", (year_id,))
weeks = cursor.fetchall()
week=[]
for w in weeks:
    week.append(w['week_number'])
print("semaines : ", week)

# -----------------------
# Paramètres généraux
# -----------------------
jours = 5
# journée 8:00 -> 18:00 en pas de 30 minutes => 10h = 20 créneaux de 30min
creneaux_par_jour = 20
slots = [(d, s) for d in range(jours) for s in range(creneaux_par_jour)]
nb_slots = len(slots)

cursor.execute("SELECT * FROM slots")
slots_bdd = cursor.fetchall()



cursor.execute("SELECT * FROM slots_teachers")
slots_teachers = cursor.fetchall()

#print("slots_bdd",slots_bdd)
#print("slots teachers",slots_teachers)
# fonction d'affichage d'un créneau 30min
def slot_to_time(t:float):
    # t : index dans la journée (0 .. creneaux_par_jour-1)
    h = 8 + (t // 2)
    m = 30 * (t % 2)
    h_end = 8 + ((t + 1) // 2)
    m_end = 30 * ((t + 1) % 2)
    return f"{h:02d}:{m:02d}-{h_end:02d}:{m_end:02d}"

# fenêtre midi 12:00-14:00 correspond aux slots 8..11 inclus (8h->slot0)
midi_window = list(range(8, 12))  # 12:00-14:00 (slots 8,9,10,11)

# -----------------------
# Groupes / cours / durées
# -----------------------
cursor.execute("SELECT acronym FROM slot_types where acronym = 'CM'")
CM = cursor.fetchall()

cours_CM=[]
for cm in CM:
    for i in range(5):
        cours_CM.append(cm['acronym']+str(i+1))
print("cours CM :", cours_CM)

cursor.execute("SELECT acronym FROM slot_types where acronym = 'TD'")
TD = cursor.fetchall()

cours_TD=[]
for td in TD:
    for i in range(10):
        cours_TD.append(td['acronym']+str(i+1))
print("cours TD :", cours_TD)
#print(groups)
#print(teachers)

cursor.execute("SELECT acronym FROM slot_types where acronym = 'TP'")
TP = cursor.fetchall()

cours_TP=[]
for tp in TP:
    for i in range(20):
        cours_TP.append(tp['acronym']+str(i+1))
print("cours TP :", cours_TP)

cursor.execute("SELECT * FROM subgroups")
subgroups = cursor.fetchall()

groupes_TP = []
for g in groups:
    for subg in subgroups:
        groupes_TP.append(g['name'] + subg['name'])
print("groupes TP :", groupes_TP)

cursor.execute("SELECT promotions.student_amount FROM promotions WHERE promotions.year_id = %s;", (year_id,))
taille_promos = cursor.fetchall()
taille_promo=[]
for tp in taille_promos:
    taille_promo.append(tp['student_amount'])
print("taille_promo :", taille_promo)

cursor.execute("SELECT `groups`.student_amount, `groups`.name FROM `groups`")
taille_groupes = cursor.fetchall()
print("taille_groupes :", taille_groupes)

cursor.execute("SELECT subgroups.student_amount, subgroups.name FROM subgroups ")
taille_sous_groupes = cursor.fetchall()
print("taille_sous_groupes :", taille_sous_groupes)

# Construire la liste des cours
cours:list[dict[str, list[str]]] = []

#for f in slots_bdd:
 #   for i in f:
  #      print(i,":",(f[i]))
   # print("----")

#for g in cours_CM + cours_TD + cours_TP:
#    cours.append({"id": f"Cours_{g}", "groups": promotion[0] if g in cours_CM else (group[0:3] if g in cours_TD else (groupes_TP[0:6] if g in cours_TP else []))})

cours_CM=[]
cours_TD=[]
cours_TP=[]
duree_cours = {}

for group in slots_bdd:
    if group['type_id']==1:
        year:int=int(group['promotion_id'])
        year_group:str=recup.recup_year_group_test_CM(year)
        id_ressource:str=group['teaching_id']
        cursor.execute(f"SELECT title FROM teachings WHERE id ={id_ressource}")
        nom_ressource=cursor.fetchall()
        year_groupv1="_"+year_group
        nom_ressource_a_ecrire=nom_ressource[0]['title']+year_groupv1
        cours.append({"id": f"Cours_{nom_ressource_a_ecrire}","groups":[year_group]})
        duration=group['duration']
        cursor.execute(f"SELECT duration FROM slots WHERE teaching_id ={id_ressource} AND type_id ={1}")
        duration1=cursor.fetchall()
        duree_cours[f"Cours_{nom_ressource_a_ecrire}"] = int(2*duration1[0]['duration'])
        cours_CM.append(nom_ressource_a_ecrire)
    elif group['type_id']==2:
        year:int=int(group['group_id'])
        id_ressource:str=group['teaching_id']
        year_group:str=recup.recup_year_group_test_TD(year)
        cursor.execute(f"SELECT title FROM teachings WHERE id ={id_ressource}")
        nom_ressource=cursor.fetchall()
        year_groupv1="_"+year_group
        nom_ressource_a_ecrire=nom_ressource[0]['title']+year_groupv1
        cours.append({"id": f"Cours_{nom_ressource_a_ecrire}","groups":[year_group]})
        cours_TD.append(nom_ressource_a_ecrire)
    elif group['type_id']==3:
        group_id:int=int(group['group_id'])
        year:int=int(group['subgroup_id'])
        id_ressource:str=group['teaching_id']
        year_group:str=recup.recup_year_group_test_TP(group_id,year)
        year_groupv1="_"+year_group
        cursor.execute(f"SELECT title FROM teachings WHERE id ={id_ressource}")
        nom_ressource=cursor.fetchall()
        nom_ressource_a_ecrire=nom_ressource[0]['title']+year_groupv1
        cours.append({"id": f"Cours_{nom_ressource_a_ecrire}","groups":[year_group]})
        cours_TP.append(nom_ressource_a_ecrire)
print("cours : ",cours)

# Durées en nombre de créneaux de 30 minutes
# CM = 1h30 = 3 créneaux
#for g in cours_CM:
#    duree_cours[f"Cours_{g}"] = 3
# TD/TP = 2h = 4 créneaux
for g in cours_TD + cours_TP:
    duree_cours[f"Cours_{g}"] = 4
# Spé = CM => 1h30
nb_spec = 0  # Define nb_spec, set to the desired number of special courses
for i in range(nb_spec):
    duree_cours[f"SpecCourse{i}"] = 3

# -----------------------
# Salles, profs, contraintes initiales
# -----------------------

salles = {
    r["name"]: r["seat_capacity"]
    for r in rooms
}


rooms = list(salles.keys())
nb_rooms = len(rooms)
capacites = [salles[r] for r in rooms]

#profs = ["ProfA", "ProfB", "ProfC", "ProfD", "ProfE", "ProfF", "ProfG", "ProfH"]
profs:list[str] = [t['first_name'] + ' ' + t['last_name'] for t in teachers]
nb_profs = len(profs)

# prof imposé pour spéciaux
speccourse_prof = {}
for i in range(nb_spec):
    speccourse_prof[f"SpecCourse{i}"] = profs[i % nb_profs]

course_possible_profs = {}
for c in cours:
    cid = c["id"]
    if cid in speccourse_prof:
        course_possible_profs[cid] = [speccourse_prof[cid]]
    else:
        course_possible_profs[cid] = profs.copy()

# forbidden start slots (ex: SpecCourse0 ne peut pas démarrer sur 0,1)
course_forbidden_start = {c["id"]: [] for c in cours}
course_forbidden_start["SpecCourse0"] = [0, 1]

# soft preferences: nombre max de "blocs" consécutifs (1 bloc = ancien créneau de 1h30).
# on conserve la même sémantique : max_consecutive_per_group = 2 signifie 'pas plus de 2 blocs (2 * 1h30)'.
# pour convertir en slots 30min on multiplie par 3
max_consecutive_per_group = {g: 2 for g in cours_CM + cours_TD + cours_TP}

# -----------------------
# Modèle
# -----------------------
model = cp_model.CpModel()

# Variables start[cid, s] = cours cid commence au slot s (s doit permettre la durée)
start = {}
# occ[cid, t] = cours cid occupe le slot t (t est index global 0..nb_slots-1)
occ = {}
# room assign y[cid, r] (unique)
y = {}
# prof assign z[cid, p] (unique among allowed)
z = {}

for c in cours:
    cid = c["id"]
    d = duree_cours[cid]
    # starts only where it fits in the week
    for s in range(nb_slots):
        # compute day and offset to forbid starts that would overflow the day
        day, offset = slots[s]
        # index within day
        idx_in_day = offset
        # start allowed if idx_in_day + d <= creneaux_par_jour
        if idx_in_day + d <= creneaux_par_jour:
            start[cid, s] = model.NewBoolVar(f"start_{cid}_{s}")
        else:
            # not possible to start so no variable; we will treat as implicitly 0
            start[cid, s] = None

    # occ variables for every slot
    for t in range(nb_slots):
        occ[cid, t] = model.NewBoolVar(f"occ_{cid}_{t}")

    # room/prof assign
    for r in range(nb_rooms):
        y[cid, r] = model.NewBoolVar(f"y_{cid}_{r}")
    for p in range(nb_profs):
        z[cid, p] = model.NewBoolVar(f"z_{cid}_{p}")

    # Exactly one room, exactly one allowed prof, exactly one start
    model.Add(sum(y[cid, r] for r in range(nb_rooms)) == 1)
    allowed_idx = [profs.index(p) for p in course_possible_profs[cid]]
    model.Add(sum(z[cid, p] for p in allowed_idx) == 1)
    # sum of allowed starts == 1
    starts_list = [start[cid, s] for s in range(nb_slots) if start[cid, s] is not None]
    model.Add(sum(starts_list) == 1)

    # Link starts -> occ:
    # For each slot t, occ[cid,t] == sum_{s : s<=t<=s+d-1} start[cid,s]
    # (since exactly one start, the sum is 0 or 1)
    for t in range(nb_slots):
        covering_starts = []
        for s in range(nb_slots):
            sv = start[cid, s]
            if sv is None:
                continue
            # s is a valid start. Does it cover t?
            # s and t are global indices; need day logic: start must be on same day and cover within day
            day_s, offset_s = slots[s]
            day_t, offset_t = slots[t]
            if day_s != day_t:
                continue
            d_len = duree_cours[cid]
            if offset_s <= offset_t <= offset_s + d_len - 1:
                covering_starts.append(sv)
        if covering_starts:
            model.Add(sum(covering_starts) == occ[cid, t])
        else:
            # no valid start covers t => occ == 0
            model.Add(occ[cid, t] == 0)

# -----------------------
# Contraintes structurelles
# -----------------------

# capacité des salles : si taille > capacite[r] => y[cid,r] == 0
for c in cours:
    cid = c["id"]
    groupname = cid.replace("Cours_", "") if cid.startswith("Cours_") else None
    taille = taille_groupes["student_amount"] if groupname in group else (taille_sous_groupes["student_amount"] if groupname in groupes_TP else (taille_promo[0] if groupname in cours_CM else 0))
    for r in range(nb_rooms):
        if taille > capacites[r]:
            model.Add(y[cid, r] == 0)

# Pas deux cours dans la même salle au même slot
# on crée b[cid,t,r] qui vaut 1 si occ[cid,t] AND y[cid,r]
b = {}
for c in cours:
    cid = c["id"]
    for t in range(nb_slots):
        for r in range(nb_rooms):
            b[cid, t, r] = model.NewBoolVar(f"b_{cid}_{t}_{r}")
            # b -> occ and y
            model.AddBoolAnd([occ[cid, t], y[cid, r]]).OnlyEnforceIf(b[cid, t, r])
            model.AddBoolOr([occ[cid, t].Not(), y[cid, r].Not()]).OnlyEnforceIf(b[cid, t, r].Not())

for t in range(nb_slots):
    for r in range(nb_rooms):
        model.Add(sum(b[c["id"], t, r] for c in cours) <= 1)

# Un prof ne peut pas donner deux cours en même temps :
# pour chaque prof p et slot t, au plus 1 cours a z[c,p]==1 et occ[c,t]==1
for p_idx in range(nb_profs):
    for t in range(nb_slots):
        prof_and_vars = []
        for c in cours:
            cid = c["id"]
            v = model.NewBoolVar(f"profbusy_{p_idx}_{cid}_{t}")
            model.AddBoolAnd([occ[cid, t], z[cid, p_idx]]).OnlyEnforceIf(v)
            model.AddBoolOr([occ[cid, t].Not(), z[cid, p_idx].Not()]).OnlyEnforceIf(v.Not())
            prof_and_vars.append(v)
        model.Add(sum(prof_and_vars) <= 1)

# -----------------------
# Hiérarchie CM -> TD -> TP : pas de chevauchement temporel
# -----------------------



#for cm in cours_CM:
#    for td in cours_TD:
#        for t in range(nb_slots):
#            model.Add(occ[f"Cours_{cm}", t] + occ[f"Cours_{td}", t] <= 1)
#print("occ ",occ)
#for td, tps in cours_TP:
#    for tp in tps:
#        for t in range(nb_slots):
#            model.Add(occ[f"Cours_{td}", t] + occ[f"Cours_{tp}", t] <= 1)

# -----------------------
# Contrainte pause midi minimale (≥ 1h30) pour chaque groupe
# Interprétation utilisée : dans la fenêtre 12:00-14:00 (slots 8..11),
# chaque groupe peut occuper au maximum 1 slot (30min), donc il aura >= 3 slots libres = 1h30.
# -----------------------
group_course_map = {}
for g in cours_CM + cours_TD + cours_TP:
    group_course_map[g] = [c["id"] for c in cours if g in c["groups"]]

for g, clist in group_course_map.items():
    # sum occ of all their courses on midi_window <= 1 (au maximum 30min occupée)
    model.Add(sum(occ[cid, t] for cid in clist for t in midi_window) <= 1)

# -----------------------
# Soft constraints : forbidden starts, max consecutifs (converted en 30-min slots)
# -----------------------
viol_forbidden = []
viol_overconsec = []

# forbidden start slots penalty variables
for c in cours:
    cid = c["id"]
    forb = course_forbidden_start.get(cid, [])
    for s in forb:
        sv = start[cid, s] if (start[cid, s] is not None) else None
        if sv is None:
            # si start impossible, pas besoin de variable de violation pour ce s
            continue
        v = model.NewBoolVar(f"viol_forb_{cid}_{s}")
        # v == 1 iff le cours démarre sur un slot interdit
        model.Add(sv == 1).OnlyEnforceIf(v)
        model.Add(sv == 0).OnlyEnforceIf(v.Not())
        viol_forbidden.append(v)

# max consecutive blocks per group:
# On reconvertit la notion "max_consecutive_per_group[g] (en blocs 1h30)" -> en slots 30min:
# max_slots = max_consecutive_per_group[g] * 3
for g in group_course_map:
    max_blocks = max_consecutive_per_group.get(g, 2)
    max_slots_allowed = max_blocks * 3
    # on parcourt chaque journée et chaque fenêtre de taille max_slots_allowed + 1
    for day in range(jours):
        day_offset = day * creneaux_par_jour
        for start_slot in range(0, creneaux_par_jour - max_slots_allowed):
            window = [day_offset + (start_slot + o) for o in range(max_slots_allowed + 1)]
            v = model.NewBoolVar(f"viol_over_{g}_{day}_{start_slot}")
            model.Add(sum(occ[cid, s] for cid in group_course_map[g] for s in window) >= (max_slots_allowed + 1) * v)
            viol_overconsec.append(v)

# -----------------------
# Objectif : minimiser pénalités
# -----------------------
# On pondère forbiddens plus lourd que overconsec
model.Minimize(10 * sum(viol_forbidden) + 3 * sum(viol_overconsec))

# -----------------------
# Solveur
# -----------------------
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 60
solver.parameters.num_search_workers = 8
status = solver.Solve(model)

# -----------------------
# AFFICHAGE JOUR PAR JOUR (lisible)
# -----------------------
def format_course_block(cid, day, start_offset):
    d = duree_cours[cid]
    start_time = slot_to_time(start_offset)
    # compute end_time (start_offset is local offset in day)
    end_slot_in_day = start_offset + d - 1
    # convert to global slot indices to derive times properly
    # (but slot_to_time expects index-in-day, so reuse)
    # We'll create a nice "start - end" string:
    h0 = 8 + (start_offset // 2)
    m0 = 30 * (start_offset % 2)
    # compute end minute/time:
    tot_minutes = (h0 * 60 + m0) + d * 30
    hend = tot_minutes // 60
    mend = tot_minutes % 60
    return f"{h0:02d}:{m0:02d}-{hend:02d}:{mend:02d} ({d*30}min)"

if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    print("Solution trouvée (status = ", solver.StatusName(status), ")\n")

    # Construire planning slot -> liste des (cours, salle, prof)
    planning = {s: [] for s in range(nb_slots)}
    # aussi stocker les starts pour bel affichage
    starts_actual = {}
    for c in cours:
        cid = c["id"]
        # trouver le start réel
        chosen_start = None
        for s in range(nb_slots):
            sv = start[cid, s]
            if sv is None:
                continue
            if solver.Value(sv) == 1:
                chosen_start = s
                starts_actual[cid] = s
                break
        # trouver salle & prof
        chosen_r = [r for r in range(nb_rooms) if solver.Value(y[cid, r]) == 1]
        chosen_p = [p for p in range(nb_profs) if solver.Value(z[cid, p]) == 1]
        r_str = rooms[chosen_r[0]] if chosen_r else "--"
        p_str = profs[chosen_p[0]] if chosen_p else "--"
        # remplir planning par slots occupés
        if chosen_start is not None:
            day, offset = slots[chosen_start]
            for off in range(duree_cours[cid]):
                t = chosen_start + off
                planning[t].append((cid, r_str, p_str))

    print()
    print("Cours 1ère année : ")
    print()
    # Affichage jour par jour, grouper par créneau (30min)
    for d in range(jours):
        print(f"=== Jour {d+1} ===")
        for t_in_day in range(creneaux_par_jour):
            global_t = d * creneaux_par_jour + t_in_day
            entries = planning[global_t]
            time_str = slot_to_time(t_in_day)
            if entries:
                # afficher chaque cours occupant ce slot
                for (cid, r_str, p_str) in entries:
                    # n'afficher que la ligne de début (pour plus de lisibilité), détecter si c'est le start
                    is_start = (cid in starts_actual and starts_actual[cid] == global_t)
                    if is_start:
                        # afficher durée et détails
                        day_idx, offset = slots[global_t]
                        block_info = format_course_block(cid, d, offset)
                        print(f"  {time_str} : {cid} (Salle: {r_str}, Prof: {p_str}) -> Débute: {block_info}")
                    else:
                        # slot couvert par un cours déjà affiché à son début, on peut afficher un simple continuation
                        print(f"  {time_str} : {cid} (en cours) (Salle: {r_str}, Prof: {p_str})")
            else:
                print(f"  {time_str} : --")
        print("")
        

    
    for d in range(jours):
        print(f"=== Jour {d+1} ===")
        
        for t_in_day in range(creneaux_par_jour):
            global_t = d * creneaux_par_jour + t_in_day
            entries = planning[global_t]
            time_str = slot_to_time(t_in_day)
            if entries:
                # afficher chaque cours occupant ce slot
                for (cid, r_str, p_str) in entries:
                    if {cid}=={"Cours_CM1"} or cid in [f"Cours_TP{i}" for i in range(1, 7)] or cid in [f"Cours_TD{i}" for i in range(1, 4)]:
                        # n'afficher que la ligne de début (pour plus de lisibilité), détecter si c'est le start
                        is_start = (cid in starts_actual and starts_actual[cid] == global_t)
                        if is_start:
                            # afficher durée et détails
                            day_idx, offset = slots[global_t]
                            block_info = format_course_block(cid, d, offset)
                            print(f"  {time_str} : {cid} (Salle: {r_str}, Prof: {p_str}) -> Débute: {block_info}")
                        else:
                            # slot couvert par un cours déjà affiché à son début, on peut afficher un simple continuation
                            print(f"  {time_str} : {cid} (en cours) (Salle: {r_str}, Prof: {p_str})")
            else:
                print(f"  {time_str} : --")
        print("")

    t: dict[str, dict[str, list[str]]] = {
        "A1": {"groupes": ["G1", "G2", "G3", "G1A", "G1B", "G2A", "G2B", "G3A", "G3B"], "cours": []}}
    recup.recup_edt(t, jours, creneaux_par_jour, starts_actual, slots, planning, duree_cours, 0, 3, 0, 6, 1)

    sg.generate_schedule("A1",1,t["A1"]["groupes"],t["A1"]["cours"])

    t:    dict[str, dict[str, list[str]]] = {"A2":{"groupes":["G4","G5","G4A","G4B","G5A","G5B"],"cours":[]}}

    recup.recup_edt(t,jours,creneaux_par_jour,starts_actual,slots,planning,duree_cours,3, 5, 7, 10, 2)
    print("t :", t)

    #fig, ax = plt.subplots()
    #sg.generate_schedule("A2",1,t["A2"]["groupes"],t["A2"]["cours"])
    #sg.plt.show()
    t:    dict[str, dict[str, list[str]]] = {"A3":{"groupes":["G7","G8","G7A","G7B","G8A"],"cours":[]}}
    recup.recup_edt(t,jours,creneaux_par_jour,starts_actual,slots,planning,duree_cours,5, 7, 12, 16, 3)
    print("t :", t)
    #sg.generate_schedule("A3",1,t["A3"]["groupes"],t["A3"]["cours"])
    # Affichage violations soft
    viols = []
    for v in viol_forbidden + viol_overconsec:
        if solver.Value(v) == 1:
            viols.append(str(v.Name()))
    if viols:
        print("Contraintes soft non respectées :")
        for vv in viols:
            print(" -", vv)
    else:
        print("Toutes les contraintes soft sont respectées !")

else:
    print("Aucune solution trouvée : status =", solver.StatusName(status))


print("creneaux : ",creneaux_par_jour)
#sg.create_template()
