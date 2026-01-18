"""familiar - compose and invoke ai agent prompts."""

from importlib.metadata import version, PackageNotFoundError

__all__ = ["agents", "render", "cli"]

try:
    __version__ = version("familiar-cli")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
