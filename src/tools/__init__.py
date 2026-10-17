# Tools package
#
# The shared toolkit (analytics, vault, code generation, bash/search, TOOL_REGISTRY, ...)
# lives in src/tools/toolkit.py. It is re-exported lazily (PEP 562) so importing a light
# submodule such as src.tools.dice_roller does not pull in src.config or psutil.
import importlib


def __getattr__(name):
    if name.startswith("__"):
        raise AttributeError(name)
    toolkit = importlib.import_module("src.tools.toolkit")
    try:
        return getattr(toolkit, name)
    except AttributeError:
        raise AttributeError(f"module 'src.tools' has no attribute {name!r}") from None
