from __future__ import annotations
from dataclasses import dataclass
import logging
logger = logging.getLogger("CURVES")

# needed to calculate absolute positions
LEFT_MARGIN = 1  # in cells
TOP_MARGIN = 1   # in cells

DIR_DICT = {
    "n": 0,
    "e": 90,
    "s": 180,
    "w": 270
}

ROT_DICT = { v: k for k, v in DIR_DICT.items() }

def get_direction(coords: Point, next_coords: Point) -> str:
        if next_coords.x > coords.x:
            return "e"
        elif next_coords.x < coords.x:
            return "w"
        elif next_coords.y > coords.y:
            return "s"
        elif next_coords.y < coords.y:
            return "n"
        else:
            return None
        
def get_rotation(coords: Point, next_coords: Point) -> int:
    # print(f"Getting rotation from {coords} to {next_coords}")
    direction = get_direction(coords, next_coords)
    return DIR_DICT.get(direction, None)

@dataclass
class Point:
    x: float
    y: float

    # define addition
    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)
    
    def __neg__(self) -> Point:
        return Point(-self.x, -self.y)
    
    def __mul__(self, scalar: float) -> Point:
        return Point(self.x * scalar, self.y * scalar)
    
    def __str__(self):
        return f"Point(x={self.x}, y={self.y})"
    
    def __dict__(self):
        return {"x": self.x, "y": self.y}
    
    def make_abs(self, cell_size, grid_offset=True) -> Point:
        offset = 1 if grid_offset else 0
        return Point(
            (self.x + offset) * cell_size,
            (self.y + offset) * cell_size
        )
    
    def abs_string(self, cell_size):
        logger.info(f"Making absolute string for point {self} with cell size {cell_size}")
        abs_point = self.make_abs(cell_size)
        return f"{round(abs_point.x, 5)} {round(abs_point.y, 5)}"
    
    def rel_string(self):
        return f"{round(self.x, 5)} {round(self.y, 5)}"
    
    def from_dict(point_dict: dict) -> Point:
        if point_dict is None:
            return None
        return Point(point_dict.get("x", None), point_dict.get("y", None))

ROTATION_OFFSETS = {
    0: Point(0, -1),
    45: Point(1, -1),
    90: Point(1, 0),
    135: Point(1, 1),
    180: Point(0, 1),
    225: Point(-1, 1),
    270: Point(-1, 0),
    315: Point(-1, -1)
}

@dataclass
class CurveSegment:
    start: Point
    end: Point
    c_0: Point = None
    c_1: Point = None
    center: Point = None
    
    def __post_init__(self):
        if self.center is None:
            self.center = Point(.5, .5)
    
    def __str__(self):
        return f"CurveSegment(center={self.center}, start={self.start}, end={self.end}, c_0={self.c_0}, c_1={self.c_1})"

    def standalone_path(self, cell_size):
        # make absolute path string for svg
        start = self.start.make_abs(cell_size)
        # round all values to 5 decimal places for smaller svg files
        return f"M {round(start.x, 5)} {round(start.y, 5)} " + self.segment_path(cell_size)
    
    def segment_path(self, cell_size):
        # make path string for svg without initial M
        end = self.end.make_abs(cell_size)
        if not self.c_0:
            return f"L {end.x} {end.y} "
        c_0 = self.c_0.make_abs(cell_size)
        c_1 = self.c_1.make_abs(cell_size)
        # round all values to 5 decimal places for smaller svg files
        return f"C {round(c_0.x, 5)} {round(c_0.y, 5)} {round(c_1.x, 5)} {round(c_1.y, 5)} {round(end.x, 5)} {round(end.y, 5)} "
    
    def reverse_path(self) -> CurveSegment:
        # return a new CurveSegment that is the reverse of this one

        return CurveSegment(
            start=self.end,
            end=self.start,
            c_0=self.c_1,
            c_1=self.c_0,
            center=self.center
        )
    
    def translate(self, offset: Point) -> CurveSegment:
        # return a new CurveSegment that is translated by the given offset
        return CurveSegment(
            start=self.start + offset,
            end=self.end + offset,
            c_0=None if self.c_0 is None else self.c_0 + offset,
            c_1=None if self.c_1 is None else self.c_1 + offset,
            center=self.center + offset
        )

# OFFSETS FOR INCOMING CURVE SEGMENTS
# Assume curve segment approximates a quarter circle with radius 0.5 cell size
# Then mid point of curve is at (1 / sqrt(2)) ~= 0.70711 of radius along both axes
# since radius is 0.5 cell size, mid point offset is 0.35355
# i.e., offset from center point is (0.5 - 0.35355) = 0.14645 of cell_size along both axes
# Rest of points are calculated graphically using Inkscape:
# - offset of tangent control point is 0.09377
# - offset of control point on incoming line: 14.645,22.095
# - offset of incoming/outgoing point 14.645,35.355

# We calculate mid point from center of cell, then everything else from mid point

def incoming_curve(mid: Point, start: Point, c_0: Point=None, c_1: Point=None, center=Point(.5,.5)) -> CurveSegment:
    # mid point is relative to center
    mid = center + mid
    # everything else is relative to mid
    segment = CurveSegment(
        start=mid + start,
        end=mid,
        c_0=None if c_0 is None else mid + c_0,
        c_1=None if c_1 is None else mid + c_1,
        center=center
    )
    return segment

def outgoing_curve(mid: Point, end: Point, c_0: Point=None, c_1: Point=None, center=Point(.5,.5)) -> CurveSegment:
    # mid point is relative to center
    mid = center + mid
    # everything else is relative to mid
    segment = CurveSegment(
        start=mid,
        end=mid + end,
        c_0=None if c_0 is None else mid + c_0,
        c_1=None if c_1 is None else mid + c_1,
        center=center
    )
    return segment

CURVES = {
     (0, 90): {   # north to east
        "incoming": incoming_curve(
            mid=Point(0.14645, 0.14645),     # offset from center of cell
            start=Point(-0.14645, 0.35355),    # offset from mid point
            c_0=Point(-0.14645, 0.22095),
            c_1=Point(-0.09377, 0.09377)
        ),
        "outgoing": outgoing_curve(
            mid=Point(0.14645, 0.14645),
            end=Point(0.35355, -0.14645),
            c_0=Point(0.09377, -0.09377),
            c_1=Point(0.22095, -0.14645)
        ),
        "rotation": 45  # rotation of train at mid point
    },
    (0, 270): {  # north to west
        "incoming": incoming_curve(
            mid=Point(-0.14645, 0.14645),
            start=Point(0.14645, 0.35355),
            c_0=Point(0.14645, 0.22095),
            c_1=Point(0.09377, 0.09377)
        ),
        "outgoing": outgoing_curve(
            mid=Point(-0.14645, 0.14645),
            end=Point(-0.35355, -0.14645),
            c_0=Point(-0.09377, -0.09377),
            c_1=Point(-0.22095, -0.14645)
        ),
        "rotation": 315
    },
    (180, 90): {  # south to east
        "incoming": incoming_curve(
            mid=Point(0.14645, -0.14645),
            start=Point(-0.14645, -0.35355),
            c_0=Point(-0.14645, -0.22095),
            c_1=Point(-0.09377, -0.09377)
        ),
        "outgoing": outgoing_curve(
            mid=Point(0.14645, -0.14645),
            end=Point(0.35355, 0.14645),
            c_0=Point(0.09377, 0.09377),
            c_1=Point(0.22095, 0.14645)
        ),
        "rotation": 135
    },
    (180, 270): {  # south to west
        "incoming": incoming_curve(
            mid=Point(-0.14645, -0.14645),
            start=Point(0.14645, -0.35355),
            c_0=Point(0.14645, -0.22095),
            c_1=Point(0.09377, -0.09377)
        ),
        "outgoing": outgoing_curve(
            mid=Point(-0.14645, -0.14645),
            end=Point(-0.35355, 0.14645),
            c_0=Point(-0.09377, 0.09377),
            c_1=Point(-0.22095, 0.14645)
        ),
        "rotation": 225
    }
}
# add straight paths
CURVES[(0, 0)] = {
    "incoming": CurveSegment(
        start=Point(.5, 1),
        end=Point(.5, .5)
    ),
    "outgoing": CurveSegment(
        start=Point(.5, .5),
        end=Point(.5, 0)
    ),
    "rotation": 0
}
CURVES[(90, 90)] = {
    "incoming": CurveSegment(
        start=Point(0, .5),
        end=Point(.5, .5)
    ),
    "outgoing": CurveSegment(
        start=Point(.5, .5),
        end=Point(1, .5)
    ),
    "rotation": 90
}

# add reverse curves for each entry
for (start_dir, end_dir), segments in list(CURVES.items()):
    if start_dir == end_dir:
        reverse_dir = start_dir + 180 % 360
        CURVES[(reverse_dir, reverse_dir)] = {
            "incoming": segments["outgoing"].reverse_path(),
            "outgoing": segments["incoming"].reverse_path(),
            "rotation": reverse_dir
        }
    else:
        rev_start_dir = (start_dir + 180) % 360
        rev_end_dir = (end_dir + 180) % 360
        rev_rotation = (segments["rotation"] + 180) % 360   
        CURVES[(rev_end_dir, rev_start_dir)] = {
            "incoming": segments["outgoing"].reverse_path(),
            "outgoing": segments["incoming"].reverse_path(),
            "rotation": rev_rotation
        }

def get_wait_path(rotation: int):
    offset = ROTATION_OFFSETS[rotation] * 0.0001
    start = Point(0.5, 0.5)
    end = start + offset
    return CurveSegment(
        start=start,
        end=end
    )
