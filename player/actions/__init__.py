
import glob
import os
import traceback


class CommandRegistry:
    """Simple class to keep track of all the commands we find"""

    def __init__(self):
        self.found_commands = {}

    def insert_commands(self, name, cmds):
        """Insert a command into the registry makes sure it is unique"""
        if not isinstance(cmds, list):
            cmds = [cmds]

        for cmd in cmds:
            assert (
                name not in self.found_commands
            ), f"Duplicate command name: {name}"
            self.found_commands[name] = cmd



def fetch_factories(registry, base_module, base_file_name, function_name="action"):
    """Loads all the defined commands"""
    module_path = os.path.dirname(os.path.abspath(base_file_name))

    for module_path in glob.glob(os.path.join(module_path, "[A-Za-z]*.py")):
        module_file = module_path.split(os.sep)[-1]

        if module_file == base_file_name:
            continue

        module_name = module_file.split(".py")[0]

        try:
            module = __import__(".".join([base_module, module_name]), fromlist=[""])
        except ImportError:
            print(traceback.format_exc())
            continue

        if hasattr(module, function_name):
            registry.insert_commands(module_name, module)


def discover_commands():
    """Discover all the commands we can find (plugins and built-in)"""
    registry = CommandRegistry()

    fetch_factories(registry, "player.actions", __file__)

    return registry.found_commands


actions = discover_commands()
