- BOCQUET Lucas: lbocquet0
- CHASTENET Valentin: 002Nero
- DESCOUTURES Cathy: Cat-dcts
- DESMOND Romain: RomainDesmond
- GENDRY Marine: Wiiinterz

# SAE01Algo

## Database Setup:

### Prerequisites
- Docker installed
- IDE (like VSCode) with database exetension

1. Open Docker
2. In VSCode terminal run:
docker-compose up -d --build

3. In Database extension, create a new connection with:

- **Name** : edt_app
- **Username** : edt_user
- **Password** : userpassword


## Schedule Generator:

### Main Functions

- **`generate_schedule()`** : Main function to create schedule
- **`create_template()`** : Create the main template using schedule
- **`add_courses()`** : Formats course data and add them to the template

### Usage Example

Courses template
(day, start_hour, slot_number, course_name, teacher_name, room_name, course_type, groups)
```python
from SAE01Algo.Front.schedule_generator import     generate_schedule(promotion ="A1",
week="S1",
groups = ["G1","G1A","G1B","G1C", "G2","G2A","G2B","G2C"],
courses = [
    ("Lundi", "8:00", 2, "R4.11.Programmation", "Dupont A.", "R20", "CM", None),
    ("Mardi", "10:00", 2, "R4.05.Réseaux", "Martin L.", "108", "TP", [0, 'A']), ...],
custom_file_name= None)

```

## Project Structure

```
SAE01Algo/
├── Front/
│   └── schedule_generator.py
├── Database/
│   └── Create_data.sql
│   └── Create_tables.sql
├── docker-compose.yml
└── README.md
```

## Getting Started
1. Clone the repository
2. Set up the database following the Database Setup section
3. Install Python dependencies
4. Use the schedule generator functions to create your schedule
