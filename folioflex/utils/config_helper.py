"""Load config."""

import configparser
import os
from pathlib import Path

import tzlocal
import yaml

from folioflex.utils import custom_logger

ROOT_PATH = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = (
    Path(os.getenv("FFX_CONFIG_PATH"))
    if os.getenv("FFX_CONFIG_PATH")
    else ROOT_PATH / "folioflex" / "configs"
)
TESTS_PATH = ROOT_PATH / "tests" / "files"
LOCAL_TIMEZONE = tzlocal.get_localzone()


logger = custom_logger.setup_logging(__name__)


def get_config(path):
    """
    Get the config path.

    Parameters
    ----------
    path : str
       path to the config file

    Returns
    -------
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
        paths_str = ", ".join(map(str, paths_to_try))
        raise FileNotFoundError(
            f"Config file not found at any of the following paths: {paths_str}"
        )

    with open(path_to_try, "r") as f:
        config = yaml.safe_load(f)

    return config


def get_config_options(path, *sections):
    """
    Load the configuration options.

    Parameters
    ----------
    path : str
       path to the config file
    *sections : str
       the section of the config file to load
       the sections can be nested, e.g. "section", "subsections"

    Returns
    -------
    options : dict
        dictionary of options

    """
    config = get_config(path)

    options = {}

    # traverse the sections
    section_data = config.copy()
    try:
        for section in sections:
            section_data = section_data[section]
    except KeyError:
        logger.warning(
            f"Section {' > '.join(sections)} not found in the configuration."
        )
        return {}
    for key, value in section_data.items():
        options[key] = _config_reference(config, value, *sections)

    # the portfolio class has a tx_file option that is not in the config file
    if "tx_file" in options:
        options["name"] = section

    return options


def _config_reference(config, value, *sections):
    """
    Get the value of references in config.

    Parameters
    ----------
    config : ConfigParser
        the config parser
    value : any
        The value in the section
    *sections : str
        the section of the config file to load
        the sections can be nested, e.g. "section", "subsections"

    Returns
    -------
    value : str
        the value of the option

    Notes
    -----
    There are certain special characters
    `static`: reference to static section
    `$`: reference to an environment variable

    """
    if isinstance(value, str):
        value = value.strip()
        # Handle 'static' references
        if value.startswith("static."):
            config_static = config
            if len(sections) > 1:
                for section in sections[:-1]:
                    config_static = config_static[section]
            config_static = config_static.get("static", {})
            ref_option = value[len("static.") :]
            ref_value = config_static.get(ref_option)
            if ref_value is not None:
                return ref_value
            else:
                logger.warning(f"Static reference `static.{ref_option}` not found.")
                return None
        # Handle environment variables
        elif value.startswith("$"):
            env_var = value[1:]
            env_value = os.getenv(env_var)
            if env_value is not None:
                return env_value
            else:
                logger.warning(f"Environment variable {env_var} not found.")
                return None
        # Handle None values
        elif value.lower() in ["", "none", "null"]:
            return None
        else:
            return value
    else:
        # If the value is not a string, return it as is
        return value


config_file = os.path.join(CONFIG_PATH, "config.yml")

# credentials
_credentials_config = get_config_options(config_file, "config", "credentials")
FFX_USERNAME = _credentials_config.get("ffx_username", None)
FFX_PASSWORD = _credentials_config.get("ffx_password", None)

# apis
_api_config = get_config_options(config_file, "config", "api")
FRED_API = _api_config.get("fred_api", None)
SCRAPINGBEE_API = _api_config.get("scrapingbee_api", None)
YODLEE_CLIENT_ID = _api_config.get("yodlee_client_id", None)
YODLEE_SECRET = _api_config.get("yodlee_secret", None)
YODLEE_ENDPOINT = _api_config.get("yodlee_endpoint", None)

# gpts
_gpt_config = get_config_options(config_file, "config", "gpt")
HUGCHAT_LOGIN = _gpt_config.get("hugchat_login", None)
HUGCHAT_PASSWORD = _gpt_config.get("hugchat_password", None)
OPENAI_API_KEY = _gpt_config.get("openai_api_key", None)
BROWSER_LOCATION = _gpt_config.get("browser_location", None)
BROWSER_EXTENSION = _gpt_config.get("browser_extension", None)

# other
_other_config = get_config_options(config_file, "config", "other")
if os.path.exists(r"/app/tests"):
    REDIS_URL = _other_config["redis_url"].get("redis_url", None)
else:
    # if debugging locally will need a redis
    REDIS_URL = _other_config.get("local_redis", None)
SMTP_USERNAME = _other_config.get("smtp_username", None)
SMTP_PASSWORD = _other_config.get("smtp_password", None)
SMTP_SERVER = _other_config.get("smtp_server", None)
SMTP_PORT = _other_config.get("smtp_port", None)
