import glob
import inspect
import os
from types import FunctionType
from typing import Tuple


def has_arity(fn: FunctionType, argc: int) -> Tuple[bool, str]:
    if not inspect.isfunction(fn):
        return False, "call to has_arity must provide a function"
    sig = inspect.signature(fn)
    params = sig.parameters.values()
    if len(params) != argc:
        return False, f"function in has_arity takes {len(params)} argc, expected {argc}"

    return True, ""


def get_files(base: str, capture: str) -> list[str]:
    pattern = os.path.join(base, capture)
    return [path for path in glob.glob(pattern, recursive=False) if os.path.isfile(path)]
