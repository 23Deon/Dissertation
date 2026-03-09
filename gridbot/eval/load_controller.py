import importlib.util
import sys


def load_controller(path):
    spec = importlib.util.spec_from_file_location("controller_module", path)
    module = importlib.util.module_from_spec(spec)

    sys.modules["controller_module"] = module
    spec.loader.exec_module(module)

    return module.Controller()