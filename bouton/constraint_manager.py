#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de gestion des contraintes pour l'emploi du temps
Backend pour l'ajout, modification et suppression de contraintes
"""

import mysql.connector
from datetime import datetime, time
from typing import List, Dict, Optional, Tuple
from enum import Enum

class ConstraintType(Enum):
    """Types de contraintes possibles"""
    TEACHER_UNAVAILABLE = "teacher_unavailable"
    ROOM_UNAVAILABLE = "room_unavailable"
    GROUP_UNAVAILABLE = "group_unavailable" 
    MAX_HOURS_PER_DAY = "max_hours_per_day"
    MIN_BREAK = "min_break"
    PREFERRED_SLOT = "preferred_slot"
    NO_CONSECUTIVE = "no_consecutive"
    SAME_DAY_REQUIRED = "same_day_required"
    
class ConstraintPriority(Enum):
    """Niveau de priorité des contraintes"""
    HARD = "hard"  # Contrainte obligatoire (doit être respectée)
    SOFT = "soft"  # Contrainte souhaitée (peut être violée)
    MEDIUM = "medium"  # Contrainte importante (préférable de respecter)

class ConstraintManager:
    """Gestionnaire de contraintes pour l'emploi du temps"""
    
    def __init__(self, host='127.0.0.1', port=33066, database='edt_app', 
                 user='edt_user', password='userpassword'):
        """Initialise le gestionnaire de contraintes"""
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        # Pour éviter de vérifier/migrer en boucle
        self._week_columns_checked = False
        # Vérifie séparément la colonne is_exam (ne pas bloquer les migrations week_id)
        self._is_exam_checked = False
        # Semaine par défaut
        self.default_week_id: Optional[int] = None

    def set_default_week(self, week_id: int):
        """Définit une semaine par défaut utilisée si week_id n'est pas fourni aux insert/select"""
        self.default_week_id = week_id
    
    def _get_connection(self):
        """Crée une connexion à la base de données"""
        return mysql.connector.connect(**self.connection_params)

    # ==================== MIGRATIONS SCHEMA ====================
    def _column_exists(self, cursor, table_name: str, column_name: str):
        """Vérifie si une colonne existe dans la table donnée"""
        cursor.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
            """,
            (table_name, column_name)
        )
        row = cursor.fetchone()
        return (row[0] if isinstance(row, tuple) else row.get('cnt', 0)) > 0

    def _ensure_week_id_column_for(self, cursor, table_name: str, fk_name: str):
        """Ajoute la colonne week_id + index + contrainte FK si absents"""
        if not self._column_exists(cursor, table_name, 'week_id'):
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN week_id INT NULL")
            # Index pour les requêtes par semaine
            try:
                cursor.execute(f"CREATE INDEX idx_{table_name}_week_id ON {table_name}(week_id)")
            except Exception:
                pass
            # Contrainte FK
            try:
                cursor.execute(
                    f"ALTER TABLE {table_name} ADD CONSTRAINT {fk_name} FOREIGN KEY (week_id) REFERENCES weeks(id)"
                )
            except Exception:
                # Contrainte déjà existante ou autre: on ignore
                pass

    def _ensure_week_columns_once(self, conn=None):
        """S'assure une fois que les colonnes week_id existent sur toutes les tables de contraintes"""
        if self._week_columns_checked:
            return
        close_after = False
        if conn is None:
            conn = self._get_connection()
            close_after = True
        cur = conn.cursor()
        try:
            self._ensure_week_id_column_for(cur, 'teacher_constraints', 'fk_teacher_constraints_week_id')
            self._ensure_week_id_column_for(cur, 'room_constraints', 'fk_room_constraints_week_id')
            self._ensure_week_id_column_for(cur, 'group_constraints', 'fk_group_constraints_week_id')
            # noter que l'ajout de is_exam est géré séparément via _ensure_is_exam_column
            conn.commit()
            self._week_columns_checked = True
        except Exception:
            conn.rollback()
            # on ne bloque pas si la migration échoue, mais on laisse l'exception monter si besoin
            raise
        finally:
            cur.close()
            if close_after:
                conn.close()

    def _ensure_is_exam_column(self, conn=None):
        """S'assure que la colonne `is_exam` existe sur `slots`.
        """
        if self._is_exam_checked:
            return
        close_after = False
        if conn is None:
            conn = self._get_connection()
            close_after = True
        cur = conn.cursor()
        try:
            if not self._column_exists(cur, 'slots', 'is_exam'):
                try:
                    cur.execute("ALTER TABLE slots ADD COLUMN is_exam BOOLEAN DEFAULT 0")
                    conn.commit()
                except Exception as e:
                    # Ne pas lever ici : on veut ignorer l'erreur mais laisser la possibilité
                    # de retenter plus tard (ne pas positionner _is_exam_checked à True).
                    conn.rollback()
                    print(f"Avertissement: impossible d'ajouter la colonne is_exam: {e}")
                    return
            # si on arrive ici, la colonne existe (ou a été créée)
            self._is_exam_checked = True
        finally:
            cur.close()
            if close_after:
                conn.close()

    def ensure_is_exam_column(self):
        """Public wrapper: assure that `slots.is_exam` existe.
        """
        # appelle la méthode interne; si une exception survient elle remontera
        self._ensure_is_exam_column()
    
    # ==================== CONTRAINTES ENSEIGNANTS ====================
    
    def add_teacher_unavailability(self, teacher_id: int, day: str, start_time: str, end_time: str, reason: str = None,  priority: ConstraintPriority = ConstraintPriority.HARD, week_id: Optional[int] = None, force_permanent: bool = False):
        """
        Ajoute une contrainte d'indisponibilité pour un enseignant
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # S'assurer que le schéma contient bien week_id (migration si nécessaire)
            self._ensure_week_columns_once(conn)
            # Vérifier que l'enseignant existe
            cursor.execute("SELECT id FROM teachers WHERE id = %s", (teacher_id,))
            if not cursor.fetchone():
                raise ValueError(f"Enseignant {teacher_id} non trouvé")
            
            # Insérer la contrainte
            query = """
                INSERT INTO teacher_constraints 
                (teacher_id, constraint_type, day_of_week, start_time, end_time, 
                 reason, priority, week_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            # Si force_permanent=True, utiliser NULL peu importe week_id
            # Sinon, utiliser week_id fourni ou default_week_id
            if force_permanent:
                ins_week_id = None
            else:
                ins_week_id = week_id if week_id is not None else self.default_week_id
            cursor.execute(query, (
                teacher_id,
                ConstraintType.TEACHER_UNAVAILABLE.value,
                day,
                start_time,
                end_time,
                reason,
                priority.value,
                ins_week_id
            ))
            
            conn.commit()
            constraint_id = cursor.lastrowid
            print(f"Contrainte enseignant créée (ID: {constraint_id})")
            return constraint_id
            
        except Exception as e:
            conn.rollback()
            print(f"Erreur lors de la création de la contrainte: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_teacher_constraints(self, teacher_id: int, week_id: Optional[int] = None):
        """
        Récupère toutes les contraintes d'un enseignant
        """
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            base = """
                SELECT tc.*, u.first_name, u.last_name
                FROM teacher_constraints tc
                JOIN teachers t ON tc.teacher_id = t.id
                JOIN users u ON t.user_id = u.id
                WHERE tc.teacher_id = %s AND tc.active = 1
            """
            params = [teacher_id]
            effective_week_id = week_id if week_id is not None else self.default_week_id
            if effective_week_id is not None:
                # Inclure les contraintes de la semaine spécifique ET les contraintes permanentes (week_id = NULL)
                base += " AND (tc.week_id = %s OR tc.week_id IS NULL)"
                params.append(effective_week_id)
            base += " ORDER BY tc.day_of_week, tc.start_time"
            cursor.execute(base, tuple(params))
            constraints = cursor.fetchall()
            
            print(f" {len(constraints)} contrainte(s) trouvée(s) pour l'enseignant {teacher_id}")
            return constraints
            
        finally:
            cursor.close()
            conn.close()
    
    # ==================== CONTRAINTES SALLES ====================
    
    def add_room_unavailability(self, room_id: int, day: str, start_time: str, end_time: str, reason: str = None, priority: ConstraintPriority = ConstraintPriority.HARD, week_id: Optional[int] = None, force_permanent: bool = False):
        """
        Ajoute une contrainte d'indisponibilité pour une salle
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Migration éventuelle
            self._ensure_week_columns_once(conn)
            # Vérifier que la salle existe
            cursor.execute("SELECT id FROM rooms WHERE id = %s", (room_id,))
            if not cursor.fetchone():
                raise ValueError(f"Salle {room_id} non trouvée")
            
            query = """
                INSERT INTO room_constraints 
                (room_id, constraint_type, day_of_week, start_time, end_time, 
                 reason, priority, week_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            # Si force_permanent=True, utiliser NULL peu importe week_id
            # Sinon, utiliser week_id fourni ou default_week_id
            if force_permanent:
                ins_week_id = None
            else:
                ins_week_id = week_id if week_id is not None else self.default_week_id
            cursor.execute(query, (
                room_id,
                ConstraintType.ROOM_UNAVAILABLE.value,
                day,
                start_time,
                end_time,
                reason,
                priority.value,
                ins_week_id
            ))
            
            conn.commit()
            constraint_id = cursor.lastrowid
            print(f" Contrainte salle créée (ID: {constraint_id})")
            return constraint_id
            
        except Exception as e:
            conn.rollback()
            print(f" Erreur: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_room_constraints(self, room_id: int, week_id: Optional[int] = None):
        """Récupère toutes les contraintes d'une salle"""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            base = """
                SELECT rc.*, r.name as room_name
                FROM room_constraints rc
                JOIN rooms r ON rc.room_id = r.id
                WHERE rc.room_id = %s AND rc.active = 1
            """
            params = [room_id]
            effective_week_id = week_id if week_id is not None else self.default_week_id
            if effective_week_id is not None:
                # Inclure les contraintes de la semaine spécifique ET les contraintes permanentes (week_id = NULL)
                base += " AND (rc.week_id = %s OR rc.week_id IS NULL)"
                params.append(effective_week_id)
            base += " ORDER BY rc.day_of_week, rc.start_time"
            cursor.execute(base, tuple(params))
            constraints = cursor.fetchall()
            
            print(f" {len(constraints)} contrainte(s) trouvée(s) pour la salle {room_id}")
            return constraints
            
        finally:
            cursor.close()
            conn.close()
    
    # ==================== CONTRAINTES GROUPES ====================
    
    def add_group_unavailability(self, group_id: int, day: str, start_time: str, end_time: str, reason: str = None, priority: ConstraintPriority = ConstraintPriority.HARD, week_id: Optional[int] = None, force_permanent: bool = False):
        """Ajoute une contrainte d'indisponibilité pour un groupe"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Migration éventuelle
            self._ensure_week_columns_once(conn)
            cursor.execute("SELECT id FROM `groups` WHERE id = %s", (group_id,))
            if not cursor.fetchone():
                raise ValueError(f"Groupe {group_id} non trouvé")
            
            query = """
                INSERT INTO group_constraints 
                (group_id, constraint_type, day_of_week, start_time, end_time, 
                 reason, priority, week_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            # Si force_permanent=True, utiliser NULL peu importe week_id
            # Sinon, utiliser week_id fourni ou default_week_id
            if force_permanent:
                ins_week_id = None
            else:
                ins_week_id = week_id if week_id is not None else self.default_week_id
            cursor.execute(query, (
                group_id,
                ConstraintType.GROUP_UNAVAILABLE.value,
                day,
                start_time,
                end_time,
                reason,
                priority.value,
                ins_week_id
            ))
            
            conn.commit()
            constraint_id = cursor.lastrowid
            print(f" Contrainte groupe créée (ID: {constraint_id})")
            return constraint_id
            
        except Exception as e:
            conn.rollback()
            print(f" Erreur: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_group_constraints(self, group_id: int, week_id: Optional[int] = None):
        """Récupère toutes les contraintes d'un groupe"""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            base = """
                SELECT gc.*, g.name as group_name
                FROM group_constraints gc
                JOIN `groups` g ON gc.group_id = g.id
                WHERE gc.group_id = %s AND gc.active = 1
            """
            params = [group_id]
            effective_week_id = week_id if week_id is not None else self.default_week_id
            if effective_week_id is not None:
                # Inclure les contraintes de la semaine spécifique ET les contraintes permanentes (week_id = NULL)
                base += " AND (gc.week_id = %s OR gc.week_id IS NULL)"
                params.append(effective_week_id)
            base += " ORDER BY gc.day_of_week, gc.start_time"
            cursor.execute(base, tuple(params))
            constraints = cursor.fetchall()
            
            print(f" {len(constraints)} contrainte(s) trouvée(s) pour le groupe {group_id}")
            return constraints
            
        finally:
            cursor.close()
            conn.close()
    
    # ==================== GESTION DES CONTRAINTES ====================
    
    def delete_constraint(self, constraint_type: str, constraint_id: int):
        """
        Supprime (désactive) une contrainte
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            table_name = f"{constraint_type}_constraints"
            query = f"UPDATE {table_name} SET active = 0 WHERE id = %s"
            cursor.execute(query, (constraint_id,))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                print(f" Contrainte {constraint_id} supprimée")
                return True
            else:
                print(f" Contrainte {constraint_id} non trouvée")
                return False
                
        except Exception as e:
            conn.rollback()
            print(f" Erreur: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def update_constraint_priority(self, constraint_type: str, constraint_id: int, new_priority: ConstraintPriority):
        """Modifie la priorité d'une contrainte"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            table_name = f"{constraint_type}_constraints"
            query = f"UPDATE {table_name} SET priority = %s WHERE id = %s"
            cursor.execute(query, (new_priority.value, constraint_id))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                print(f" Priorité de la contrainte {constraint_id} mise à jour")
                return True
            else:
                print(f" Contrainte {constraint_id} non trouvée")
                return False
                
        except Exception as e:
            conn.rollback()
            print(f" Erreur: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def update_constraint(self, constraint_type: str, constraint_id: int, updates: dict):
        """
        Met à jour une contrainte générique (teacher/room/group).
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            table_name = f"{constraint_type}_constraints"

            # Mapping des clés publiques vers colonnes DB
            key_map = {
                'day': 'day_of_week',
                'day_of_week': 'day_of_week',
                'start_time': 'start_time',
                'end_time': 'end_time',
                'reason': 'reason',
                'priority': 'priority',
                'week_id': 'week_id',
                'active': 'active'
            }

            set_clauses = []
            params = []
            for k, v in updates.items():
                if k not in key_map:
                    continue
                col = key_map[k]
                set_clauses.append(f"{col} = %s")
                # For priority, accept either enum or string
                if k == 'priority' and isinstance(v, ConstraintPriority):
                    params.append(v.value)
                else:
                    params.append(v)

            if not set_clauses:
                return False

            query = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE id = %s"
            params.append(constraint_id)
            cursor.execute(query, tuple(params))
            conn.commit()

            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Erreur mise à jour contrainte: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def update_teacher_constraint(self, constraint_id: int, updates: dict):
        """Wrapper pratique pour mettre à jour une contrainte enseignant."""
        return self.update_constraint('teacher', constraint_id, updates)

    # ==================== SLOTS EXAM FLAG ====================
    def set_slot_exam(self, slot_id: int, is_exam: bool = True):
        """Marque/démarque un slot comme examen en ajoutant/modifiant la colonne `is_exam` sur la table `slots`.

        Retourne True si la ligne a été modifiée, False sinon.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # s'assurer que les colonnes nécessaires existent
            self._ensure_week_columns_once(conn)
            # s'assurer que la colonne is_exam existe (tentative de migration si nécessaire)
            self._ensure_is_exam_column(conn)
            # Mettre à jour la colonne is_exam
            cursor.execute("UPDATE slots SET is_exam = %s WHERE id = %s", (1 if is_exam else 0, slot_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Erreur lors du marquage examen du slot {slot_id}: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_all_constraints(self, week_id: Optional[int] = None):
        """Récupère toutes les contraintes actives du système"""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            constraints = {
                'teachers': [],
                'rooms': [],
                'groups': []
            }
            
            # Contraintes enseignants
            base = """
                SELECT tc.*, u.first_name, u.last_name
                FROM teacher_constraints tc
                JOIN teachers t ON tc.teacher_id = t.id
                JOIN users u ON t.user_id = u.id
                WHERE tc.active = 1
            """
            params: list = []
            effective_week_id = week_id if week_id is not None else self.default_week_id
            if effective_week_id is not None:
                # Inclure les contraintes de la semaine spécifique ET les contraintes permanentes (week_id = NULL)
                base += " AND (tc.week_id = %s OR tc.week_id IS NULL)"
                params.append(effective_week_id)
            base += " ORDER BY tc.day_of_week, tc.start_time"
            cursor.execute(base, tuple(params))
            constraints['teachers'] = cursor.fetchall()
            
            # Contraintes salles
            base = """
                SELECT rc.*, r.name as room_name
                FROM room_constraints rc
                JOIN rooms r ON rc.room_id = r.id
                WHERE rc.active = 1
            """
            params = []
            effective_week_id = week_id if week_id is not None else self.default_week_id
            if effective_week_id is not None:
                # Inclure les contraintes de la semaine spécifique ET les contraintes permanentes (week_id = NULL)
                base += " AND (rc.week_id = %s OR rc.week_id IS NULL)"
                params.append(effective_week_id)
            base += " ORDER BY rc.day_of_week, rc.start_time"
            cursor.execute(base, tuple(params))
            constraints['rooms'] = cursor.fetchall()
            
            # Contraintes groupes
            base = """
                SELECT gc.*, g.name as group_name
                FROM group_constraints gc
                JOIN `groups` g ON gc.group_id = g.id
                WHERE gc.active = 1
            """
            params = []
            effective_week_id = week_id if week_id is not None else self.default_week_id
            if effective_week_id is not None:
                # Inclure les contraintes de la semaine spécifique ET les contraintes permanentes (week_id = NULL)
                base += " AND (gc.week_id = %s OR gc.week_id IS NULL)"
                params.append(effective_week_id)
            base += " ORDER BY gc.day_of_week, gc.start_time"
            cursor.execute(base, tuple(params))
            constraints['groups'] = cursor.fetchall()

            total = sum(len(v) for v in constraints.values())
            print(f" Total: {total} contraintes actives")
            
            return constraints
            
        finally:
            cursor.close()
            conn.close()
    
    def validate_constraint(self, constraint_type: str, day: str, start_time: str, end_time: str):
        """
        Valide qu'une contrainte est cohérente
        """
        # Vérifier le jour
        valid_days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        if day not in valid_days:
            return False, f"Jour invalide: {day}"
        
        # Vérifier les heures
        try:
            start = datetime.strptime(start_time, "%H:%M").time()
            end = datetime.strptime(end_time, "%H:%M").time()
            
            if start >= end:
                return False, "L'heure de fin doit être après l'heure de début"
            
            # Vérifier les heures de cours (8h-20h)
            if start < time(8, 0) or end > time(20, 0):
                return False, "Les contraintes doivent être entre 8h et 20h"
                
        except ValueError as e:
            return False, f"Format d'heure invalide: {e}"
        
        return True, "Contrainte valide"

    # ==================== MAINTENANCE / UTILITAIRES ====================
    def clear_all_constraints(self, hard: bool = True):
        """
        Vide toutes les tables de contraintes.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if hard:
                for table in (
                    'teacher_constraints',
                    'room_constraints',
                    'group_constraints',
                ):
                    cursor.execute(f"TRUNCATE TABLE {table}")
                conn.commit()
            else:
                for table in (
                    'teacher_constraints',
                    'room_constraints',
                    'group_constraints',
                ):
                    cursor.execute(f"UPDATE {table} SET active = 0")
                conn.commit()
            print(" Tables de contraintes vidées avec succès")
        except Exception as e:
            conn.rollback()
            print(f" Erreur lors du vidage des tables: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def clear_constraints_for_week(self, week_id: int, hard: bool = True):
        """Supprime/désactive toutes les contraintes d'une semaine donnée."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if hard:
                for table in ('teacher_constraints','room_constraints','group_constraints'):
                    cursor.execute(f"DELETE FROM {table} WHERE week_id = %s", (week_id,))
                conn.commit()
            else:
                for table in ('teacher_constraints','room_constraints','group_constraints'):
                    cursor.execute(f"UPDATE {table} SET active = 0 WHERE week_id = %s", (week_id,))
                conn.commit()
            print(f" Contraintes de la semaine {week_id} supprimées/désactivées")
        except Exception as e:
            conn.rollback()
            print(f" Erreur lors de la suppression des contraintes de la semaine {week_id}: {e}")
            raise
        finally:
            cursor.close()
            conn.close()


# ==================== FONCTIONS UTILITAIRES ====================

def create_constraint_tables():
    """Crée les tables nécessaires pour stocker les contraintes"""
    conn = mysql.connector.connect(
        host='127.0.0.1',
        port=33066,
        database='edt_app',
        user='edt_user',
        password='userpassword'
    )
    cursor = conn.cursor()
    
    try:
        # Table contraintes enseignants
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS teacher_constraints (
                id INT AUTO_INCREMENT PRIMARY KEY,
                teacher_id INT NOT NULL,
                constraint_type VARCHAR(50) NOT NULL,
                day_of_week VARCHAR(20),
                start_time TIME,
                end_time TIME,
                reason TEXT,
                priority VARCHAR(20) DEFAULT 'hard',
                    week_id INT NULL,
                active BOOLEAN DEFAULT 1,
                created_at DATETIME,
                    FOREIGN KEY (teacher_id) REFERENCES teachers(id),
                    FOREIGN KEY (week_id) REFERENCES weeks(id)
            )
        """)
        
        # Table contraintes salles
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS room_constraints (
                id INT AUTO_INCREMENT PRIMARY KEY,
                room_id INT NOT NULL,
                constraint_type VARCHAR(50) NOT NULL,
                day_of_week VARCHAR(20),
                start_time TIME,
                end_time TIME,
                reason TEXT,
                priority VARCHAR(20) DEFAULT 'hard',
                    week_id INT NULL,
                active BOOLEAN DEFAULT 1,
                created_at DATETIME,
                    FOREIGN KEY (room_id) REFERENCES rooms(id),
                    FOREIGN KEY (week_id) REFERENCES weeks(id)
            )
        """)
        
        # Table contraintes groupes
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS group_constraints (
                id INT AUTO_INCREMENT PRIMARY KEY,
                group_id INT NOT NULL,
                constraint_type VARCHAR(50) NOT NULL,
                day_of_week VARCHAR(20),
                start_time TIME,
                end_time TIME,
                reason TEXT,
                priority VARCHAR(20) DEFAULT 'hard',
                    week_id INT NULL,
                active BOOLEAN DEFAULT 1,
                created_at DATETIME,
                    FOREIGN KEY (group_id) REFERENCES `groups`(id),
                    FOREIGN KEY (week_id) REFERENCES weeks(id)
            )
        """)
        
        conn.commit()
        print(" Tables de contraintes créées avec succès")
        
    except Exception as e:
        conn.rollback()
        print(f" Erreur lors de la création des tables: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
