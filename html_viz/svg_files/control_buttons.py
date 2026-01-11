from pydreamplet import SVG, Rect, Path, Vector, G
import xml.etree.ElementTree as ET

play_button = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
  <rect x="2" y="2" rx="2" ry="2" width="20" height="20" fill="#000000" fill-opacity="0.2" stroke="#000000" stroke-width="1" stroke-opacity="0"/>
  <path fill-rule="evenodd" d="M8.6 5.2A1 1 0 0 0 7 6v12a1 1 0 0 0 1.6.8l8-6a1 1 0 0 0 0-1.6l-8-6Z" clip-rule="evenodd" fill="#000000" fill-opacity="0.4"/>
</svg>"""
pause_button = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
  <rect x="2" y="2" rx="2" ry="2" width="20" height="20" fill="#000000" fill-opacity="0.2" stroke="#000000" stroke-width="1" stroke-opacity="0"/>
  <path fill-rule="evenodd" d="M8 5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H8Zm7 0a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-1Z" clip-rule="evenodd" fill="#000000" fill-opacity="0.4"/>
</svg>"""
forward_button = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
  <rect x="2" y="2" rx="2" ry="2" width="20" height="20" fill="#000000" fill-opacity="0.2" stroke="#000000" stroke-width="1" stroke-opacity="0"/>
  <path fill-rule="evenodd" d="M17 6a1 1 0 1 0-2 0v4L8.6 5.2A1 1 0 0 0 7 6v12a1 1 0 0 0 1.6.8L15 14v4a1 1 0 1 0 2 0V6Z" clip-rule="evenodd" fill="#000000" fill-opacity="0.4"/>
</svg>"""
backward_button = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 24 24">
  <rect x="2" y="2" rx="2" ry="2" width="20" height="20" fill="#000000" fill-opacity="0.2" stroke="#000000" stroke-width="1" stroke-opacity="0"/>
  <path fill-rule="evenodd" d="M7 6a1 1 0 0 1 2 0v4l6.4-4.8A1 1 0 0 1 17 6v12a1 1 0 0 1-1.6.8L9 14v4a1 1 0 1 1-2 0V6Z" clip-rule="evenodd" fill="#000000" fill-opacity="0.4"/>
</svg>"""
first_button = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
  <rect x="2" y="2" rx="2" ry="2" width="20" height="20" fill="#000000" fill-opacity="0.2"/>
  <path stroke="#000000" stroke-opacity="0.4" fill="none" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m17 16-4-4 4-4m-6 8-4-4 4-4"/>
</svg>"""
last_button = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
  <rect x="2" y="2" rx="2" ry="2" width="20" height="20" fill="#000000" fill-opacity="0.2" stroke="#000000" stroke-width="1" stroke-opacity="0"/>
  <path stroke="#000000" stroke-opacity="0.4" fill="none" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m7 16 4-4-4-4m6 8 4-4-4-4"/>
</svg>"""

def build_button(svg_string: str, transform: Vector, id: str, class_name: str) -> G:
    button_svg = ET.fromstring(svg_string)
    button_group = G(id=id, class_name=class_name)
    button_group.append(button_svg)
    button_group.scale = transform
    return button_group

def build_buttons(cell_size: int = 24) -> G:
    control_group = G(id="control_buttons", class_name="control buttons")
    transform_vector = Vector(cell_size / 24, cell_size / 24)
    for button in ["first_button", "backward_button", "pause_button", "play_button", "forward_button", "last_button"]:
        svg_string = globals()[button]
        button_id = button
        class_name = button.replace("_", " ")
        button_group = build_button(svg_string, transform_vector, button_id, class_name)
        index = ["first_button", "backward_button", "pause_button", "play_button", "forward_button", "last_button"].index(button)
        button_group.pos = Vector(cell_size * index, 0)
        control_group.append(button_group)
    return control_group