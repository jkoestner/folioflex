"""Load config."""

import ast
import configparser
import os

from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT_PATH / "folioflex" / "configs"
TESTS_PATH = ROOT_PATH / "tests" / "files"


def get_config(path):
    """Get the config path.

    Parameters
    ----------
    path : str
       path to the config file

    Returns
    ----------
    config : configparser.ConfigParser
        the config parser

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
            f"Config file not found at any of the following paths: {', '.join(map(str, paths_to_try))}"
        )

    config.read(path_to_try)

    return config


def get_config_options(path, section):
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
    config = get_config(path)
    options = {}
    for option in config.options(section):
        options[option] = _config_reference(config, section, option, fallback=[])

    # the portfolio class has a tx_file option that is not in the config file
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
    `static`: reference to static section
    `$`: reference to an environment variable
    """
    value = config.get(section, option, **kwargs)
    if value.startswith("static"):  # If value is a static reference
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


config_file = CONFIG_PATH / "config.ini"

# credentials
FFX_USERNAME = get_config_options(config_file, "credentials")["ffx_username"]
FFX_PASSWORD = get_config_options(config_file, "credentials")["ffx_password"]

# apis
FRED_API = get_config_options(config_file, "api")["fred_api"]
YODLEE_CLIENT_ID = get_config_options(config_file, "api")["yodlee_client_id"]
YODLEE_SECRET = get_config_options(config_file, "api")["yodlee_secret"]
YODLEE_ENDPOINT = get_config_options(config_file, "api")["yodlee_endpoint"]

# other
if os.path.exists(r"/app/tests"):
    REDIS_URL = get_config_options(config_file, "other")["redis_url"]
else:
    # if debugging locally will need a redis
    REDIS_URL = get_config_options(config_file, "other")["local_redis"]
SMTP_USERNAME = get_config_options(config_file, "other")["smtp_username"]
SMTP_PASSWORD = get_config_options(config_file, "other")["smtp_password"]
SMTP_SERVER = get_config_options(config_file, "other")["smtp_server"]
SMTP_PORT = get_config_options(config_file, "other")["smtp_port"]
