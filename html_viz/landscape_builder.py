from __future__ import annotations
import xml.etree.ElementTree as ET
from pydreamplet import SVG, G, Vector, Rect, Text, Path, Circle
import os
import random
import json
from dataclasses import dataclass
from html_viz.svg_files.control_buttons import build_buttons
from html_viz.svg_files.get_svg import clean_svg_group, sample_scenery_file, get_train_svg, get_train_color
from html_viz.train_paths import TrainPath

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s -- %(name)s: %(message)s', filename='build_svg.log', filemode='w')
logger = logging.getLogger(__name__)

STANDARD_STYLE = "standard_style_dynamic.css"

def load_grid(grid_file):
    with open(grid_file, "r") as f:
        grid = json.load(f)
        # make keys int
        grid = {int(y): {int(x): str(track_id) for x, track_id in row.items()} for y, row in grid.items()}
    return grid

def load_trains(train_file):
    with open(train_file, "r") as f:
        trains = json.load(f)
    return trains

class LandscapeBuilder:
    def __init__(self, base_dir, time_frame=None, cell_size=25, style_file=STANDARD_STYLE):
        self.base_dir = base_dir
        self.grid = load_grid(os.path.join(base_dir, "grid.json"))
        self.trains = load_trains(os.path.join(base_dir, "train_info.json"))
        self.time_frame = time_frame
        self.cell_size = cell_size        
        self.prepare_dynamic_styles(os.path.join(os.path.dirname(os.path.abspath(__file__)), style_file))
        self.compute_dimensions(self.grid)
        self.canvas = self.build_landscape()
        self.train_path_group = G(id="train_paths", class_name="train_paths")
        self.canvas.append(self.train_path_group)
        self.save_svg()
        self.train_paths = self.prepare_train_paths()
        self.display_states = {}
        self.legend = []
        self.place_trains()
        self.align_legend()
        self.build_controls()

    def prepare_dynamic_styles(self, style_path):
        # pre-computes all elements that depend on cell size
        self.font_size = self.cell_size / 2
        self.font_size_hover = f"{1.2 * self.font_size}px"
        self.train_path_width = self.cell_size / 15
        self.train_path_width_hover = f"{2 * self.train_path_width}px"

        # open style_path and replace font-size placeholders
        with open(style_path, "r") as f:
            style_content = f.read()
        style_content = style_content.replace("{{HOVER_FONT_SIZE}}", f"{self.font_size_hover}")
        style_content = style_content.replace("{{TRAIN_PATH_WIDTH_HOVER}}", f"{self.train_path_width_hover}")

        # generate train fill colors
        train_fill_colors = ""
        train_fill_template = ".train-fill-TRAIN_ID{fill: TRAIN_COLOR;}"
        for train_id in self.trains.keys():
            train_color = get_train_color(train_id)
            train_fill_colors += train_fill_template.replace("TRAIN_ID", str(train_id)).replace("TRAIN_COLOR", train_color) + "\n"
        style_content = style_content.replace("{{TRAIN_FILL_COLORS}}", train_fill_colors)

        self.standard_style = style_content


        train_hover_style = ""
        train_hover_template = f"""svg:has(#train_TRAIN_ID_main:hover) #train_TRAIN_ID_path {{
  stroke-width: {self.train_path_width_hover};
  transition: 0.2s;
}}"""
        for train_id in self.trains.keys():
            train_hover_style += train_hover_template.replace("TRAIN_ID", str(train_id)) + "\n"
        self.standard_style = self.standard_style.replace("{{TRAIN_HOVER_STYLE}}", train_hover_style)

    def save_svg(self, output_filename=None):
        if not output_filename:
            output_filename = os.path.join(self.base_dir, "landscape.svg")
        with open(output_filename, "w") as f:
            f.write(self.canvas.to_string())
    
    def svg_string(self):
        return self.canvas.to_string()

    def compute_dimensions(self, grid):
        max_x = 0
        max_y = 0
        for y in grid:
            if y + 1 > max_y:
                max_y = y + 1
            for x in grid[y]:
                if x + 1 > max_x:
                    max_x = x + 1
        self.grid_width = max_x
        self.grid_height = max_y
        
        self.legend_base_size = 3
        # each legend element is 3 cells high
        self.legend_columns = 1
        if len(self.trains) * self.legend_base_size > self.grid_height:
            self.legend_columns = (len(self.trains) * self.legend_base_size) // self.grid_height
        self.legend_width = self.legend_columns * self.legend_base_size

        self.buttons_width = 6
        self.width = self.grid_width + 2 + self.legend_width
        self.slider_x = 1
        if self.width < 12:
            self.control_height = 3
            self.buttons_x = (self.width - self.buttons_width) / 2
            self.buttons_y = self.grid_height + 2
            self.slider_y = self.buttons_y + 1
            self.slider_width = self.width - 2
        else:
            # slider and buttons on one row
            self.control_height = 2
            self.buttons_x = self.width - 7
            self.buttons_y = self.grid_height + 3
            self.slider_y = self.buttons_y - 1
            self.slider_width = self.width - 9
        self.height = self.grid_height + 2 + self.control_height

    def get_abs_coord(self, coord, grid_offset=True):
        offset = 1 if grid_offset else 0
        # convert coordinates to absolute svg coordinates. If grid_offset, add margin for grid labels
        return (coord + offset) * self.cell_size
        
    def get_abs_vector(self, x, y, grid_offset=True):
        # convert coordinates to absolute svg coordinates. If grid=True, add margin for grid labels
        offset = 1 if grid_offset else 0
        # convert grid coords to absolute svg coords, allowing for 1 cell margin
        abs_x = (x + offset) * self.cell_size
        abs_y = (y + offset) * self.cell_size
        return Vector(abs_x, abs_y)
    
    def cell_label(self, x, y, text):
        label = Text(text)
        label.font_family = "monospace"
        label.font_size = self.font_size * 0.8
        label.fill = "#000000"
        # label.stroke = "#ffffff"
        label.font_weight = 700
        label.stroke_width = self.cell_size * .02
        label.pos = self.get_abs_vector(x + .5, y +.5)
        label.text_anchor = "middle"
        label.dominant_baseline = "central"
        return label

    def build_landscape(self):
        canvas = SVG(self.width * self.cell_size, self.height * self.cell_size)
        style_element = ET.Element("style")
        style_element.text = self.standard_style
        canvas.append(style_element)
        # set background color
        canvas.append(Rect(pos=self.get_abs_vector(0,0), width=self.grid_width * self.cell_size, height=self.grid_height * self.cell_size, class_name="background"))

        landscape = G(id="landscape", class_name="landscape")
        canvas.append(landscape)

        # label rows and columns
        for y in range(self.grid_height):
            label_group = G(id=f"row_label_{y}", class_name="row_label")
            # add a rect covering the whole row as first child for easier selection
            label_background = Rect(
                pos=self.get_abs_vector(-1, y, grid_offset=True),
                width=(self.grid_width + 2) * self.cell_size,
                height=self.cell_size,
                fill="#000000",
                fill_opacity=0.0,
                id=f"row_label_{y}_background"
            )
            label_group.append(label_background)
            label_left = self.cell_label(-1, y, str(y))
            label_group.append(label_left)
            label_right = self.cell_label(self.grid_width, y, str(y))
            label_group.append(label_right)
            landscape.append(label_group)
        for x in range(self.grid_width):
            label_group = G(id=f"col_label_{x}", class_name="col_label")
            # add a rect covering the whole column as first child for easier selection
            label_background = Rect(
                pos=self.get_abs_vector(x, -1, grid_offset=True),
                width=self.cell_size,
                height=(self.grid_height + 2) * self.cell_size,
                fill="#000000",
                fill_opacity=0.0,
                id=f"col_label_{x}_background"
            )
            label_group.append(label_background)
            top_label = self.cell_label(x, -1, str(x))
            label_group.append(top_label)
            bottom_label = self.cell_label(x, self.grid_height, str(x))
            label_group.append(bottom_label)
            landscape.append(label_group)

        for y in self.grid:
            for x in self.grid[y]:
                track_id = self.grid.get(y, {}).get(x, None)
                if track_id is None:
                    continue
                elif track_id == "0":
                    svg_path = sample_scenery_file()
                else:
                    svg_path = f"{track_id}_restyled.svg"
                group_id = f"cell_{x}_{y}_t{track_id}"
                cell_group = G(id=group_id, class_name="cell")
                cell_image = clean_svg_group(svg_path, group_id, self.cell_size, scale=240)
                cell_pos = self.get_abs_vector(x, y, grid_offset=True)
                cell_image.pos = cell_pos
                cell_group.append(cell_image)
                # add invisible rect to capture hover events with stroke to show grid
                hover_rect = Rect(
                    pos=cell_pos,
                    width=self.cell_size,
                    height=self.cell_size,
                    stroke="#000000",
                    stroke_width=1,
                    stroke_opacity=0.05,
                    fill="#000000",
                    fill_opacity=0.0,
                    id=f"cell_{x}_{y}_hover_rect"
                )
                cell_group.append(hover_rect)

                coord_label = self.cell_label(x, y, f"{x},{y}")
                coord_label.opacity = 0.0
                cell_group.append(coord_label)
                landscape.append(cell_group)
        return canvas
    
    def prepare_train_paths(self):
        """
        Generates a default path element for each train to be populated later.
        Added to self.train_path_group so that it appears behind trains.
        """
        train_paths = {}
        for train_id in self.trains.keys():
            path_element = Path(
                d="",
                stroke=get_train_color(train_id),
                stroke_width=self.train_path_width,
                stroke_dasharray=f"{self.cell_size * 0.2},{self.cell_size * 0.2}",
                stroke_linecap="round",
                fill="none",
                id=f"train_{train_id}_path",
                class_name=f"train_{train_id}_path",
                opacity=0.9
                )
            self.train_path_group.append(path_element)
            train_paths[train_id] = path_element
        return train_paths

    def place_trains(self):
        """
        Calls TrainPath to build paths for each train and prepares their respective SVG elements.
        """
        for i, train_id in enumerate(self.trains):
            logger.info(f"Placing train {train_id}")
            train_color = get_train_color(train_id)
            # container to hold all elements of the train for easy highlighting
            train_group = G(id=f"train_{train_id}_main", class_name="train")
            train_info = self.trains[train_id]
            # build train path
            print(f"INFO -- TRAIN_PATHS: Initializing TrainPath for train {train_id} with time frame {self.time_frame}")
            train_path_builder = TrainPath(train_id, train_info, self.time_frame)
            path_string = train_path_builder.get_path_string(cell_size=self.cell_size)
            # self.display_states[train_id] = train_path_builder.get_display_states(cell_size=self.cell_size)
            self.display_states[train_id] = train_path_builder.get_display_states()
            self.train_paths[train_id].d = path_string
            
            # Create train legend
            train_group.append(self.create_train_legend(train_id, speed=train_info.get("speed", 0)))

            # Prepare train SVG
            train_render_group = get_train_svg(train_id, self.cell_size, scale=240)

            # Train rotation group normalizes position so that mid point is at (0,0) for easier rotation (set in JavaScript)
            train_rotation_group = G(id=f"train_{train_id}_rotation_group", class_name="train_rotation")

            # add a rect behind the train as first child for easier selection
            background_rect = Rect(
                pos=Vector(0, 0),
                rx=self.cell_size/5, ry=self.cell_size/5,
                width=self.cell_size,
                height=self.cell_size,
                stroke=train_color,
                stroke_width=self.cell_size / 15,
                stroke_opacity=0.0,
                fill=train_color,
                fill_opacity=0.0,
                id=f"train_{train_id}_background",
                class_name="train_background"
            )
            train_rotation_group.append(background_rect)

            train_rotation_group.append(train_render_group)
            train_rotation_group.pos = Vector(-self.cell_size/2, -self.cell_size/2)
            train_rotation_group.__setattr__("transform-origin", "center")
            # TODO: set initial rotation based on first movement direction?
            train_rotation_group.angle = 90

            transformed_train_group = G(id=f"train_{train_id}_transformed_group", class_name="train_transformed")
            transformed_train_group.append(train_rotation_group)
            # Make animation group, takes care of positioning and rotation during animation
            train_animation_group = G(id=f"train_{train_id}_animation_group", class_name="train_animation")

            path_animation = ET.Element("animateMotion", {
                "id": f"train_{train_id}_animate",
                "dur": "1s",    # to be set in JavaScript
                # "repeatCount": "1",
                "repeatCount": "indefinite", # for debugging
                "fill": "freeze",
                "rotate": "auto",
                "path": "",
                "keyPoints": "0;1",
                "keyTimes": "0;1",
                "calcMode": "linear"
            })
            path_animation.set("path", path_string)
            train_animation_group.append(path_animation)
            train_animation_group.append(transformed_train_group)

            opacity_animation = ET.Element("animate", {
                "id": f"train_{train_id}_opacity_animation",
                "attributeName": "opacity",
                "dur": "1s",    # to be set in JavaScript
                "repeatCount": "1",
                # "repeatCount": "indefinite", # for debugging
                "fill": "freeze",
                "from": "1",
                "to": "1",
            })
            train_animation_group.append(opacity_animation)

            train_group.append(train_animation_group)

            self.canvas.append(train_group)

    def create_train_legend(self, train_id, speed=0):
        train_legend = G(id=f"train_{train_id}_legend", class_name="train_legend")
        self.legend.append(train_legend)
        lines = 4
        margin = self.cell_size * 0.1
        width = self.cell_size * 3 - margin * 2
        text_x = width / 2
        line_height = self.cell_size * 2.5 / lines
        # baseline of first text line
        text_y = margin + line_height * 0.5
        # add rect behind the label as first child for easier selection
        background_rect = Rect(
            pos=Vector(0.5, 0.5),
            width=width,
            height=width,
            rx=self.cell_size/5, ry=self.cell_size/5,
            fill=get_train_color(train_id),
            fill_opacity=0.2,
            id=f"train_{train_id}_legend_background",
            class_name="train_legend_background"
        )
        train_legend.append(background_rect)
        train_label = Text(
            initial_text=f"Train {train_id}",
            pos=Vector(text_x, text_y),
            font_family="sans-serif",
            font_size=self.font_size,
            font_weight=700,
            fill="#000000",
            dominant_baseline="central",
            text_anchor="middle",
            id=f"train_{train_id}_label"
            )
        # second label beneath first to display action state
        action_label = Text(
            initial_text="wait",
            pos=Vector(text_x, text_y + line_height),
            font_family="sans-serif",
            font_size=self.font_size * 0.7,
            font_weight=700,
            fill="#000000",
            dominant_baseline="central",
            text_anchor="middle",
            id=f"train_{train_id}_action_label"
            )
        # third label: position
        position_label = Text(
            initial_text="(0,0)",
            pos=Vector(text_x, text_y + line_height * 2),
            font_family="monospace",
            font_size=self.font_size * 0.7,
            font_weight=700,
            fill="#000000",
            dominant_baseline="central",
            text_anchor="middle",
            id=f"train_{train_id}_position_label"
            )
        # fourth label: speed
        speed_label = Text(
            initial_text=f"speed: {speed}",
            pos=Vector(text_x, text_y + line_height * 3),
            font_family="monospace",
            font_size=self.font_size * 0.7,
            font_weight=700,
            fill="#000000",
            dominant_baseline="central",
            text_anchor="middle",
            id=f"train_{train_id}_speed_label"
        )
        train_legend.append(position_label)
        train_legend.append(action_label)
        train_legend.append(train_label)
        train_legend.append(speed_label)
        return train_legend
    
    def align_legend(self):
        # place legend according to self.legend_columns, centered vertically
        elements_per_column = (len(self.trains) + self.legend_columns - 1) // self.legend_columns
        column_height = elements_per_column * self.legend_base_size

        for i, train_legend in enumerate(self.legend):
            column = i // elements_per_column
            row = i % elements_per_column
            x = self.get_abs_coord(self.grid_width + 2 + column * self.legend_base_size, grid_offset=False)
            y = ((self.grid_height + 2 - column_height) / 2 + row * self.legend_base_size) * self.cell_size
            train_legend.pos = Vector(
                x,
                y
            )
    
    def build_controls(self):
        controls_group = build_buttons(self.cell_size)
        controls_group.pos = Vector(
            self.get_abs_coord(self.buttons_x, grid_offset=False),
            self.get_abs_coord(self.buttons_y, grid_offset=False)
        )
        self.canvas.append(controls_group)
        
        slider_group = G(id="slider_group", class_name="slider")
        self.canvas.append(slider_group)
        # make invisible rect behind slider for calculating time steps
        slider_background = Rect(
            pos=Vector(self.get_abs_coord(self.slider_x + 0.5, grid_offset=False), self.get_abs_coord(self.slider_y + 1, grid_offset=False)),
            width=(self.slider_width - .5) * self.cell_size,
            height=self.cell_size,
            fill="#000000",
            fill_opacity=0.0,
            id="slider_background",
            class_name="slider_background"
        )
        slider_group.append(slider_background)
        # make a path from .5 to self.buttons_x - 1 on height control_y + .5 for time step slider
        slider_path = Path(
            d=f"M {self.get_abs_coord(self.slider_x + 0.5, grid_offset=False)},{self.get_abs_coord(self.slider_y + 1.5, grid_offset=False)} L {self.get_abs_coord(self.slider_x + self.slider_width, grid_offset=False)},{self.get_abs_coord(self.slider_y + 1.5, grid_offset=False)}",
            stroke="#000000",
            stroke_opacity=0.2,
            stroke_width=self.cell_size * 0.5,
            stroke_linecap="round",
            fill="none",
            id="time_step_slider_path"
        )
        slider_group.append(slider_path)
        # make a circle with diameter cell_size as slider handle
        slider_handle = Circle(cx=self.get_abs_coord(self.slider_x + 0.5, grid_offset=False), cy=self.get_abs_coord(self.slider_y + 1.5, grid_offset=False), r=self.cell_size*.4, fill="#d8d8d8", stroke="#A4A4A4", stroke_width=self.cell_size * 0.1, id="slider_handle", class_name="slider_handle")
        slider_group.append(slider_handle)

        step_group = self.step_label()
        slider_group.append(step_group)
    
    def step_label(self):
        step_group = G(id="step_legend", class_name="step_legend")
        step_group.pos = Vector(
            self.get_abs_coord(self.slider_x + self.slider_width / 2, grid_offset=False),
            self.get_abs_coord(self.slider_y + 0.5, grid_offset=False)
        )
        # # add rect behind the label as first child for easier selection
        # background_rect = Rect(
        #     pos=Vector(0, 0),
        #     width=self.slider_width * self.cell_size,
        #     height=self.cell_size * 1,
        #     fill="#000000",
        #     fill_opacity=0.0,
        #     id="step_legend_background",
        #     class_name="step_legend_background"
        # )
        # step_group.append(background_rect)
        step_label = Text(
            initial_text="Time Step: 0",
            # pos=Vector(self.slider_x + (0.5 * self.slider_width), self.slider_y + 0.5),
            font_family="monospace",
            font_size=self.font_size,
            font_weight=700,
            fill="#000000",
            dominant_baseline="central",
            text_anchor="middle",
            id="step_label"
            )
        step_group.append(step_label)
        return step_group

def get_latest_model_dir(env_name, base_dir="env"):
    dirs = [d for d in os.listdir(base_dir) if d.startswith(env_name)]
    if not dirs:
        raise FileNotFoundError(f"No model directories found for environment {env_name} in {base_dir}.")
    dirs.sort(reverse=True)
    latest_dir = dirs[0]
    return os.path.join(base_dir, latest_dir)

if __name__ == "__main__":

    # env_name = "env_001--2_6"
    env_name = "testenv_2"
    model_dir = get_latest_model_dir(env_name)
    # print(f"Using model directory: {model_dir}")
    cell_size = 25

    landscape_builder = LandscapeBuilder(model_dir, cell_size=cell_size)
    # landscape_builder = LandscapeBuilder(env_encoding=env_encoding, cell_size=cell_size)
    landscape_builder.save_svg()

    