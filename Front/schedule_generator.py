import datetime
import gc
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.axes import Axes
import textwrap
import os
from typing import Tuple, List, Dict, Any

FONT_SIZE=7

def get_color(type: str) -> str:
    """Function which returns the color associated with a course type

    Args:
        type (str): Courses type

    Returns:
        str: Hexadecimal color
    """
    if type == "CM":
        return '#FDE74C'
    elif type == "TP":
        return '#809BCE'
    elif type == "TD":
        return '#FFDDD2'
    elif type == "SAE":
        return '#20BF55'
    elif type == "Controle":
        return '#A26769'
    else:
        return "#D6D6D6"


def create_template(promotion: str, week: str, days: list[str], hours: list[str], year_group: list[str]) -> None:
    """Create the schedule template based on the number of groups

    Args:
        promotion (str): Name of the promotion
        week (str): Week number
        days (list): List of days in the schedule
        hours (list): List of time slots
        year_group (list): Group of the promotion

    Returns:
        _type_: Schedule data necessary for course management
    """

    _, ax = plt.subplots(figsize=(11, 9))
    
    group_structure = {}
    main_group = [groupname for groupname in year_group if len(groupname) == 2]
    
    line_number = len(main_group)
    for index, main_group in enumerate(main_group):
        subgroups = [group for group in year_group if group.startswith(main_group) and len(group) == 3]
        
        subgroups_letters = sorted([g[-1] for g in subgroups])

        
        group_structure[index] = {
            'name': main_group,
            'subgroups': subgroups,
            'subgroup_letters': subgroups_letters,
            'num_subgroups': len(subgroups_letters)
        }

    for index, hour in enumerate(hours):
        if hour == "12:00":
            ax.add_patch(patches.Rectangle((index, 0), 3, len(days)*line_number, fill=False, edgecolor="red", linewidth=1.5))

        for day in range(len(days)):
            for group in range(line_number):
                idx = day*line_number + group
                ax.add_patch(patches.Rectangle((index, idx), 1, 1, fill=False, edgecolor="grey", linewidth=0.8))

    # Days separation lines
    for day in range(1, len(days)):
        ax.axhline(y=day*line_number, color="black", linewidth=2, alpha=0.7, zorder=0)

    # Separation lines for groups A/B
    for day in range(len(days)):
        for group in range(line_number):
            structure = group_structure[group]
            if structure['num_subgroups'] > 1:
                # Create dashed lines for each subgroup
                for i in range(1, structure['num_subgroups']):
                    y : float = day*line_number + group + (i / structure['num_subgroups'])
                    ax.axhline(y=y, color="black", linewidth=1, linestyle=(0, (3, 5)), alpha=0.7, zorder=0)

    # Days and hours settings
    ax.set_xlim(0, len(hours))
    ax.set_ylim(0, len(days)*line_number)
    ax.set_xticks([index for index in range(len(hours))])
    ax.set_xticklabels(hours)
    ax.set_xticklabels(hours, rotation=90, fontsize=8)


    ax.invert_yaxis()  # Inversion of the y-axis
    ax_top = ax.secondary_xaxis('top') #Duplication of the x-axis at the top
    ax_top.set_xticks([index for index in range(len(hours))])
    ax_top.set_xticklabels(hours)
    ax_top.set_xticklabels(hours, rotation=90, fontsize=8)

    ax.set_title(f"Emploi du temps {promotion} - S{week} (Création: {datetime.date.today()} {datetime.datetime.now().strftime('%H:%M:%S')}) ", fontsize=8, fontweight="bold", pad=-10)
    yticks = [day*line_number + group + 0.5 for day in range(len(days)) for group in range(line_number)]
    yticklabels = ["" for _ in yticks]
    ax.set_yticks(yticks)
    ax.set_yticklabels(yticklabels)
    ax.tick_params(axis="y", length=0)

    for day in range(len(days)):
        ax.text(-1.6, day*line_number + line_number/2, days[day], va="center", ha="right", fontsize=12, fontweight="bold")

    #Show group and subgroup labels
    for day in range(len(days)):
        for group in range(line_number):
            idx = day*line_number + group
            structure = group_structure[group]

            # Main group labels
            ax.text(-1.1, idx + 0.5, structure['name'], va="center", ha="center", fontsize=10, color="black", fontweight="bold")

            # Subgroup labels
            if structure['num_subgroups'] > 1:
                # Show each subgroup letter at its position
                for i, letter in enumerate(structure['subgroup_letters']):
                    y_pos = idx + (i + 0.5) / structure['num_subgroups']
                    ax.text(-0.5, y_pos, letter, va="center", ha="center", fontsize=8, color="black")
            elif structure['num_subgroups'] == 1:
                # Only one subgroup, show it centered
                ax.text(-0.5, idx + 0.5, structure['subgroup_letters'][0], va="center", ha="center", fontsize=9, color="black")

    plt.tight_layout(rect=[0.08, 0.05, 2, 1.93])
    plt.subplots_adjust(left=1.3)
    plt.tight_layout()

    return ax, line_number, plt, group_structure


def wrap_text_to_fit_rectangle(course_type: str, name: str, teacher: str, room: str, duration: float, line_number: int) -> str:
    """Function that formats the text to fit in the rectangle

        Args:
            course_type (str): Courses type (CM, TD, etc.)
            name (str): Courses name
            teacher (str): Teacher name
            room (str): Room
            duration (float): Duration of the course in 30min slots (length of the rectangle)
            line_number (int): Number of lines (width of the rectangle)

        Returns:
            str: Formatted text to display in the rectangle
    """
    # Constraints
    chars_per_unit = max(6, 12 - FONT_SIZE)
    max_chars_per_line = max(5, int(duration * chars_per_unit) - 2)
    lines_per_unit = max(2, 6 - FONT_SIZE // 2)
    max_lines = max(1, int(line_number * lines_per_unit))
    
    if course_type == "CM":
        # Formatting the teacher's name
        if teacher and teacher.strip() != "":
            words_teacher = teacher.strip().split()
            if len(words_teacher) >= 2:
                nom = words_teacher[0]
                prenom = " ".join(words_teacher[1:])
                teacher_formatted = f"{nom}.{prenom[0].upper()}"
            else:
                teacher_formatted = teacher
        else:
            teacher_formatted = teacher
        
        essential_parts = [teacher_formatted, room]
        essential_lines: list[str] = []
        
        for part in essential_parts:
            if len(part) <= max_chars_per_line:
                essential_lines.append(part)
            else:
                wrapped = textwrap.wrap(part, width=max_chars_per_line, 
                                      break_long_words=True, break_on_hyphens=True)
                essential_lines.extend(wrapped)
        
        remaining_lines = max(1, max_lines - len(essential_lines))
        
        course_lines = []
        
        if "R" in name and "." in name:
            import re
            match = re.search(r'R\d+\.\d+', name) 
            if match:
                resource = match.group()
                rest_of_name = name.replace(resource, "").strip()
                if rest_of_name.startswith(" "):
                    rest_of_name = rest_of_name[1:].strip()
                
                if len(name) <= max_chars_per_line:
                    course_lines = [name]
                else:
                    if remaining_lines >= 2:
                        course_lines = [resource]
                        if rest_of_name:
                            remaining_for_rest = remaining_lines - 1
                            wrapped_rest = textwrap.wrap(rest_of_name, width=max_chars_per_line, 
                                                       break_long_words=True, break_on_hyphens=True)
                            if len(wrapped_rest) <= remaining_for_rest:
                                course_lines.extend(wrapped_rest)
                            else:
                                course_lines.extend(wrapped_rest[:remaining_for_rest-1])
                                last_part = wrapped_rest[remaining_for_rest-1]
                                if len(last_part) <= max_chars_per_line - 3:
                                    course_lines.append(last_part + "...")
                                else:
                                    course_lines.append(last_part[:max_chars_per_line-3] + "...")
                    else:
                        course_lines = [resource]
            else:
                wrapped_name = textwrap.wrap(name, width=max_chars_per_line, 
                                           break_long_words=True, break_on_hyphens=True)
                
                if len(wrapped_name) <= remaining_lines:
                    course_lines = wrapped_name
                else:
                    course_lines = wrapped_name[:remaining_lines-1]
                    if course_lines:
                        last_line = course_lines[-1]
                        if len(last_line) <= max_chars_per_line - 3:
                            course_lines.append("...")
                        else:
                            course_lines[-1] = last_line[:max_chars_per_line-3] + "..."
                    else:
                        course_lines = [name[:max_chars_per_line-3] + "..."]
        else:
            wrapped_name = textwrap.wrap(name, width=max_chars_per_line, 
                                       break_long_words=True, break_on_hyphens=True)
            
            if len(wrapped_name) <= remaining_lines:
                course_lines = wrapped_name
            else:
                course_lines = wrapped_name[:remaining_lines-1]
                if course_lines:
                    last_line = course_lines[-1]
                    if len(last_line) <= max_chars_per_line - 3:
                        course_lines.append("...")
                    else:
                        course_lines[-1] = last_line[:max_chars_per_line-3] + "..."
                else:
                    course_lines = [name[:max_chars_per_line-3] + "..."]
        
        all_lines = course_lines + essential_lines
        return '\n'.join(all_lines)
    
        
    elif course_type in ["TD", "TP"]:
        if "R" in name and "." in name:
            import re
            match = re.search(r'R\d+\.\d+', name)
            resource = match.group() if match else name.split(".")[0]
        else:
            resource = name
        
        if teacher and teacher.strip() != "":
            words_teacher = teacher.strip().split()
            initials = "".join([word[0].upper() for word in words_teacher if word])
            text = f"{resource} - {initials} - {room}"
        else:
            text = f"{resource} - {room}"
            
    elif course_type == "SAE":
        if "SAE" in name:
            import re
            match = re.search(r'SAE\.?\d*', name)
            sae_code = match.group() if match else name
        else:
            sae_code = name
        
        if teacher and teacher.strip() != "":
            words_teacher = teacher.strip().split()
            initials = "".join([word[0].upper() for word in words_teacher if word])
            text = f"{sae_code} - {initials} - {room}"
        else:
            text = f"{sae_code} - {room}"
            
    else:  
        if teacher and teacher.strip() != "":
            words_teacher = teacher.strip().split()
            initials = "".join([word[0].upper() for word in words_teacher if word])
            text = f"{name} - {initials} - {room}"
        else:
            text = f"{name} - {room}"

    original_lines = text.split('\n')
    wrapped_lines: list[str] = []
    
    for line in original_lines:
        if len(line) <= max_chars_per_line:
            wrapped_lines.append(line)
        else:
            wrapped = textwrap.wrap(line, width=max_chars_per_line, 
                                  break_long_words=True, break_on_hyphens=True)
            wrapped_lines.extend(wrapped)
    
    if len(wrapped_lines) > max_lines:
        wrapped_lines = wrapped_lines[:max_lines-1]
        if wrapped_lines:
            last_line = wrapped_lines[-1]
            if len(last_line) > max_chars_per_line - 3:
                wrapped_lines[-1] = last_line[:max_chars_per_line-3] + "..."
            else:
                wrapped_lines.append("...")
    
    return '\n'.join(wrapped_lines)


def add_courses(ax: Axes, courses: List[Tuple[str, str, float, str, str, str, str, List[int] | None]], hours: List[str], days: List[str], line_number: int, group_structure: Dict[int, Dict[str, Any]]) -> Axes:
    """Function that adds courses to the schedule

    Args:
        ax (_type_): matplotlib axe
        courses (list): list of courses
        hours (list): list of hours
        days (list): list of days
        line_number (int): number of lines (of groups)
        group_structure (dict): structure of groups

    Returns:
        _type_: matplotlib axe with added courses
    """
    for course in courses:
        day, start_hour, duration, name, teacher, room, course_type, course_group = course
        color = get_color(course_type)
        i = hours.index(start_hour)
        j = days.index(day)

        final_text = wrap_text_to_fit_rectangle(course_type, name, teacher, room, duration, line_number)

        
        # Show courses
        if course_type == "CM":
            
            ax.add_patch(patches.Rectangle((i, j*line_number), duration, line_number, 
                                         facecolor=color, edgecolor="black", linewidth=0.5))
            ax.text(i + duration/2, j*line_number + line_number/2, final_text, 
                   ha="center", va="center", fontsize=FONT_SIZE)

        elif course_type == "TD":
            if course_group and len(course_group) == 1:
                g = course_group[0]
                idx = j*line_number + g

                ax.add_patch(patches.Rectangle((i, idx), duration, 1,
                                             facecolor=color, edgecolor="black", linewidth=0.5))
                ax.text(i + duration/2, idx + 0.5, final_text, 
                       ha="center", va="center", fontsize=FONT_SIZE)
        
        elif course_type == "TP":
            if course_group and len(course_group) == 1:
                # TP for the entire group
                g = course_group[0]
                idx = j*line_number + g
                
                ax.add_patch(patches.Rectangle((i, idx), duration, 1, 
                                             facecolor=color, edgecolor="black", linewidth=0.5))
                ax.text(i + duration/2, idx + 0.5, final_text, 
                       ha="center", va="center", fontsize=FONT_SIZE)
                       
            elif course_group and len(course_group) == 2:
                # TP for one group especially
                g, subgroup = course_group
                structure = group_structure[g]
                idx = j*line_number + g

                if structure['num_subgroups'] > 1:
                    try:
                        subgroup_index = structure['subgroup_letters'].index(subgroup)
                        height_subgroup = 1.0 / structure['num_subgroups']
                        y_position = idx + (subgroup_index * height_subgroup)
                        
                        subgroup_font_size = max(4, FONT_SIZE - 1)

                        ax.add_patch(patches.Rectangle((i, y_position), duration, height_subgroup, 
                                                     facecolor=color, edgecolor="black", linewidth=0.5))
                        y_text = y_position + height_subgroup/2
                        ax.text(i + duration/2, y_text, final_text, 
                               ha="center", va="center", fontsize=subgroup_font_size)
                    except ValueError:
                        # Subgroup not found
                        
                        ax.add_patch(patches.Rectangle((i, idx), duration, 1, 
                                                     facecolor=color, edgecolor="black", linewidth=0.5))
                        ax.text(i + duration/2, idx + 0.5, final_text, 
                               ha="center", va="center", fontsize=FONT_SIZE)
                else:
                    ax.add_patch(patches.Rectangle((i, idx), duration, 1,
                                                 facecolor=color, edgecolor="black", linewidth=0.5))
                    ax.text(i + duration/2, idx + 0.5, final_text, 
                           ha="center", va="center", fontsize=FONT_SIZE)

        else:  # SAE or other
            if not course_group:
                ax.add_patch(patches.Rectangle((i, j*line_number), duration, line_number,
                                             facecolor=color, edgecolor="black", linewidth=0.5))
                ax.text(i + duration/2, j*line_number + line_number/2, final_text, 
                       ha="center", va="center", fontsize=FONT_SIZE)
            else:
                for g in course_group:
                    if isinstance(g, int):
                        idx = j*line_number + g
                        
                        ax.add_patch(patches.Rectangle((i, idx), duration, 1, 
                                                     facecolor=color, edgecolor="black", linewidth=0.5))
                        ax.text(i + duration/2, idx + 0.5, final_text, 
                               ha="center", va="center", fontsize=FONT_SIZE)
                    elif isinstance(g, (list, tuple)) and len(g) == 2:
                        groupe_index, subgroup = g
                        structure = group_structure[groupe_index]
                        idx = j*line_number + groupe_index
                        
                        if structure['num_subgroups'] > 1:
                            try:
                                subgroup_index = structure['subgroup_letters'].index(subgroup)
                                height_subgroup = 1.0 / structure['num_subgroups']
                                y_position = idx + (subgroup_index * height_subgroup)
                                
                                subgroup_font_size = max(4, FONT_SIZE - 1)
                                
                                ax.add_patch(patches.Rectangle((i, y_position), duration, height_subgroup, 
                                                             facecolor=color, edgecolor="black", linewidth=0.5))
                                y_text = y_position + height_subgroup/2
                                ax.text(i + duration/2, y_text, final_text, 
                                       ha="center", va="center", fontsize=subgroup_font_size)
                            except ValueError:
                                # Sub-group not found
                                
                                ax.add_patch(patches.Rectangle((i, idx), duration, 1, 
                                                             facecolor=color, edgecolor="black", linewidth=0.5))
                                ax.text(i + duration/2, idx + 0.5, final_text, 
                                       ha="center", va="center", fontsize=FONT_SIZE)
                        else:
                            ax.add_patch(patches.Rectangle((i, idx), duration, 1, 
                                                         facecolor=color, edgecolor="black", linewidth=0.5))
                            ax.text(i + duration/2, idx + 0.5, final_text, 
                                   ha="center", va="center", fontsize=FONT_SIZE)
    return ax

from typing import Optional

def generate_schedule(promotion: str, week: int, groups: list[str], courses: list[Any], custom_file_name: Optional[str] = None):
    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
    hours = ["08:00","08:30","09:00","09:30","10:00","10:30","11:00","11:30","12:00","12:30","13:00","13:30","14:00","14:30","15:00","15:30","16:00","16:30","17:00","17:30","18:00","18:30","19:00","19:30"]

    if not os.path.exists("Edt"):
        os.makedirs("Edt")

    ax, line_number, plt_ref, groups_structure = create_template(promotion, week, days, hours, groups)
    ax = add_courses(ax, courses, hours, days, line_number, groups_structure)

    if custom_file_name:
        file_name = f"Edt/{custom_file_name}.png"
    else:
        file_name = f"Edt/emploi_du_temps_{promotion}_S{week:02d}.png"

    plt_ref.savefig(file_name, dpi=300, bbox_inches='tight')
    plt_ref.close('all')  
    gc.collect()
    print(f"Généré : {file_name}")



config_3_sous_groupes = {
        "A2_3SG": {
            "groupes": ["G4","G4A","G4B","G4C", "G5","G5A","G5B","G5C"],  # 2 groupes avec 3 sous-groupes chacun
            "cours": [
                # LUNDI - 3 sous-groupes
                ("Lundi", "08:00", 2, "R4.11.Programmation", "Dupont A.", "R20", "CM", None),
                ("Lundi", "10:00", 2, "R4.05.Réseaux", "Martin L.", "C101", "TP", [0, 'A']),  # G4A
                ("Lundi", "10:00", 2, "R4.07.Web", "Blanc S.", "S105", "TP", [0, 'B']),  # G4B
                ("Lundi", "10:00", 2, "R4.08.Mobile", "Mobile Dev", "S106", "TP", [0, 'C']),  # G4C
                ("Lundi", "10:00", 2, "R4.09.Base", "DB Expert", "R25", "TD", [1]),  # G5 entier
                ("Lundi", "14:00", 2, "R4.12.Math", "Math Prof", "R22", "TD", [0]),  # G4 entier
                ("Lundi", "14:00", 2, "R4.13.Algo", "Algo Expert", "R23", "TP", [1, 'A']),  # G5A
                ("Lundi", "14:00", 2, "R4.14.Struct", "Struct Expert", "R24", "TP", [1, 'B']),  # G5B
                ("Lundi", "14:00", 2, "R4.15.Graph", "Graph Expert", "S201", "TP", [1, 'C']),  # G5C
                
                # MARDI - Mix de configurations
                ("Mardi", "08:00", 2, "R4.20.Théorie", "Théoricien", "Amphi", "CM", None),
                ("Mardi", "10:00", 4, "SAE.05", "", "S401", "SAE", [0]),  # Tout G4
                ("Mardi", "10:00", 4, "SAE.06", "", "S402", "SAE", [1]),  # Tout G5
                ("Mardi", "16:00", 2, "R4.21.Spé1", "Spé Expert 1", "L401", "TP", [0, 'A']),
                ("Mardi", "16:00", 2, "R4.22.Spé2", "Spé Expert 2", "L402", "TP", [0, 'B']),
                ("Mardi", "16:00", 2, "R4.23.Spé3", "Spé Expert 3", "L403", "TP", [0, 'C']),
            ]
        }
    }
    
    
for promo, config in config_3_sous_groupes.items():
    generate_schedule(promo, 1, config["groupes"], config["cours"])
    