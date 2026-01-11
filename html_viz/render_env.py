from flatland.envs.rail_env import RailEnv
from flatland.envs.agent_utils import Agent
import pickle
import json

def grid_json(env: RailEnv) -> dict:
    """
    Convert Flatland environment to a grid dictionary
    """
    rail_map = env.rail.grid
    height, width = env.height, env.width
    grid_dict = {}

    for row in range(height):
        grid_dict[row] = {}
        for col in range(width):
            grid_dict[row][col] = str(rail_map[row][col])

    return grid_dict

def train_info(env: RailEnv) -> dict:
    """
    Extract train information from Flatland environment
    """
    dir_map = {0:"n", 1:"e", 2:"s", 3:"w"}
    train_dict = {}

    for agent_num, agent_info in enumerate(env.agents):
        init_y, init_x = agent_info.initial_position
        goal_y, goal_x = agent_info.target
        min_start, max_end = agent_info.earliest_departure, agent_info.latest_arrival
        speed = int(1/agent_info.speed_counter.speed) # inverse, e.g. 1/2 --> 2, 1/4 --> 4 etc.
        direction = dir_map[agent_info.initial_direction]

        train_dict[agent_num] = {
            "start": {
                "position": {
                    "x": int(init_x),
                    "y": int(init_y)
                }, 
                "min_start": int(min_start), 
                "direction": direction
                },
            "end": {
                "position": {
                    "x": int(goal_x),
                    "y": int(goal_y)
                },
                "max_end": int(max_end)
                },
            "speed": int(speed),
            "path": {}
        }

    return train_dict

if __name__ == "__main__":
    # env_path = "/Users/karlosswald/repositories/flatland/flatland_playground/flatland/envs/pkl/env_005--3_3.pkl"
    env_path = "/Users/karlosswald/repositories/flatland/flatland_playground/flatland/output/1767805303.3741739/env.pkl"
    env = pickle.load(open(env_path, "rb"))
    grid = grid_json(env)
    # dump to json file
    with open("grid.json", "w") as f:
        json.dump(grid, f, indent=4)
    print("Grid saved to grid.json")
    trains = train_info(env)
    with open("trains.json", "w") as f:
        json.dump(trains, f, indent=4)
    print("Train info saved to trains.json")