- BOCQUET Lucas: lbocquet0
- CHASTENET Valentin: 002Nero
- DESCOUTURES Cathy: Cat-dcts
- DESMOND Romain: RomainDesmond
- GENDRY Marine: Wiiinterz

# SAE01Algo

> ⚠️ Ce dépôt est le **second dépôt** de l'application principale. Pour tester le projet, l'application complète doit être lancée.

## Configuration de la base de données

### Prérequis
- Docker installé
- IDE (comme VSCode) avec une extension de base de données

### Étapes

1. Ouvrir Docker
2. Dans le terminal VSCode, exécuter (depuis l'application principale) :
```bash
docker-compose up -d --build
```


## Tester le projet

Pour lancer le générateur d'emploi du temps, exécuter en ligne de commande :

```bash
python .\app.py --id_semaine 222
```

> Remplacer `222` par l'identifiant de la semaine souhaitée.


## Générateur d'emploi du temps

### Fonctions principales

- **`generate_schedule()`** : Fonction principale pour créer un emploi du temps
- **`create_template()`** : Crée le modèle principal de l'emploi du temps
- **`add_courses()`** : Formate les données des cours et les ajoute au modèle

### Exemple d'utilisation

Format des cours :
(jour, heure_debut, nombre_creneaux, nom_cours, nom_professeur, nom_salle, type_cours, groupes)

```python
from SAE01Algo.Front.schedule_generator import generate_schedule

generate_schedule(
    promotion="A1",
    week="S1",
    groups=["G1", "G1A", "G1B", "G1C", "G2", "G2A", "G2B", "G2C"],
    courses=[
        ("Lundi", "8:00", 2, "R4.11.Programmation", "Dupont A.", "R20", "CM", None),
        ("Mardi", "10:00", 2, "R4.05.Réseaux", "Martin L.", "108", "TP", [0, 'A']),
        # ...
    ],
    custom_file_name=None
)
```

## Structure du projet

```
SAE01Algo/
├── Front/
│   └── schedule_generator.py
├── Database/
│   └── Creation_donnees.sql
│   └── Creation_tables.sql
├── docker-compose.yml
├── app.py
├── db_utils.py
├── data_provider_id.py
├── time_table_model.py
├── solution_visualizer.py
├── diagnose.py
├── function.py
├── local_generator.py
├── requirements.txt
└── README.md
```

## Démarrage rapide

1. Cloner le dépôt
2. Configurer la base de données en suivant la section ci-dessus
3. Installer les dépendances Python :
```bash
pip install -r requirements.txt
```
4. Créer un fichier `.env` avec la configuration de la base de données :
```
DB_HOST=[host]
DB_PORT=[port]
DB_DATABASE=[db]
DB_USER=[user]
DB_PASSWORD=[pwd]
```
5. Lancer le générateur d'emploi du temps :
```bash
python .\app.py --id_semaine 222
```
