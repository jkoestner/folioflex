"""Stores constants."""

import ast
import configparser
import os


def load_config(path, section):
    """Load the configuration options for the Portfolio class.

     Parameters
     ----------
     path : str
         column to sum over on the portfolio dataframe
    section : str
        the section of the config file to load

     Returns
     ----------
     options : dict
         dictionary of options for the Portfolio class

     Notes
     ----------
    The following are options for the config file:
         tx_file : str
             the location of the transaction file
         filter_type : list (optional)
             the transaction types to exclude from analysis
             e.g. dividends, cash
         filter_broker : list (optional)
             the brokers to include in analysis
             e.g. company_a, company_b
         funds : list (optional)
             the symbols that should be analyzed as funds. These symbols won't have any
             yahoo finance reference, so we use transaction prices to fill in blank values
         delisted : list (optional)
             similar to funds. These symbols won't have any yahoo finance reference, so we
             use transaction prices to fill in blank values
         benchmarks : list (optional)
             the symbols to use as a benchmark to compare against.
         other_fields : list (optional)
             additional fields to include

    """
    config = configparser.ConfigParser()

    # test if path exists
    try:
        with open(path):
            pass
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found at {path}")

    config.read(path)

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
    If the value of the option is a reference to another option, then the value of that
    option will be returned instead.

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
    else:  # If value is not a reference
        return ast.literal_eval(value)
