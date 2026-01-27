from sqlalchemy import create_engine
from typing import Dict, Any, Tuple

import pandas as pd
from sqlalchemy import create_engine

#TODO Faire une refacto des fonctions afin qu'il y ait moins de duplication et que ce soit plus compréhensible et renommage.
def get_end_time(row) -> str:
    if pd.isna(row['end_time']):
        return ""
    return str(row['end_time'])[-8:]


def get_start_time(row) -> str:
    if pd.isna(row['start_time']):
        return ""
    return str(row['start_time'])[-8:]


def convert_daystring_to_int(day: str) -> int:
    days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
    return days.index(day)

def convert_days_int_to_string(day:int)->str:
    days=['Lundi','Mardi','Mercredi','Jeudi','Vendredi']
    return days[day]

def _time_to_slot(time_str: str) -> int:
    """'13:30:00' → 11 (8h=0, 8h30=1, ..., 13h30=11)"""
    if pd.isna(time_str):
        return 0
    h, m, _ = map(int, str(time_str).split(':'))
    return (h - 8) * 2 + (m // 30)
def get_availabilityProf_From_Unavailable(df_dispos,creneaux_par_jour):
    disponibilites_profs = {}
    indisponibilites_profs = {}
    indisponibilites_profs=recuperation_indisponibilites(df_dispos, indisponibilites_profs)

    disponibilites_profs=recuperation_disponibilites_profs(creneaux_par_jour, disponibilites_profs, indisponibilites_profs)
    return disponibilites_profs


def recuperation_disponibilites_profs(creneaux_par_jour, disponibilites_profs: dict[Any, Any],
                                      indisponibilites_profs: dict[Any, Any])-> dict[Any, Any]:
    liste_jour=['Lundi','Mardi','Mercredi','Jeudi','Vendredi']
    for i in indisponibilites_profs:
        for day in liste_jour:
            if day in indisponibilites_profs[i]:
                h_min = 0
                h_max = creneaux_par_jour
                for k in indisponibilites_profs[i][day]:
                    if k[0] == '':
                        continue
                    else:
                        if h_min < k[1] < creneaux_par_jour:
                            h_min = k[1]
                            disponibilites_profs.setdefault(i, {}).setdefault(liste_jour.index(day), []).append((h_min + 1, h_max))
                            continue
                        if h_max > k[0]:
                            h_max = k[0]
                            disponibilites_profs.setdefault(i, {}).setdefault(liste_jour.index(day), []).append((h_min, h_max - 1))
            else:
                disponibilites_profs.setdefault(i, {}).setdefault(liste_jour.index(day), []).append((0, creneaux_par_jour))
    return disponibilites_profs


def recuperation_indisponibilites(df_dispos, indisponibilites_profs: dict[Any, Any])-> dict[Any, Any]:
    for _, row in df_dispos.iterrows():
        teacher_id = row['teacher_id']
        day_id = (row['day_of_week'])  # 0 = lundi, 4 = vendredi
        debut_str = get_start_time(row)
        fin_str = get_end_time(row)
        if debut_str != "":
            debut_slot = _time_to_slot(debut_str)
            fin_slot = _time_to_slot(fin_str)
        else:
            debut_slot = ""
            fin_slot = ""
        indisponibilites_profs.setdefault(teacher_id, {}).setdefault(day_id, []).append((debut_slot, fin_slot))
    return indisponibilites_profs


def get_availabilityRoom_From_Unavailable(df_dispos,creneaux_par_jour):
    disponibilites_salles = {}
    indisponibilites_salles = {}
    indisponibilites_salles=recuperation_indisponibilites_rooms(df_dispos, indisponibilites_salles)

    disponibilites_salles=recuperation_disponibilites_rooms(creneaux_par_jour, disponibilites_salles, indisponibilites_salles)
    print("indisponibilites_salles : ",indisponibilites_salles)
    print("disponibilites_salles : ",disponibilites_salles)
    #disponibilites_salles= {16: {0: [(9, 23)], 1: [(0, 9)], 2: [(0, 9)], 4: [(9, 20)]}}

    return disponibilites_salles


def recuperation_disponibilites_rooms(creneaux_par_jour, disponibilites_salles: dict[Any, Any],
                                      indisponibilites_salles: dict[Any, Any])-> dict[Any, Any]:
    liste_jour=['Lundi','Mardi','Mercredi','Jeudi','Vendredi']
    for i in indisponibilites_salles:
        for day in liste_jour:
            if day in indisponibilites_salles[i]:
                print("day : ", day)
                h_min = 0
                h_max = creneaux_par_jour
                for k in indisponibilites_salles[i][day]:
                    if k[0] == '':
                        continue
                    else:
                        if h_min < k[1] < creneaux_par_jour:
                            h_min = k[1]
                            disponibilites_salles.setdefault(i, {}).setdefault(liste_jour.index(day), []).append((h_min + 1, h_max))
                            continue
                        if h_max > k[0]:
                            h_max = k[0]
                            disponibilites_salles.setdefault(i, {}).setdefault(liste_jour.index(day), []).append((h_min, h_max - 1))
            else:
                disponibilites_salles.setdefault(i, {}).setdefault(liste_jour.index(day), []).append((0, creneaux_par_jour))
    return disponibilites_salles
def recup_cours(cid:str):
    id_cour= cid.split("_")
    type_cour= id_cour[0]
    nom_cour= id_cour[1]

    return type_cour,nom_cour
def recup_id_slot_from_str_to_int(cid:str):
    id_cour = cid.split("_")
    id_slot = id_cour[-1]
    return int(id_slot[1:])

def recuperation_indisponibilites_rooms(df_dispos, indisponibilites_profs: dict[Any, Any])-> dict[Any, Any]:
    for _, row in df_dispos.iterrows():
        room_id = row['room_id']
        day_id = (row['day_of_week'])  # 0 = lundi, 4 = vendredi
        debut_str = get_start_time(row)
        fin_str = get_end_time(row)
        if debut_str != "":
            debut_slot = _time_to_slot(debut_str)
            fin_slot = _time_to_slot(fin_str)
        else:
            debut_slot = ""
            fin_slot = ""
        indisponibilites_profs.setdefault(room_id, {}).setdefault(day_id, []).append((debut_slot, fin_slot))
    return indisponibilites_profs


def get_availabilityGroup_From_Unavailable(df_dispos,creneaux_par_jour):
    disponibilites_groupes = {}
    indisponibilites_groupes = {}
    indisponibilites_groupes=recuperation_indisponibilites_group(df_dispos, indisponibilites_groupes)

    disponibilites_groupes=recuperation_disponibilites_group(creneaux_par_jour, disponibilites_groupes, indisponibilites_groupes)
    return disponibilites_groupes


def recuperation_disponibilites_group(creneaux_par_jour, disponibilites_groupes: dict[Any, Any],
                                      indisponibilites_groupes: dict[Any, Any])-> dict[Any, Any]:
    liste_jour=['Lundi','Mardi','Mercredi','Jeudi','Vendredi']
    for i in indisponibilites_groupes:
        for day in liste_jour:
            if day in indisponibilites_groupes[i]:
                h_min = 0
                h_max = creneaux_par_jour
                for k in indisponibilites_groupes[i][day]:
                    if k[0] == '':
                        continue
                    else:
                        if h_min < k[1] < creneaux_par_jour:
                            h_min = k[1]
                            disponibilites_groupes.setdefault(i, {}).setdefault(liste_jour.index(day), []).append((h_min + 1, h_max))
                            continue
                        if h_max > k[0]:
                            h_max = k[0]
                            disponibilites_groupes.setdefault(i, {}).setdefault(liste_jour.index(day), []).append((h_min, h_max - 1))
            else:
                disponibilites_groupes.setdefault(i, {}).setdefault(liste_jour.index(day), []).append((0, creneaux_par_jour))
    return disponibilites_groupes


def recuperation_indisponibilites_group(df_dispos, indisponibilites_groupes: dict[Any, Any])-> dict[Any, Any]:
    for _, row in df_dispos.iterrows():
        group_id = row['group_id']
        day_id = (row['day_of_week'])  # 0 = lundi, 4 = vendredi
        debut_str = get_start_time(row)
        fin_str = get_end_time(row)
        if debut_str != "":
            debut_slot = _time_to_slot(debut_str)
            fin_slot = _time_to_slot(fin_str)
        else:
            debut_slot = ""
            fin_slot = ""
        indisponibilites_groupes.setdefault(group_id, {}).setdefault(day_id, []).append((debut_slot, fin_slot))
    return indisponibilites_groupes

def get_availabilitySlot_From_Unavailable(df_dispos,creneaux_par_jour):
    indisponibilites_groupes = {}
    disponibilites_slot=recuperation_indisponibilites_slot(df_dispos, indisponibilites_groupes)
    return  disponibilites_slot

def recuperation_disponibilites_slot(creneaux_par_jour, disponibilites_groupes: dict[Any, Any],
                                      indisponibilites_groupes: dict[Any, Any])-> dict[Any, Any]:
    liste_jour=['Lundi','Mardi','Mercredi','Jeudi','Vendredi']
    for i in indisponibilites_groupes:
        for day in liste_jour:
            if day in indisponibilites_groupes[i]:
                h_min = 0
                h_max = creneaux_par_jour
                for k in indisponibilites_groupes[i][day]:
                    if k[0] == '':
                        continue
                    else:
                        if h_min < k[1] < creneaux_par_jour:
                            h_min = k[1]
                            disponibilites_groupes.setdefault(i, {}).setdefault(liste_jour.index(day), []).append((h_min + 1, h_max))
                            continue
                        if h_max > k[0]:
                            h_max = k[0]
                            disponibilites_groupes.setdefault(i, {}).setdefault(liste_jour.index(day), []).append((h_min, h_max - 1))
            else:
                disponibilites_groupes.setdefault(i, {}).setdefault(liste_jour.index(day), []).append((0, creneaux_par_jour))
    return disponibilites_groupes


def recuperation_indisponibilites_slot(df_dispos, indisponibilites_groupes: dict[Any, Any])-> dict[Any, Any]:
    liste_jour=['Lundi','Mardi','Mercredi','Jeudi','Vendredi']

    for _, row in df_dispos.iterrows():
        slot_id = row['slot_id']
        day_id = (row['day_of_week'])  # 0 = lundi, 4 = vendredi
        debut_str = get_start_time(row)
        fin_str = get_end_time(row)
        if debut_str != "":
            debut_slot = _time_to_slot(debut_str)
            fin_slot = _time_to_slot(fin_str)
        else:
            debut_slot = ""
            fin_slot = ""
        indisponibilites_groupes.setdefault(slot_id, {}).setdefault(liste_jour.index(day_id), []).append((debut_slot, fin_slot))
    return indisponibilites_groupes


class FunctionTest:
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self.engine = create_engine(
            f"mysql+mysqlconnector://{db_config['user']}:{db_config['password']}@"
            f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )
    def load_and_prepare_data(self):
        week_id=221
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
        df_dispos_profs = pd.read_sql(query_dispos, self.engine, params={"week_id": week_id})
        print("test Prof",get_availabilityProf_From_Unavailable(df_dispos_profs,20)) # changer le 20 en une valeur étant le nombre de créneau

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
        print("Test salles : ",get_availabilityRoom_From_Unavailable(df_dispos_salles,23)) # changer le 20 en une valeur étant le nombre de créneau

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
        print("Test Group",get_availabilityGroup_From_Unavailable(df_dispos_groupes,20))

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
        print("Test slot : ",get_availabilitySlot_From_Unavailable(df_dispos_slots,20))



if __name__ == "__main__":
    DB_CONFIG = {
        'host': '127.0.0.1', 'database': 'provisional_calendar',
        'user': 'root', 'password': 'secret', 'port': 3306
    }
    data_provider = FunctionTest(DB_CONFIG)
    data_provider.load_and_prepare_data()
    print(recup_cours("CM_R1.01 Initiation au développement_BUT1_s7000000"))
    print(recup_id_slot_from_str_to_int("développement_BUT1_s7000000"))