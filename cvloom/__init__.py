"""cvloom: manage CV/resume content as YAML, build tailored PDF/HTML outputs."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("cvloom")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.10.1"
