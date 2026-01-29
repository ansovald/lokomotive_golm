import sys
import pickle
import io
import time
from clingo.symbol import Number, Function
from clingo.application import Application, clingo_main
from modules.convert import convert_to_clingo
from modules.actionlist import build_action_list
import logging
# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO, format='%(levelname)s -- %(name)s: %(message)s', filename='flatland_api.log', filemode='w')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.FileHandler("flatland_api.log", mode="w")
formatter = logging.Formatter("%(levelname)s -- %(name)s: %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)
logger.propagate = False

class IncrementalFlatlandPlan(Application):
    """ takes an environment and a set of primary encodings """
    program_name = "flatland_incremental"
    version = "1.0"

    def __init__(self, env, actions=None, optimize=False):
        self.env = env
        self.actions = actions
        self.action_list = None
        self.model = None
        self.optimize = optimize
        self.stats = {
            "total_running_time": None,
            "incremental": None
        }

    def main(self, ctl, files):
        start_time = time.time()
        # add encodings
        for f in files: 
            print(f"Loading file: {f}")
            ctl.load(f)
        if not files:
            raise Exception('No file loaded into clingo.')
        
        # add env
        ctl.add(convert_to_clingo(self.env))
        
        # add actions
        if self.actions is not None:
            print(f".join(self.actions): {' '.join(self.actions)}")
            ctl.add('base', [], ' '.join(self.actions))
        

        # ground the program
        ctl.ground([("base", [])], context=self)
        # ctl.configuration.solve.models="-1"

        max_time = ctl.symbolic_atoms.by_signature("global", 1)
        print(max_time)
        while True:
            try:
                atom = next(max_time)
                max_time = atom.symbol.arguments[0].number
                break
            except StopIteration:
                break
        if not max_time:
            raise Exception('No max_time defined in the encoding.')

        models = []
        step = 0
        result = None
        while (result == None or result.unsatisfiable) and step < max_time:
            print(f"Incremental step: {step}/{max_time}")
            parts = []
            parts.append(("check", [Number(step)]))
            if step > 0:
                query = Function("query", [Number(step - 1)])
                ctl.release_external(query)
                parts.append(("step", [Number(step)]))
            ctl.ground(parts, context=self)
            query = Function("query", [Number(step)])
            ctl.assign_external(query, True)
            symbolic_atoms = ctl.symbolic_atoms
            print(f"number of symbolic atoms: {symbolic_atoms.__len__()}")
            # for atom in symbolic_atoms.by_signature("action", 3):
            #     print(atom.symbol)
            # for atom in symbolic_atoms.by_signature("speed_action", 4):
            #     print(atom.symbol)
            # for atom in symbolic_atoms.by_signature("occupied", 3):
            #     print(atom.symbol)
            # for atom in symbolic_atoms.by_signature("state", 4):
            #     print(atom.symbol)
            # for atom in symbolic_atoms.by_signature("arrived", 2):
            #     print(atom.symbol)
            # for atom in symbolic_atoms:
            #     if atom.symbol.name in ["transition", "possible_tansition", "arrived"]:
            #         logger.info(f"Time step {step} -- Atom: {atom.literal} Symbol: {atom.symbol}")
            handle = ctl.solve(yield_=True)
            for model in handle:
                models.append(model.symbols(atoms=True))

            result = handle.get()
            # model = handle.model()
            current_running_time = time.time() - start_time
            hours = int(current_running_time // 3600)
            minutes = int((current_running_time % 3600) // 60)
            seconds = current_running_time % 60
            running_time_str = ""
            if hours > 0:
                running_time_str += f"{hours}h "
            if minutes > 0 or hours > 0:
                running_time_str += f"{minutes}m "
            running_time_str += f"{seconds:.2f}s"
            print(f"Current running time: {running_time_str}")
            print(result)
            step += 1
        
        incremental_time = time.time() - start_time
        self.stats["incremental"] = {"running_time": f"{incremental_time:.2f}", "stats": ctl.statistics}
        if result.satisfiable and self.optimize:
            print(f"Solution found in {step} steps.")
            ctl.release_external(Function("query", [Number(step-1)]))
            ctl.configuration.solve.models="-1"
            parts = [("optimize", [])]
            ctl.ground(parts, context=self)
            with ctl.solve(yield_=True) as handle:
                for model in handle:
                    models.append(model.symbols(atoms=True))
            optimization_time = time.time() - incremental_time - start_time
            print(f"Optimization running time: {optimization_time:.2f} seconds.")
            self.stats["optimization"] = {"optimization_time": f"{optimization_time:.2f}", "stats": ctl.statistics}
        
        if models:
            self.model = models[-1]
            print(f"Final model has {len(self.model)} symbols.")
            self.action_list = build_action_list(models)
            print(f"Action list built with {len(self.action_list)} steps.")
            # capture output actions for renderer
            #return(build_action_list(models))
        else:
            print("No models were found.")
            self.model = None
            self.action_list = None
        current_time = time.time()
        total_running_time = current_time - start_time
        print(f"Total running time: {total_running_time:.2f} seconds.")
        self.stats["total_running_time"] = f"{total_running_time:.2f}"

class FlatlandPlan(Application):
    """ takes an environment and a set of primary encodings """
    program_name = "flatland"
    version = "1.0"

    def __init__(self, env, actions=None):
        self.env = env
        self.actions = actions
        self.action_list = None
        self.model = None
        self.stats = None

    def main(self, ctl, files):
        # add encodings
        for f in files: 
            ctl.load(f)
        if not files:
            raise Exception('No file loaded into clingo.')
        
        # add env
        ctl.add(convert_to_clingo(self.env))
        
        # add actions
        if self.actions is not None:
            print(f".join(self.actions): {' '.join(self.actions)}")
            ctl.add('base', [], ' '.join(self.actions))
        
        # ground the program
        ctl.ground([("base", [])], context=self)
        ctl.configuration.solve.models="-1"

        # solve and save models
        models = []
        with ctl.solve(yield_=True) as handle:
            for model in handle:
                models.append(model.symbols(atoms=True))
        
        self.model = models[-1] if models else None
        # capture output actions for renderer
        #return(build_action_list(models))
        self.action_list = build_action_list(models)

        self.stats = ctl.statistics


# let's see later whether we even need this
class FlatlandReplan(Application):
    """ takes an environment, a set of secondary encodings, and additional context """
    program_name = "flatland"
    version = "1.0"

