from pydreamplet import G, Vector, Path, Circle
import xml.etree.ElementTree as ET
import os
import random

SVG_DIR = os.path.dirname(os.path.abspath(__file__))

scenery_path = os.path.join(SVG_DIR, "scenery")
scenery_files = []
for file in os.listdir(scenery_path):
    if file.endswith("restyled.svg"):
        scenery_files.append(os.path.join(scenery_path, file))

def make_signal_group(train_id):
    signal_group = G(id=f"train_{train_id}_signal_group", class_name="train_signal")
    background = Path(d="m 228,76.8 c 0,9.941 -8.059,18 -18,18 -9.941,-0 -18,-8.059 -18,-18 V 30 c 0,-9.941 8.059,-18 18,-18 9.941,0 18,8.059 18,18z", style="stroke: #000000; stroke-width: 14.4;")
    signal_group.append(background)
    red_light = Circle(cx=210, cy=30, r=18, style="fill: #ff0000;", id=f"train_{train_id}_red_light", class_name="red_light")
    signal_group.append(red_light)
    green_light = Circle(cx=210, cy=76.8, r=18, style="fill: #00ff00;", id=f"train_{train_id}_green_light", class_name="green_light")
    signal_group.append(green_light)
    return signal_group

def get_train_svg(train_id, cell_size=25, scale=240):
    svg_file = os.path.join(SVG_DIR, "trains_wide", f"train-{train_id}_restyled.svg")
    train_group = clean_svg_group(svg_file, f"train_{train_id}_group", cell_size, scale, class_name="train")
    train_group.id = f"train_{train_id}_group"
    train_group.append(make_signal_group(train_id))
    return train_group

def clean_svg_group(svg_file, group_id, cell_size=25, scale=240, class_name=None):
    # if not os.path.exists(svg_file):
    #     raise FileNotFoundError(f"SVG file {svg_file} not found.")
    elem = ET.parse(os.path.join(SVG_DIR, svg_file)).getroot()
    for child in elem.iter():
        if child.tag.endswith("defs") or child.tag.endswith("title") or child.tag.endswith("style"):
            try:
                elem.remove(child)
            except ValueError:
                pass
    group = G(id=group_id)
    for child in elem:
        group.append(child)
    group.scale = Vector(cell_size / scale, cell_size / scale)
    if class_name:
        group.class_name = class_name
    return group

def sample_scenery_file():
    return random.choice(scenery_files)