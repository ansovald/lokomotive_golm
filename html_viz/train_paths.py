from __future__ import annotations
from html_viz.curves import CURVES, Point, CurveSegment, ROTATION_OFFSETS, DIR_DICT, ROT_DICT, get_direction, get_rotation, get_wait_path
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

@dataclass
class TrainState:
    timestep: int
    coords: Point
    # actions: list[str]
    duration: int
    status: str
    rotation: int
    incoming_segment: CurveSegment = None
    outgoing_segment: CurveSegment = None

class Movement:
    def __init__(self, train_path: TrainPath, action: str, start: int, duration: int):
        self.train_path = train_path
        self.action = action
        self.start = start
        self.duration = duration
        self.from_state = None
        self.to_state = None
        self.keypoints: list[float] = [0.0, 1.0]
        self.keypoints = self.calculate_keypoints()
        self.motion_path = ""

    def calculate_keypoints(self) -> list[float, float]:
        key_points = [0.0]
        for i in range(1, self.duration + 1):
            kp = i / self.duration
            key_points.append(kp)
        return key_points

    def get_motion_info(self, cell_size: int, timestep) -> str:
        logger.info(f"Getting motion info for movement {self} at timestep {timestep}, \nkeypoints={self.keypoints}")
        if not self.motion_path:
            self.motion_path = self.build_motion_path(cell_size)
        keypoint_idx = timestep - self.start
        return self.motion_path, [self.keypoints[keypoint_idx], self.keypoints[keypoint_idx + 1]]

    def build_motion_path(self, cell_size: int) -> str:
        path_string = self.from_state.outgoing_segment.standalone_path(cell_size)
        path_string += self.to_state.incoming_segment.segment_path(cell_size)
        return path_string
    
    def set_states(self):
        from_state_idx = self.train_path.timestep_state_mapping[self.start]
        self.from_state = self.train_path.main_states[from_state_idx]
        to_state_timestep = self.start + self.duration
        to_state_idx = self.train_path.timestep_state_mapping.get(to_state_timestep, None)
        if to_state_idx is not None:
            self.to_state = self.train_path.main_states[to_state_idx]
        else:
            raise ValueError(f"Movement {self} has no to_state for timestep {to_state_timestep}")
    
    def __str__(self):
        return f"Movement(action={self.action}, start={self.start}, duration={self.duration}, keypoints={self.keypoints}, motion_path={self.motion_path})"

class TrainPath:
    def __init__(self, train_id: int, train_info: dict, time_frame: int, cell_size: int):
        self.train_id = train_id
        self.speed = train_info['speed']
        self.train_info = train_info
        self.time_frame = time_frame
        self.cell_size = cell_size
        self.main_states: list[dict] = []
        self.timestep_state_mapping: dict[int, int] = {}
        self.timestep_movement_mapping: dict[int, int] = {}
        self.movements: list[Movement] = []
        self.path_string = ""
        logger.info(f"Initializing TrainPath for train {train_id} with time frame {time_frame}")
        self.build_base_path()
        self.build_segments()
        # # for debugging: write main states to file
        # with open(f"train_{train_id}_main_states.txt", "w") as f:
        #     for i, state in enumerate(self.main_states):
        #         f.write(f"{i}: " + state.__str__() + "\n")
        # with open(f"train_{train_id}_movements.txt", "w") as f:
        #     f.write(self.timestep_movement_mapping.__str__() + "\n")
        #     for i, action in enumerate(self.movements):
        #         f.write(f"{i}: " + action.__str__() + "\n")
        
    def build_base_path(self):
        logger.info(f"Parsing states for TrainPath {self.train_id}")
        # main states merge consecutive states with same coordinates and status
        timestep = 0
        last_coords = None
        last_state = None
        last_movement = None
        while timestep <= self.time_frame:
            current_state = self.trainstate_at(timestep)
            coords = current_state.coords
            status = current_state.status
            if status == "READY_TO_DEPART":
                # train is ready to depart but hasn't moved yet. Ignore the move action
                self.main_states.append(current_state)
                self.timestep_state_mapping[timestep] = len(self.main_states) - 1
                logger.info(f"Adding READY_TO_DEPART state for train {self.train_id} at timestep {timestep}:\n{current_state}")
            elif coords:
                if not last_coords:
                    self.main_states.append(current_state)
                    last_state = current_state
                    last_coords = coords
                elif coords == last_coords and status == last_state.status:
                    # still moving but coordinates haven't changed yet
                    last_state.duration += 1
                else:
                    self.main_states.append(current_state)
                    last_coords = coords
                    last_state = current_state
                self.timestep_state_mapping[timestep] = len(self.main_states) - 1

                if timestep not in self.timestep_movement_mapping:
                    action = self.action_at(timestep)
                    if action != "wait":
                        movement = Movement(self, action, timestep, self.speed)
                        last_movement = movement
                        self.movements.append(movement)
                        for i in range(timestep, timestep + self.speed):
                            self.timestep_movement_mapping[i] = len(self.movements) - 1
            timestep += 1
        
        last_timestep = self.main_states[-1].timestep + self.main_states[-1].duration
        dest_coords = Point.from_dict(self.train_info['end']['position'])
        arrival_state = TrainState(
            timestep = last_timestep,
            coords = dest_coords,
            duration = 1,
            status = "ARRIVED",
            rotation = get_rotation(self.main_states[-1].coords, dest_coords)
        )
        self.main_states.append(arrival_state)
        self.timestep_state_mapping[last_timestep] = len(self.main_states) - 1

        if last_timestep < self.time_frame:
            self.timestep_state_mapping[last_timestep] = len(self.main_states) - 1
            last_timestep += 1
            duration = self.time_frame - last_timestep + 1
            last_state = TrainState(
                timestep=last_timestep,
                coords=dest_coords,
                duration=duration,
                status="PARKED",
                rotation=arrival_state.rotation
            )
            self.main_states.append(last_state)
            for i in range(last_timestep, self.time_frame + 1):
                self.timestep_state_mapping[i] = len(self.main_states) - 1

    def build_segments(self):
        # Most states have two segments: an incoming segment and an outgoing segment, centered on the state's coordinates.
        # The incoming segment connects to the outgoing segment of the prior state.
        # The outgoing segment connects to the incoming segment of the next state.
        # The movements are connected to the states, and the motion paths are built from the segments of the states.
        for i in range(1, len(self.main_states)):
            # we don't need to build segments for the last state (train has arrived and is stopped)
            logger.info(f"\ntrain={self.train_id}, i={i}/{len(self.main_states)}, building segments for state: {self.main_states[i]}")
            coords = self.main_states[i].coords
            rotation = self.main_states[i].rotation
            status = self.main_states[i].status
            if i == 1:
                curve = CURVES[(rotation, rotation)]
                outgoing = curve['outgoing'].translate(coords)
                self.main_states[i].outgoing_segment = outgoing
                self.path_string = outgoing.standalone_path(self.cell_size)
            elif status == "WAITING":
                # don't need to build any segments for waiting state
                logger.info(f"waiting state for train {self.train_id}, skipping segment building")
                continue
            elif status == "ARRIVED":
                logger.info(f"arrival state for train {self.train_id}, building incoming segment only")
                curve = CURVES[(rotation, rotation)]
                incoming = curve['incoming'].translate(coords)
                self.main_states[i].incoming_segment = incoming
                self.path_string += incoming.segment_path(self.cell_size)
                # we don't need to build any more segments after arrival
                break
            else:
                # train is moving, build incoming and outgoing segments
                next_coordinates = self.main_states[i+1].coords
                offset = 2
                while next_coordinates == coords:
                    next_coordinates = self.main_states[i + offset].coords
                    offset += 1
                logger.info(f"current coords at i={i}: {coords}, rotation={rotation}, next coords: {next_coordinates}")
                out_rotation = get_rotation(coords, next_coordinates)
                logger.info(f"getting curve for (in={rotation}, out={out_rotation})")
                curve = CURVES[(rotation, out_rotation)]
                incoming = curve['incoming'].translate(coords)
                outgoing = curve['outgoing'].translate(coords)
                self.main_states[i].incoming_segment = incoming
                self.main_states[i].outgoing_segment = outgoing
                self.path_string += incoming.segment_path(self.cell_size)
                self.path_string += outgoing.standalone_path(self.cell_size)
                logger.info(f"Built segments for train {self.train_id} at state index {i}:\nIncoming: {incoming}\nOutgoing: {outgoing}")
            logger.info(f"i={i}, {self.main_states[i]}")

    def get_motion_info(self, timestep) -> str:
        movement_idx = self.timestep_movement_mapping.get(timestep, None)
        # if there is no movement for this timestep, return wait path for current state
        if movement_idx is None:
            state_idx = self.timestep_state_mapping.get(timestep, None)
            if state_idx is None:
                # no entry for this timestep, default to initial wait path
                state = self.main_states[1]
                return get_wait_path(state.rotation).translate(state.coords).standalone_path(self.cell_size), [0.0, 1.0]
            else:
                state = self.main_states[state_idx]
                if state.status == "READY_TO_DEPART":
                    state = self.main_states[state_idx + 1]
                    return get_wait_path(state.rotation).translate(state.coords).standalone_path(self.cell_size), [0.0, 1.0]
                logger.info(f"No movement found for train {self.train_id} at timestep {timestep}, defaulting to wait path for state index {state_idx}")
                state = self.main_states[state_idx]
                return get_wait_path(state.rotation).translate(state.coords).standalone_path(self.cell_size), [0.0, 1.0]
        movement = self.movements[movement_idx]
        movement.set_states()
        return movement.get_motion_info(self.cell_size, timestep)
    
    def display_info(self, timestep: int) -> float:
        state_index = self.timestep_state_mapping.get(timestep, None)
        logger.info(f"\nGetting display info for train {self.train_id} at timestep {timestep}, state_index={state_index}")
        if state_index is not None:
            logger.info(f"state_index found for timestep {timestep}: {state_index}")
            state = self.main_states[state_index]
            status = state.status
        else:
            logger.info(f"No state_index found for timestep {timestep}, defaulting to initial PARKED state")
            # no entry for this timestep, default to initial wait path
            state = self.main_states[1]
            status = "PARKED"
            logger.info(f"state: {state}")
        motion_path, keypoints = self.get_motion_info(timestep)
        logger.info(f"state: {self.main_states[state_index] if state_index is not None else 'N/A'}")
        logger.info(f"motion_path: {motion_path}")
        opacity = [1.0, 1.0]
        if status == "PARKED":
            opacity = [0.0, 0.0]
        elif status == "ARRIVED":
            opacity = [1.0, 0.0]
        elif status == "READY_TO_DEPART":
            opacity = [0.0, 1.0]
        action = self.action_at(timestep)
        position = self.coords_at(timestep)
        signal = None
        action = self.action_at(timestep)
        if action == "wait":
            signal = "red"
            if self.action_at(timestep + 1) != "wait":
                signal = "green"
        return {
            "action": action,
            "status": status,
            "position": f"{position.x},{position.y}" if position else None,
            "motionPath": motion_path,
            "signal": signal,
            # TODO: make opacity fade in/out
            "opacity": opacity,
            "keyPoints": f"{keypoints[0]};{keypoints[1]}",
            # "keyPoints": f"0;1",
            # "keyTimes": "0;1"
        }
    
    def trainstate_at(self, timestep: int) -> TrainState:
        return TrainState(
            timestep=timestep,
            coords=self.coords_at(timestep),
            duration=1,
            status=self.status_at(timestep),
            rotation=self.rotation_at(timestep)
        )
    
    def get_display_states(self) -> dict[int, dict]:
        display_states = {}
        for timestep in range(self.time_frame + 1):
            logger.info(f"\nCalling display info for train {self.train_id} at timestep {timestep}")
            display_states[timestep] = self.display_info(timestep)
            logger.info(f"Display info for train {self.train_id} at timestep {timestep}:\n{display_states[timestep]}")
        return display_states

    def coords_at(self, timestep: int) -> Point:
        timestep = str(timestep)
        if timestep in self.train_info['path']:
            step_dict = self.train_info['path'][timestep]
            coords = Point.from_dict(step_dict['position'])
            return coords
        else:
            return None
        
    def action_at(self, timestep: int) -> str:
        timestep = str(timestep)
        if timestep in self.train_info['path']:
            step_dict = self.train_info['path'][timestep]
            return step_dict.get('action', None)
        else:
            return None
        
    def status_at(self, timestep: int) -> str:
        timestep = str(timestep)
        if timestep in self.train_info['path']:
            step_dict = self.train_info['path'][timestep]
            return step_dict.get('status', None)
        else:
            return None
    
    def rotation_at(self, timestep: int) -> str:
        timestep = str(timestep)
        if timestep in self.train_info['path']:
            rotation = DIR_DICT.get(self.train_info['path'][timestep]['direction'], None)
            return rotation
        else:
            return None

    # def get_path_string(self):
    #     path_string = self.segments[0].standalone_path(self.cell_size)
    #     for segment in self.segments[1:]:
    #         path_string += segment.segment_path(self.cell_size)
    #     return path_string