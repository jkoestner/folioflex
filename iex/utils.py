"""Load config."""

import ast
import configparser
import os

from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_PATH / "iex" / "configs"
TESTS_PATH = ROOT_PATH / "tests" / "files"


def load_config(path, section):
    """Load the configuration options.

     Parameters
     ----------
     path : str
        path to the config file
    section : str
        the section of the config file to load

     Returns
     ----------
     options : dict
         dictionary of options

    """
    config = configparser.ConfigParser()

    # test if path exists and try default directories (CONFIG_PATH, TESTS_PATH)
    paths_to_try = [
        path,
        os.path.join(CONFIG_PATH, path),
        os.path.join(TESTS_PATH, path),
    ]
    for path_to_try in paths_to_try:
        try:
            with open(path_to_try):
                break
        except FileNotFoundError:
            continue
    else:
        raise FileNotFoundError(
            f"Config file not found at any of the following paths: {', '.join(paths_to_try)}"
        )

    config.read(path_to_try)

    options = {}
    for option in config.options(section):
        options[option] = _config_reference(config, section, option, fallback=[])

    if "tx_file" in options:
        options["name"] = section

    return options


def _config_reference(config, section, option, **kwargs):
    """Get the value of references in config.

    Parameters
    ----------
    config : ConfigParser
        the config parser
    section : str
        the section of the config file
    option : str
        the option to get the value of
    **kwargs : dict
        additional keyword arguments to pass to the config.get() method

    Returns
    ----------
    value : str
        the value of the option

    Notes
    ----------
    There are certain special characters
    `.`: reference to another section
    `$`: reference to an environment variable
    """
    value = config.get(section, option, **kwargs)
    if "." in value:  # If value is a reference
        ref_section, ref_option = value.split(".")
        value = config.get(ref_section, ref_option, **kwargs)
        if value.startswith("$"):
            return os.getenv(value[1:])
        else:
            return ast.literal_eval(value)
    elif value.startswith("$"):  # If value is an environment variable
        return os.getenv(value[1:])
    else:
        return ast.literal_eval(value)
