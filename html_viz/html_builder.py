import sys
import json
from html_viz import LandscapeBuilder
import os

RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
html_template_file = os.path.join(RESOURCE_DIR, "html_template.html")

def generate_html(env_name, landscape, milliseconds_per_step=500):
    # builder = LandscapeBuilder(base_dir, cell_size=cell_size)
    # landscape = builder.build_landscape()
    svg_output = landscape.svg_string()
    cell_size = landscape.cell_size

    with open(html_template_file, "r") as f:
        html_template = f.read()

    html_output = html_template.replace("{{HEADING}}", f"Flatland SVG Animation: {env_name}")
    html_output = html_output.replace("{{INLINE_SVG}}", svg_output)
    html_output = html_output.replace("{{TRAIN_DATA}}", json.dumps(landscape.display_states, indent=4))
    
    train_defs = ""
    path_defs = ""
    for train_id in landscape.trains.keys():
        train_defs += f"const train_{train_id}_rotation = document.getElementById('train_{train_id}_rotation_group');\n"
        train_defs += f"const train_{train_id}_animate = document.getElementById('train_{train_id}_animate');\n"
        train_defs += f"const train_{train_id}_opacity_animation = document.getElementById('train_{train_id}_opacity_animation');\n"
        path_defs  += f"const path_{train_id} = data[\"{train_id}\"];\n"
        train_defs += f"const train_{train_id}_action_label = document.getElementById('train_{train_id}_action_label');\n"
        train_defs += f"const train_{train_id}_position_label = document.getElementById('train_{train_id}_position_label');\n"
        train_defs += f"const train_{train_id}_signal_group = document.getElementById('train_{train_id}_signal_group');\n"
        
    html_output = html_output.replace("{{TRAIN_DEFS}}", train_defs)
    html_output = html_output.replace("{{PATH_DEFS}}", path_defs)

    html_output = html_output.replace("{{MAX_STEP}}", str(landscape.time_frame))

    html_output = html_output.replace("{{MILLISECONDS_PER_STEP}}", str(milliseconds_per_step))

    path_step_code = ""
    for train_id in landscape.trains.keys():
        path_step_code += f"  const state_{train_id} = path_{train_id}[step];\n"
        path_step_code += f"  train_{train_id}_animate.setAttribute('dur', '{milliseconds_per_step}ms');\n"
        path_step_code += f"  train_{train_id}_animate.setAttribute('keyPoints', `${{state_{train_id}.keyPoints}}`);\n"
        path_step_code += f"  train_{train_id}_animate.setAttribute('keyTimes', `${{state_{train_id}.keyTimes}}`);\n"
        # path_step_code += f"  train_{train_id}_rotation.setAttribute('opacity', `${{state_{train_id}.opacity}}`);\n"
        path_step_code += f"  train_{train_id}_opacity_animation.setAttribute('dur', '{milliseconds_per_step}ms');\n"
        path_step_code += f"  train_{train_id}_opacity_animation.setAttribute('from', state_{train_id}.opacity[0]);\n"
        path_step_code += f"  train_{train_id}_opacity_animation.setAttribute('to', state_{train_id}.opacity[1]);\n"
        # TODO: is there a way to turn animation off if 'playing' is false?
        # path_step_code += f"  train_{train_id}_animate.setAttribute('dur', '2000ms');\n"
        # path_step_code += f"  train_{train_id}_animate.setAttribute('path', `${{state_{train_id}.motion_path}}`);\n"
        path_step_code += f"  train_{train_id}_animate.beginElement();\n"
        path_step_code += f"  train_{train_id}_action_label.textContent = `${{state_{train_id}.action}}`;\n"
        path_step_code += f"  train_{train_id}_position_label.textContent = `${{state_{train_id}.position}}`;\n"
        # add signal logic: if "", add class "hide"; if "red" add class "red"; if "green" add class "green"
        path_step_code += f"  train_{train_id}_signal_group.classList.remove('hide', 'red', 'green');\n"
        path_step_code += f"  if (state_{train_id}.signal === 'red') {{\n"
        path_step_code += f"    train_{train_id}_signal_group.classList.add('red');\n"
        path_step_code += f"  }} else if (state_{train_id}.signal === 'green') {{\n"
        path_step_code += f"    train_{train_id}_signal_group.classList.add('green');\n"
        path_step_code += f"  }} else {{\n"
        path_step_code += f"    train_{train_id}_signal_group.classList.add('hide');\n"
        path_step_code += f"  }}\n"

    html_output = html_output.replace("{{PATH_STEP}}", path_step_code)

    stop_animation_code = ""
    for train_id in landscape.trains.keys():
        stop_animation_code += f"  train_{train_id}_animate.endElement();\n"
    html_output = html_output.replace("{{STOP_ANIMATION}}", stop_animation_code)

    slider_offset = landscape.get_abs_coord(1.5, grid_offset=False)
    html_output = html_output.replace("{{SLIDER_OFFSET}}", str(slider_offset))

    return html_output