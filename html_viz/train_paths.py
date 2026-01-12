from __future__ import annotations
from html_viz.curves import CURVES, Point, CurveSegment, ROTATION_OFFSETS
from html_viz.svg_files.get_svg import get_train_color
import logging
from dataclasses import dataclass
import json

logger = logging.getLogger("TRAIN_PATHS")
# logger.setLevel(logging.INFO)

# handler = logging.FileHandler("train_paths.log", mode="w")
# formatter = logging.Formatter("%(levelname)s -- %(name)s: %(message)s")
# handler.setFormatter(formatter)

# logger.addHandler(handler)
# logger.propagate = False

# rotation in degrees for each direction
dir_dict = {
    "n": 0,
    "e": 90,
    "s": 180,
    "w": 270
}

rot_dict = {v: k for k, v in dir_dict.items()}

@dataclass
class NewTrainState:
    time_step: int
    coords: Point = None
    distance_traveled: int = None
    signal: str = None
    # rotation is the incoming rotation
    rotation: int = None
    outgoing_rotation: int = None
    action: str = None
    status: str = None
    display: bool = False
    first_display: bool = False
    arrival: bool = False
    # last_display: bool = False
    incoming_segment: CurveSegment = None
    outgoing_segment: CurveSegment = None
    speed: int = None
    _time_frame: list[int] = None
    _prior_state: NewTrainState = None
    _prior_action_state: NewTrainState = None
    _next_state: NewTrainState = None
    _next_action_state: NewTrainState = None
    key_points: list[float] = None
    relative_key_points: list[float] = None

    def __dict__(self):
        return {
            "time_step": self.time_step,
            "coords": {"x": self.coords.x, "y": self.coords.y},
            "distance_traveled": self.distance_traveled,
            "rotation": self.rotation,
            "action": self.action,
            "speed": self.speed,
            "time_frame": self.time_frame,
            "display": self.display,
            "first_display": self.first_display,
            "arrival": self.arrival,
            "incoming_segment": self.incoming_segment.__str__() if self.incoming_segment else None,
            "incoming_segment_path": self.incoming_segment.segment_path(cell_size=100) if self.incoming_segment else None,
            "outgoing_segment": self.outgoing_segment.__str__() if self.outgoing_segment else None,
            "outgoing_segment_path": self.outgoing_segment.segment_path(cell_size=100) if self.outgoing_segment else None
        }
    
    @property
    def time_frame(self):
        return self._time_frame
    @time_frame.setter
    def time_frame(self, value):
        self._time_frame = value
        if self.action and self.action == 'wait':
            self.relative_key_points = [0.999, 1.0]
        self.relative_key_points = [0.0]
        if self._time_frame and len(self._time_frame) > 1:
            frame_len = len(self._time_frame)
            self.relative_key_points.extend([round(i / frame_len, 3) for i in range(1, frame_len)])
        self.relative_key_points.append(1.0)
        logger.info(f"Generated relative_key_points for NewTrainState at time step {self.time_step}: {self.relative_key_points}")

    def last_time_step(self):
        return self.time_frame[-1] if self.time_frame else self.time_step

    @property
    def x(self):
        return self.coords.x

    @property
    def y(self):
        return self.coords.y
    
    @property
    def prior_state(self):
        return self._prior_state
    
    @prior_state.setter
    def prior_state(self, value):
        self._prior_state = value
        logger.info(f"Setting prior_state at {self.time_step}: {value} for current state: {self}")
        if value.coords != self.coords:
            self.distance_traveled = value.distance_traveled + 1
        else:
            self.distance_traveled = value.distance_traveled
        if not value.next_state == self:
            value.next_state = self
    
    @property
    def next_state(self):
        return self._next_state
    
    @next_state.setter
    def next_state(self, value):
        logger.info(f"Setting next_state at {self.time_step}: {value} for current state: {self}")
        self._next_state = value
        if not value.prior_state == self:
            value.prior_state = self

    @property
    def prior_action_state(self):
        return self._prior_action_state
    
    @prior_action_state.setter
    def prior_action_state(self, value):
        logger.info(f"Setting prior_action_state at {self.time_step}: {value} for current state: {self}")
        self._prior_action_state = value
        if self.action and self.action != 'wait' and not value.next_action_state == self and not value.time_step == -1:
            value.outgoing_rotation = self.rotation
            logger.info(f"\tset outgoing_rotation of action state {value.time_step} to {self.rotation}")
            value.next_action_state = self

    @property
    def next_action_state(self):
        return self._next_action_state
    
    @next_action_state.setter
    def next_action_state(self, value):
        logger.info(f"Setting next_action_state at {self.time_step}:  {value} for current state: {self}")
        self._next_action_state = value
        if self.outgoing_rotation != value.rotation:
            self.outgoing_rotation = value.rotation
        logger.info(f"\tset outgoing_rotation of current state {self.time_step} to {value.rotation}")

    
    def from_step_dict(time_step: int, step_dict: dict, speed: int, time_frame_len=None) -> NewTrainState:
        logger.info(f"Creating NewTrainState for time step {time_step} from step_dict: {step_dict}")
        state_dict = step_dict.get("state", step_dict) # in case of initial/end state without 'state' key
        coords = Point.from_dict(state_dict.get("position", None))
        action = step_dict.get("action", None)
        status = step_dict.get("status", None)
        direction = state_dict.get("direction", None)
        rotation = dir_dict.get(direction, None)
        train_state = NewTrainState(time_step=int(time_step), coords=coords, action=action, status=status, rotation=rotation, speed=speed)
        if action and action != "wait":
            time_step_int = int(time_step)
            if not time_frame_len:
                time_frame_len = speed
            time_frame = list(range(time_step_int, time_step_int + time_frame_len))
            logger.info(f"\tAction is '{action}', setting time_frame to {time_frame}")
        else:
            time_frame = [int(time_step)]
        train_state.time_frame = time_frame
        return train_state
    
    def build_segments(self):
        if self.action is None and not self.arrival:
            logger.warning(f"self.action: None")
            logger.info(f"\taction of current state is None, returning without building segments.")
            return
        logger.info(f"\n\nBuilding segments for NewTrainState at time {self.time_step}: {self}")
        current_rotation = self.rotation
        logger.info(f"Current rotation: {current_rotation}; prior action state: {self.prior_action_state}; next action state: {self.next_action_state}")
        out_rotation = self.outgoing_rotation if self.outgoing_rotation is not None else current_rotation
        next_action_state = self.next_action_state
        logger.info(f"Next action state at time {self.time_step}: {next_action_state}")
        logger.info(f"time step {self.time_step}, building segments for action: {self.action}, current rotation: {current_rotation}, out rotation: {out_rotation}")
        curve = CURVES[(current_rotation, out_rotation)]
        logger.info(f"Display rotation set to: {curve['rotation']}")
        logger.info(f"self.coords: {self.coords}")
        self.incoming_segment = curve['incoming'].translate(self.coords)
        self.outgoing_segment = curve['outgoing'].translate(self.coords)
        logger.info(f"Built incoming segment: {self.incoming_segment}:\n{self.incoming_segment.segment_path(cell_size=50)}")
        logger.info(f"Built outgoing segment: {self.outgoing_segment}:\n{self.outgoing_segment.segment_path(cell_size=50)}")

    def calculate_key_points(self, total_distance, time_step=None):
        if not time_step:
            time_step = self.time_step
        # get position in time_frame
        index = self.time_frame.index(time_step)
        
        if total_distance == 0:
            self.key_point = 0.0
        else:
            prior_key = round(self.prior_state.distance_traveled / total_distance, 3) if self.prior_state else 0.0
            current_key = round(self.distance_traveled / total_distance, 3)
            if prior_key == current_key:
                current_key += 0.001
            self.key_points = [prior_key, current_key]
        logger.info(f"Calculated key_point for NewTrainState at time {self.time_step}: {self.key_point} (distance_traveled: {self.distance_traveled}, total_distance: {total_distance})")

@dataclass
class TrainState:
    time_step: int
    coords: Point
    signal: str = None
    rotation: int = None
    outgoing_rotation: int = None
    action: str = None
    display: bool = False
    first_display: bool = False
    arrival: bool = False
    # last_display: bool = False
    _display_rotation: int = None
    # path segment from last center to edge of cell
    incoming_segment: CurveSegment = None
    # path segment from edge of cell to its center
    outgoing_segment: CurveSegment = None
    _prior_state: TrainState = None
    _prior_action_state: TrainState = None
    _next_state: TrainState = None
    _next_action_state: TrainState = None

    def __dict__(self):
        return {
            "time_step": self.time_step,
            "coords": {"x": self.coords.x, "y": self.coords.y},
            "rotation": self.rotation,
            "outgoing_rotation": self.outgoing_rotation,
            "action": self.action,
            "display": self.display,
            "first_display": self.first_display,
            "arrival": self.arrival,
            "display_rotation": self.display_rotation,
            "incoming_segment": self.incoming_segment.__str__() if self.incoming_segment else None,
            "incoming_segment_path": self.incoming_segment.segment_path(cell_size=100) if self.incoming_segment else None,
            "outgoing_segment": self.outgoing_segment.__str__() if self.outgoing_segment else None,
            "outgoing_segment_path": self.outgoing_segment.segment_path(cell_size=100) if self.outgoing_segment else None,
            "motion_path": self.motion_path(cell_size=100),
            "prior_action_state": self.prior_action_state.time_step if self.prior_action_state else None,
            "next_action_state": self.next_action_state.time_step if self.next_action_state else None
        }
    
    def __str__(self):
        return f"TrainState(time_step=({self.time_step}), coords=({self.coords.x},{self.coords.y}), rotation={self.rotation}, outgoing_rotation={self.outgoing_rotation}, display_rotation={self.display_rotation}, action={self.action}, display={self.display})"

    def from_step_dict(time_step: int, step_dict: dict) -> TrainState:
        logger.info(f"Creating TrainState for time step {time_step} from step_dict: {step_dict}")
        state_dict = step_dict.get("state", step_dict) # in case of initial/end state without 'state' key
        x = state_dict.get("x", None)
        y = state_dict.get("y", None)
        rotation = state_dict.get("rotation", None)
        action = step_dict.get("action", None)
        return TrainState(time_step=time_step, coords=Point(x, y), rotation=rotation, action=action)

    @property
    def x(self):
        return self.coords.x

    @property
    def y(self):
        return self.coords.y
    
    @property
    def prior_state(self):
        return self._prior_state
    
    @prior_state.setter
    def prior_state(self, value):
        self._prior_state = value
        logger.info(f"Setting prior_state at {self.time_step}: {value} for current state: {self}")
        if not value.next_state == self:
            value.next_state = self
    
    @property
    def next_state(self):
        return self._next_state
    
    @next_state.setter
    def next_state(self, value):
        logger.info(f"Setting next_state at {self.time_step}: {value} for current state: {self}")
        self._next_state = value
        if not value.prior_state == self:
            value.prior_state = self

    @property
    def prior_action_state(self):
        return self._prior_action_state
    
    @prior_action_state.setter
    def prior_action_state(self, value):
        logger.info(f"Setting prior_action_state at {self.time_step}: {value} for current state: {self}")
        self._prior_action_state = value
        if self.action and self.action != 'wait' and not value.next_action_state == self and not value.time_step == -1:
            value.outgoing_rotation = self.rotation
            logger.info(f"\tset outgoing_rotation of action state {value.time_step} to {self.rotation}")
            value.next_action_state = self

    @property
    def next_action_state(self):
        return self._next_action_state
    
    @next_action_state.setter
    def next_action_state(self, value):
        logger.info(f"Setting next_action_state at {self.time_step}:  {value} for current state: {self}")
        self._next_action_state = value
        if self.outgoing_rotation != value.rotation:
            self.outgoing_rotation = value.rotation
        logger.info(f"\tset outgoing_rotation of current state {self.time_step} to {value.rotation}")
        # if self.action and self.action != 'wait' and not value.prior_action_state == self:
        #     # logger.info(f"\taction of current state is {self.action}, setting its prior_action_state to current state")
        #     value.prior_action_state = self

    @property
    def display_rotation(self):
        return self._display_rotation
    
    @display_rotation.setter
    def display_rotation(self, value):
        self._display_rotation = value

    def copy_curve_from(self, other: TrainState):
        self.incoming_segment = other.incoming_segment
        self.outgoing_segment = other.outgoing_segment
        self.display_rotation = other.display_rotation

    def build_segments(self):
        if self.action is None and not self.arrival:
            logger.warning(f"self.action: None")
            logger.info(f"\taction of current state is None, returning without building segments.")
            return
        logger.info(f"\n\nBuilding segments for TrainState at time {self.time_step}: {self}")
        current_rotation = self.rotation
        logger.info(f"Current rotation: {current_rotation}; prior action state: {self.prior_action_state}; next action state: {self.next_action_state}")
        out_rotation = self.outgoing_rotation if self.outgoing_rotation is not None else current_rotation
        next_action_state = self.next_action_state
        logger.info(f"Next action state at time {self.time_step}: {next_action_state}")
        logger.info(f"time step {self.time_step}, building segments for action: {self.action}, current rotation: {current_rotation}, out rotation: {out_rotation}")
        curve = CURVES[(current_rotation, out_rotation)]
        logger.info(f"Display rotation set to: {curve['rotation']}")
        self.incoming_segment = curve['incoming'].translate(self.coords)
        self.outgoing_segment = curve['outgoing'].translate(self.coords)
        self.display_rotation = curve['rotation']
        logger.info(f"Built incoming segment: {self.incoming_segment}:\n{self.incoming_segment.segment_path(cell_size=50)}")
        logger.info(f"Built outgoing segment: {self.outgoing_segment}:\n{self.outgoing_segment.segment_path(cell_size=50)}")
    
    def motion_path(self, cell_size):
        logger.info(f"Building motion path for state: {self}, display rotation: {self.display_rotation}")
        if self.arrival:
            logger.warning(f"Last display state at time {self.time_step}")
        if self.display == False:
            logger.info(f"\tdisplay==False, returning empty motion path")
            return ""
        waiting = self.first_display
        if self.action == "wait" and (self.prior_state and self.prior_state.action == "wait"): #" or self.last_display:
            waiting = True
        if self.action != "wait" and self.prior_state.action == "wait":
            waiting = True
        if waiting:
            if self.first_display:
                logger.info(f"\tfirst display state, building short motion path to start position")
            else:
                logger.info(f"\tconsecutive wait actions or no prior state, returning empty motion path")
            # waiting in place, so just return a super short path in direction of rotation to avoid zero-length path
            offset = ROTATION_OFFSETS[self.display_rotation] * 0.0001
            mid_point = self.outgoing_segment.start + offset
            logger.info(f"Wait action motion path offset: {offset}, mid_point: {mid_point}")
            return f"M {mid_point.abs_string(cell_size=cell_size)} l {offset.rel_string()}"
        if self.prior_action_state.outgoing_segment:
            logger.info(f"\tbuilding motion path from prior action state's outgoing segment and current incoming segment")
            logger.info(f"\tprior action state's outgoing segment: {self.prior_action_state.outgoing_segment}:\n{self.prior_action_state.outgoing_segment.standalone_path(cell_size)}")
            logger.info(f"\tcurrent incoming segment: {self.incoming_segment}:\n{self.incoming_segment.segment_path(cell_size)}")
            return self.prior_action_state.outgoing_segment.standalone_path(cell_size) + self.incoming_segment.segment_path(cell_size)
        else:
            logger.warning(f"No prior action state's outgoing segment found for time {self.time_step}, returning empty motion path.")
            return ""
    
    def segment_path(self, cell_size):
        if self.display == False:
            return ""
        # segment paths are made to be concatenated
        if self.prior_action_state.outgoing_segment:
            return self._prior_action_state.outgoing_segment.segment_path(cell_size) + self.incoming_segment.segment_path(cell_size)
        # without prior outgoing segment, we just return the current position
        mid_point = self.outgoing_segment.start
        return f"M {mid_point.abs_string(cell_size=cell_size)} "
    

@dataclass
class SpeedState(TrainState):
    time_step: int
    coords: Point
    signal: str = None
    rotation: int = None
    outgoing_rotation: int = None
    action: str = None
    display: bool = False
    first_display: bool = False
    arrival: bool = False
    # last_display: bool = False
    _display_rotation: int = None
    # path segment from last center to edge of cell
    incoming_segment: CurveSegment = None
    # path segment from edge of cell to its center
    outgoing_segment: CurveSegment = None
    _prior_state: TrainState = None
    _prior_action_state: TrainState = None
    _next_state: TrainState = None
    _next_action_state: TrainState = None
    speed: int = 0
    _time_frame: list[int] = None
    key_points: list[float] = None

    def __init__(self, time_step: int, coords: Point, rotation: int = None, outgoing_rotation: int = None, action: str = None, display: bool = False, first_display: bool = False, arrival: bool = False, speed: int = 0, time_frame: list[int] = None):
        super().__init__(time_step, coords, rotation=rotation, outgoing_rotation=outgoing_rotation, action=action, display=display, first_display=first_display, arrival=arrival)
        self.speed = speed
        self.time_frame = time_frame
    
    # def __post_init__(self):
    #     print(f"SpeedState __post_init__ for time step {self.time_step} with speed {self.speed} and time_frame {self.time_frame}")
    #     # if time_frame exists, make len(time_frame) key_points from 0 to 1
    #     self.key_points = [0.0]
    #     if self.time_frame and len(self.time_frame) > 1:
    #         frame_len = len(self.time_frame)
    #         self.key_points.extend([round(i / frame_len, 3) for i in range(1, frame_len)])
    #     self.key_points.append(1.0)
    #     logging.info(f"\tGenerated key_points for SpeedState at time step {self.time_step}: {self.key_points}")

    def last_time_step(self):
        return self.time_frame[-1] if self.time_frame else self.time_step
    
    @classmethod
    def from_step_dict(cls, time_step, step_dict, speed, time_frame_len=None) -> SpeedState:
        logger.info(f"Creating SpeedState for time step {time_step} from step_dict: {step_dict} with speed {speed} and time_frame_len {time_frame_len}")
        if not time_frame_len:
            time_frame_len = speed
        state_dict = step_dict.get("state", step_dict)
        position = state_dict.get("position", None)
        if position:
            x = position["x"]
            y = position["y"]
        else:
            x = y = -1
        direction = state_dict.get("direction", None)
        rotation = dir_dict.get(direction, None)
        action = step_dict.get("action", None)
        logger.info(f"\tParsed position: ({x}, {y}), direction: {direction}, rotation: {rotation}, action: {action}")
        
        if action and action != "wait":
            time_step_int = int(time_step)
            time_frame = list(range(time_step_int, time_step_int + time_frame_len))
            logger.info(f"\tAction is '{action}', setting time_frame to {time_frame}")
        else:
            time_frame = [int(time_step)]
        
        return cls(
            time_step=int(time_step),
            coords=Point(x, y),
            rotation=rotation,
            action=action,
            speed=speed,
            time_frame=time_frame
        )
    
    def __str__(self):
        return f"SpeedState(time_step=({self.time_step}), time_frame({self.time_frame}) coords=({self.coords.x},{self.coords.y}), rotation={self.rotation}, outgoing_rotation={self.outgoing_rotation}, display_rotation={self.display_rotation}, action={self.action}, display={self.display})"
    
    def __dict__(self):
        base_dict = super().__dict__()
        base_dict.update({
            "speed": self.speed,
            "time_frame": self.time_frame,
            "key_points": self.key_points
        })
        return base_dict
    
    @property
    def time_frame(self):
        return self._time_frame
    
    @time_frame.setter
    def time_frame(self, value):
        self._time_frame = value
        self.key_points = [0.0]
        if self._time_frame and len(self._time_frame) > 1:
            frame_len = len(self._time_frame)
            self.key_points.extend([round(i / frame_len, 3) for i in range(1, frame_len)])
        self.key_points.append(1.0)
        logging.info(f"\tGenerated key_points for SpeedState at time step {self.time_step}: {self.key_points}")


    def motion_path(self, cell_size, time_step=None):
        if not time_step:
            time_step = self.time_step
        # get position in time_frame
        index = self.time_frame.index(time_step)

        path_string = ""
        logger.info(f"Building motion path for state: {self}, display rotation: {self.display_rotation}")
        if self.arrival:
            logger.warning(f"Last display state at time {self.time_step}")
        if self.display == False:
            logger.info(f"\tdisplay==False, returning empty motion path")
            return {'motion_path': ""}
        waiting = self.first_display
        if self.action == "wait" and (self.prior_state and self.prior_state.action == "wait"): #" or self.last_display:
            waiting = True
        if self.action != "wait":
            if index == 0 and self.prior_state.action == "wait":
                waiting = True
        if waiting:
            if self.first_display:
                logger.info(f"\tfirst display state, building short motion path to start position")
            else:
                logger.info(f"\tconsecutive wait actions or no prior state, returning empty motion path")
            # waiting in place, so just return a super short path in direction of rotation to avoid zero-length path
            offset = ROTATION_OFFSETS[self.display_rotation] * 0.0001
            mid_point = self.outgoing_segment.start + offset
            logger.info(f"Wait action motion path offset: {offset}, mid_point: {mid_point}")
            path_string = f"M {mid_point.abs_string(cell_size=cell_size)} l {offset.rel_string()}"
        elif self.prior_action_state.outgoing_segment:
            logger.info(f"\tbuilding motion path from prior action state's outgoing segment and current incoming segment")
            logger.info(f"\tprior action state's outgoing segment: {self.prior_action_state.outgoing_segment}:\n{self.prior_action_state.outgoing_segment.standalone_path(cell_size)}")
            logger.info(f"\tcurrent incoming segment: {self.incoming_segment}:\n{self.incoming_segment.segment_path(cell_size)}")
            path_string = self.prior_action_state.outgoing_segment.standalone_path(cell_size) + self.incoming_segment.segment_path(cell_size)
        else:
            logger.warning(f"No prior action state's outgoing segment found for time {self.time_step}, returning empty motion path.")
            path_string = ""
        
        # print(f"time_step {time_step} at index {index} in time_frame {self.time_frame}")
        key_points = f"{self.key_points[index]};{self.key_points[index + 1]}"
        # print(f"SpeedState motion_path at time_step {time_step} with key_points {key_points}")
        return {
            "motion_path": path_string,
            "keyPoints": key_points,
            "keyTimes": "0;1"
        }

MOVE_OFFSETS = {
    "n": Point(0, -1),
    "e": Point(1, 0),
    "s": Point(0, 1),
    "w": Point(-1, 0)
}

class TrainPath:
    def __init__(self, train_id: int, train_info: dict, time_frame: int):
        self.train_id = train_id
        self.speed = train_info['speed']
        self.train_info = train_info
        self.time_frame = time_frame
        self.coords: list[Point] = []
        self.segments: list[CurveSegment] = []
        self.keypoints: dict[int, float] = {}
        self.total_distance: float = 0.0
        self.distance_traveled: dict[int, float] = {}
        logger.info(f"Initializing TrainPath for train {train_id} with time frame {time_frame}")
        self.build_path()
        self.build_segments()
        self.calculate_keypoints()

    def get_direction(self, coords: Point, next_coords: Point) -> str:
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
        
    def get_rotation(self, coords: Point, next_coords: Point) -> int:
        direction = self.get_direction(coords, next_coords)
        return dir_dict.get(direction, None)
        
    def build_path(self):
        logger.info(f"Parsing states for TrainPath {self.train_id}")

        distance_traveled = {}
        time_step = 0
        speed = int(self.train_info['speed'])
        while time_step <= self.time_frame:
            coords = self.coords_at(time_step)
            if coords:
                if not self.coords:
                    self.coords.append(coords)
                    distance_traveled[time_step] = 0
                elif coords != self.coords[-1]:
                    self.coords.append(coords)
                    distance_traveled[time_step] = distance_traveled[time_step - 1] + 1 / speed
                else:
                    action = self.action_at(time_step - 1)
                    if action == "wait":
                        # if prior action was 'wait', do not increment distance
                        distance_traveled[time_step] = distance_traveled[time_step - 1]
                    else:
                        # otherwise, we started moving again, but coords change in the next time step
                        distance_traveled[time_step] = distance_traveled[time_step - 1] + 1 / speed
            time_step += 1

        self.distance_traveled = distance_traveled
        self.total_distance = max(distance_traveled.values()) if distance_traveled else 0.0
        print(f"Total distance traveled for train {self.train_id}: {self.total_distance}")

    def build_segments(self):
        start_rotation = dir_dict.get(self.train_info['start']['direction'])
        for i in range(len(self.coords)):
            if i == 0:
                curve = CURVES[(start_rotation, start_rotation)]
                self.segments.append(curve['outgoing'].translate(self.coords[i]))
            elif i == len(self.coords) - 1:
                in_direction = self.get_rotation(self.coords[i-1], self.coords[i])
                out_direction = in_direction
                curve = CURVES[(in_direction, out_direction)]
                self.segments.append(curve['incoming'].translate(self.coords[i]))
                self.segments.append(curve['outgoing'].translate(self.coords[i]))
                # add last coord, which is not calculated by the toolkit
                last_coord = self.coords[i] + MOVE_OFFSETS[rot_dict[out_direction]]
                curve = CURVES[(out_direction, out_direction)]
                self.segments.append(curve['incoming'].translate(last_coord))
            else:
                in_direction = self.get_rotation(self.coords[i-1], self.coords[i])
                out_direction = self.get_rotation(self.coords[i], self.coords[i+1])
                curve = CURVES[(in_direction, out_direction)]
                self.segments.append(curve['incoming'].translate(self.coords[i]))
                self.segments.append(curve['outgoing'].translate(self.coords[i]))
         
    def calculate_keypoints(self):
        logger.info(f"Calculating keypoints for TrainPath {self.train_id}")
        last_keypoint = 0.0
        for timestep in range(self.time_frame + 1):
            if timestep not in self.distance_traveled:
                self.keypoints[timestep] = last_keypoint
            else:
                distance = self.distance_traveled[timestep]
                keypoint = round(distance / self.total_distance, 10) if self.total_distance > 0 else 0.0
                self.keypoints[timestep] = keypoint
                last_keypoint = keypoint
    
    def display_info(self, timestep: int) -> float:
        kp_0 = self.keypoints.get(timestep-1, None)
        kp_1 = self.keypoints.get(timestep, None)
        opacity = 1.0
        if kp_0 == kp_1:
            if kp_0 == 0.0 or kp_0 == 1.0:
                opacity = 0.0
            if kp_1 == 1.0:
                kp_0 -= 0.000001
            else:
                kp_1 += 0.000001
        action = self.action_at(timestep)
        status = self.status_at(timestep)
        position = self.coords_at(timestep)
        signal = None
        if action == "wait":
            signal = "red"
            if self.action_at(timestep + 1) != "wait":
                signal = "green" 
        return {
            "action": action,
            "status": status,
            "position": f"{position.x},{position.y}" if position else None,
            "signal": signal,
            # TODO: make opacity fade in/out
            "opacity": [opacity, opacity],
            "keyPoints": f"{kp_0};{kp_1}",
            # "keyPoints": f"0;1",
            "keyTimes": "0;1"
        }
    
    def get_display_states(self) -> dict[int, dict]:
        display_states = {}
        for timestep in range(self.time_frame + 1):
            display_states[timestep] = self.display_info(timestep)
        return display_states

    def coords_at(self, time_step: int) -> Point:
        time_step = str(time_step)
        if time_step in self.train_info['path']:
            step_dict = self.train_info['path'][time_step]
            coords = Point.from_dict(step_dict['position'])
            return coords
        else:
            return None
        
    def action_at(self, time_step: int) -> str:
        time_step = str(time_step)
        if time_step in self.train_info['path']:
            step_dict = self.train_info['path'][time_step]
            return step_dict.get('action', None)
        else:
            return None
        
    def status_at(self, time_step: int) -> str:
        time_step = str(time_step)
        if time_step in self.train_info['path']:
            step_dict = self.train_info['path'][time_step]
            return step_dict.get('status', None)
        else:
            return None

    def get_path_string(self, cell_size):
        path_string = self.segments[0].standalone_path(cell_size)
        for segment in self.segments[1:]:
            path_string += segment.segment_path(cell_size)
        return path_string