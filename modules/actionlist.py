from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_env import RailEnvActions
from flatland.utils.rendertools import RenderTool, AgentRenderVariant
from modules.convert import convert_actions_to_flatland

def to_dicts(action_list):
    """
    convert a list of actions to a list of action_dicts
    this is more consistent with the structure that flatland accepts
    """
    result = []

    current_time_step = action_list[0][2]
    current_dict = {}

    for agent, command, time_step in action_list:
        if time_step != current_time_step:
            result.append(current_dict)
            current_dict = {}
            current_time_step = time_step
        
        current_dict[agent] = command

    # append the last dictionary after the loop
    result.append(current_dict)

    # replace actions with RailEnvActions
    mapping = {"move_forward":RailEnvActions.MOVE_FORWARD, "move_right":RailEnvActions.MOVE_RIGHT, "move_left":RailEnvActions.MOVE_LEFT, "wait":RailEnvActions.STOP_MOVING}
    return(convert_actions_to_flatland(result))


def build_action_list(models):
    """
    given a model from clingo, build an python action list
    """
    action_list = []
    for func in models[-1]: # only the last model
        func_name = func.name
        if func_name == "action":
            action = func.arguments[1].name
            agent, timestep = func.arguments[0], func.arguments[2]
            agent_num = agent.arguments[0].number
            action_list.append((agent_num,action,timestep.number))
            print(f"Action found: agent {agent_num}, action {action}, timestep {timestep.number}")

    sorted_list = sorted(action_list, key=lambda x: (x[2], x[0]))
    # dump to temporary file for debugging
    with open("temp_action_list.txt", "w") as f:
        for item in sorted_list:
            f.write(f"{item}\n")
    return(to_dicts(sorted_list))