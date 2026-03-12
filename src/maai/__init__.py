from .model import Maai
from .util import get_available_models

__all__ = ["Maai", "MaaiInput", "MaaiOutput", "get_available_models"]


def __getattr__(name):
    if name == "MaaiInput":
        from . import input as MaaiInput
        return MaaiInput
    if name == "MaaiOutput":
        from . import output as MaaiOutput
        return MaaiOutput
    raise AttributeError(f"module 'maai' has no attribute '{name}'")