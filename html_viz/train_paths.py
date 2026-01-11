from __future__ import annotations
from html_viz.curves import CURVES, Point, CurveSegment, ROTATION_OFFSETS
from html_viz.svg_files.get_svg import get_train_color
import logging
from dataclasses import dataclass
import json

logger = logging.getLogger("TRAIN_PATHS")
logger.setLevel(logging.INFO)

handler = logging.FileHandler("train_paths.log", mode="w")
formatter = logging.Formatter("%(levelname)s -- %(name)s: %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)
logger.propagate = False


# .train-fill-0{fill:#d50000;}
# TODO: build dynamically from .train-fill-* styles in STANDARD_STYLE
# train_colors = ["#d50000", "#2979ff", "#ff6f00", "#fdd835", "#00c853", "#aa00ff", "#00bfa5"]

# rotation in degrees for each direction
dir_dict = {
    "n": 0,
    "e": 90,
    "s": 180,
    "w": 270
}

# def get_train_color(train_id):
#     train_id = int(train_id)
#     return train_colors[train_id % len(train_colors)]

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


class TrainPath:
    def __init__(self, train_id: int, train_info: dict, time_frame: int):
        self.train_id = train_id
        self.speed = train_info['speed']
        self.train_info = train_info
        self.time_frame = time_frame
        self.states: dict[int, TrainState] = {}
        self.covered_time_steps: dict[int, int] = {}
        self.prior_action_states: dict[int, TrainState] = {}
        self.next_action_states: dict[int, TrainState] = {}
        logger.info(f"Initializing TrainPath for train {train_id} with time frame {time_frame}")
        self.parse_states()

    def extend_covered_time_steps(self, time_steps: list[int]):
        t_0 = time_steps[0]
        for t in time_steps:
            self.covered_time_steps[t] = t_0

    def add_state(self, state: TrainState):
        self.states[state.time_step] = state
        self.extend_covered_time_steps(state.time_frame)

    def get_state(self, time_step: int) -> TrainState:
        state_n = self.covered_time_steps.get(time_step, None)
        if state_n in self.states:
            return self.states[state_n]
        return None

    def parse_states(self):
        logger.info(f"Parsing states for TrainPath {self.train_id}")
        
        first_action_state = None
        prior_state = None
        last_rotation = None
        # first pass: ignore 'wait' actions (irrelevant for path building)
        time_step = 0
        while time_step <= self.time_frame:
            current_state = self.train_state_at(time_step)
            if current_state.action == "wait":
                time_step += 1
                continue
            if current_state.action is None:
                last_rotation = current_state.rotation
                break
            if not prior_state:
                first_action_state = current_state
                first_action_state.time_frame = [time_step]
                prior_state = self.train_state_at(time_step - 1)
                logger.info(f"Initial prior state at time step {time_step-1}: {prior_state}")
            current_state.display = True
            logger.info(f"Time step {time_step}: {current_state}")
            current_state.prior_action_state = prior_state
            self.add_state(current_state)
            prior_state = current_state
            # skip time_steps already covered by time_frame of current action
            time_step = max(current_state.last_time_step() + 1, time_step + 1)
        first_action_state.display = False # "move_forward" onto start position
        last_action_state = self.train_state_at(self.time_frame)
        last_action_state.rotation = last_rotation
        # treat end of line as last action state
        last_action_state.prior_action_state = prior_state
        last_action_state.display = False
        self.add_state(last_action_state)
        prior_state.next_action_state = last_action_state


        # second pass: build segments for action states
        for time_step, state in self.states.items():
            state.build_segments()
        
        arrived = False
        initial = True
        prior_action_state = None
        # third pass: add 'wait' actions, set display flag
        for time_step in range(self.time_frame + 1):
            if time_step in self.states:
                logger.info(f"Time step {time_step}")
                prior_action_state = self.states[time_step]
            if time_step in self.covered_time_steps:
                logger.info(f"Time step {time_step} already covered by action states, skipping.")
            else:
                current_state = self.train_state_at(time_step)
                logger.info(f"Time step {time_step} is a '{current_state.action}' action, initializing state {current_state}")
                current_state.prior_action_state = prior_action_state
                if prior_action_state:
                    current_state.next_action_state = prior_action_state.next_action_state
                else:
                    current_state.next_action_state = first_action_state
                if current_state.action == "wait":
                    current_state.signal = "red"
                    if time_step + 1 in self.states and self.states[time_step + 1].action != "wait":
                        current_state.signal = "green"
                    # copy curve from next action state
                    logger.info(f"\tCopying curve from next action state for wait at time step {time_step}:\n{current_state.next_action_state}")
                    current_state.copy_curve_from(current_state.next_action_state)
                    current_state.display = True
                elif current_state.action is None:
                    if not arrived:
                        last_action_state.rotation = current_state.rotation
                        current_state.display = True
                        arrived = True
                        current_state.arrival = True
                        current_state.next_action_state = last_action_state
                        current_state.build_segments()
                        # after arrival, we stop displaying the train
                    else:
                        # TODO: fade-out after arrival
                        # if self.states[time_step - 1].arrival:
                        #     current_state.display = True
                        #     current_state.last_display = True
                        #     current_state.next_action_state = last_action_state
                        #     current_state.build_segments()
                        # else:
                        current_state.copy_curve_from(prior_action_state)
                else:
                    logger.warning(f"Unexpected action '{current_state.action}' at time step {time_step} in third pass.")
                self.add_state(current_state)
            if time_step > 0 and time_step in self.states:
                self.states[time_step].prior_state = self.get_state(time_step - 1)
        
        initial = True
        # find first display time step
        for time_step in range(self.time_frame + 1):
            if time_step not in self.states:
                continue
            state = self.states[time_step]
            if initial and state.action and state.action == "wait":
                state.display = False
            if state.action and state.action != "wait":
                initial = False
            if state.display:
                state.first_display = True
                logger.info(f"First display state for train {self.train_id} is at time step {time_step}: {state}")
                break

    def train_state_at(self, time_step: int, time_frame_len=None) -> SpeedState:
        time_step = str(time_step)
        if time_step in self.train_info['path']:
            step_dict = self.train_info['path'][time_step]
        else:
            # get start time from self.train_info['start']
            start_time = int(self.train_info['start']['min_start'])
            if int(time_step) <= start_time:
                step_dict = self.train_info['start']
            else:
                # get last element from self.train_info['path']
                last_time_step = max(int(t) for t in self.train_info['path'].keys())
                step_dict = self.train_info['path'][str(last_time_step)]
            step_dict['action'] = self.train_info['path'].get(time_step, {}).get('action', None)
        if step_dict['position'] is None:
            logger.warning(f"Position is None for train {self.train_id} at time step {time_step}, setting to start position.")
            step_dict['position'] = self.train_info['start']['position']
        return SpeedState.from_step_dict(time_step=time_step, step_dict=step_dict, speed=self.speed, time_frame_len=time_frame_len)

    def get_display_states(self, cell_size):
        display_states = {}
        train_states = {}
        for time_step in range(self.time_frame + 1):
            state = self.get_state(time_step)
            if not state:
                logger.warning(f"No state found for time step {time_step} in get_display_states.")
                continue
            train_states[time_step] = state.__dict__()
            opacity = [0.0, 0.0]
            if state.first_display:
                opacity = [0.0, 1.0]
            # elif state.last_display:
            #     opacity = [1.0, 0.3]
            elif state.display:
                opacity = [1.0, 1.0]
            display_states[time_step] = state.motion_path(cell_size, time_step)
            display_states[time_step].update({
                "action": state.action,
                "position": f"[{state.x}, {state.y}]",
                "opacity": opacity,
                "signal": state.signal
            })
            # # make dir "train_paths" if it doesn't exist
            # import os
            # if not os.path.exists("train_paths"):
            #     os.makedirs("train_paths")
            # with open(f"train_paths/train_{self.train_id}_states.json", "w") as f:
            #     json.dump(train_states, f, indent=4)
        return display_states

    def get_path_string(self, cell_size):
        path_string = ""
        for _, state in self.states.items():
            if state.action == "wait": # or state.action is None:
                continue
            path_string += state.segment_path(cell_size)
        path_string = "M" + path_string[1:]  # ensure path starts with 'M'
        return path_string