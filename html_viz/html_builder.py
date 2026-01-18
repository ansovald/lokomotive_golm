import sys
import json
from html_viz import LandscapeBuilder
import os

RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
html_template_file = os.path.join(RESOURCE_DIR, "html_template.html")
train_widget_file = os.path.join(RESOURCE_DIR, "train_widget.html")

def generate_html(env_name, landscape, milliseconds_per_step=500):
    svg_output = landscape.svg_string()
    control_svg_output = landscape.control_svg_string()

    with open(html_template_file, "r") as f:
        html_template = f.read()

    html_output = html_template.replace("{{HEADING}}", f"Flatland SVG Animation: {env_name}")
    html_output = html_output.replace("{{INLINE_SVG}}", svg_output)
    html_output = html_output.replace("{{CONTROL_SVG}}", control_svg_output)

    train_infos = build_train_widgets(landscape)
    html_output = html_output.replace("{{TRAIN_INFOS}}", train_infos)

    html_output = html_output.replace("{{TRAIN_DATA}}", json.dumps(landscape.display_states, indent=4))
    
    train_defs = ""
    path_defs = ""
    for train_id in landscape.trains.keys():
        train_defs += f"const train_{train_id}_rotation = document.getElementById('train_{train_id}_rotation_group');\n"
        train_defs += f"const train_{train_id}_animate = document.getElementById('train_{train_id}_animate');\n"
        train_defs += f"const train_{train_id}_opacity_animation = document.getElementById('train_{train_id}_opacity_animation');\n"
        path_defs  += f"const path_{train_id} = data[\"{train_id}\"];\n"
        train_defs += f"const train_{train_id}_status = document.getElementById('train_{train_id}_status');\n"
        train_defs += f"const train_{train_id}_action = document.getElementById('train_{train_id}_action');\n"
        train_defs += f"const train_{train_id}_pos = document.getElementById('train_{train_id}_pos');\n"
        # train_defs += f"const train_{train_id}_action_label = document.getElementById('train_{train_id}_action_label');\n"
        # train_defs += f"const train_{train_id}_position_label = document.getElementById('train_{train_id}_position_label');\n"
        # train_defs += f"const train_{train_id}_signal_group = document.getElementById('train_{train_id}_signal_group');\n"
        
    html_output = html_output.replace("{{TRAIN_DEFS}}", train_defs)
    html_output = html_output.replace("{{PATH_DEFS}}", path_defs)

    html_output = html_output.replace("{{MAX_STEP}}", str(landscape.time_frame))

    html_output = html_output.replace("{{MILLISECONDS_PER_STEP}}", str(milliseconds_per_step))

    path_step_code = ""
    for train_id in landscape.trains.keys():
        path_step_code += f"  const state_{train_id} = path_{train_id}[step];\n"
        path_step_code += f"  train_{train_id}_animate.setAttribute('dur', `${{ms_per_step}}ms`);\n"
        path_step_code += f"  train_{train_id}_animate.setAttribute('keyPoints', `${{state_{train_id}.keyPoints}}`);\n"
        path_step_code += f"  train_{train_id}_animate.setAttribute('path', `${{state_{train_id}.motionPath}}`);\n"
        path_step_code += f"  train_{train_id}_animate.beginElement();\n"
        # # debugging:
        # path_step_code += f"  train_{train_id}_rotation.setAttribute('opacity', '1');\n"
        # path_step_code += f"  train_{train_id}_opacity_animation.setAttribute('dur', '{milliseconds_per_step}ms');\n"
        # set 'ms_per_step' to match the animation duration
        path_step_code += f"  train_{train_id}_opacity_animation.setAttribute('dur', `${{ms_per_step}}ms`);\n"
        # path_step_code += f"  train_{train_id}_opacity_animation.setAttribute('values', `${{state_{train_id}.opacity}}`);\n"
        path_step_code += f"  train_{train_id}_opacity_animation.setAttribute('from', state_{train_id}.opacity[0]);\n"
        path_step_code += f"  train_{train_id}_opacity_animation.setAttribute('to', state_{train_id}.opacity[1]);\n"
        path_step_code += f"  train_{train_id}_status.textContent = `Status: ${{state_{train_id}.status}}`;\n"
        path_step_code += f"  train_{train_id}_action.textContent = ` Action: ${{state_{train_id}.action}}`;\n"
        path_step_code += f"  train_{train_id}_pos.textContent = ` Position: [${{state_{train_id}.position}}]`;\n"
        # path_step_code += f"  train_{train_id}_action_label.textContent = `${{state_{train_id}.action}}`;\n"
        # path_step_code += f"  train_{train_id}_position_label.textContent = `${{state_{train_id}.position}}`;\n"
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

def build_train_widgets(landscape: LandscapeBuilder) -> str:
    widgets = ""
    with open(train_widget_file, "r") as f:
        widget_template = f.read()
    for train_id in landscape.trains.keys():
        widget_html = widget_template.replace("{{TRAIN_ID}}", str(train_id))
        widget_html = widget_html.replace("{{SPEED}}", str(landscape.trains[train_id]['speed']))
        widgets += widget_html + "\n"
    return widgets