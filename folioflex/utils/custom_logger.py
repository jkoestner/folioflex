"""
Custom logger with color formatter.

inspired by:
https://gist.github.com/joshbode/58fac7ababc700f51e2a9ecdebe563ad

The Jupyter formatter exists due to issues with getting a colored output.
The following issue describes why the formatter doesn't work.
https://github.com/seleniumbase/SeleniumBase/issues/2592
"""

import logging
import sys

from colorama import Back, Fore, Style
from IPython.display import HTML, display


class ColoredFormatter(logging.Formatter):
    """Colored log formatter."""

    def __init__(self, *args, colors=None, **kwargs):
        """Initialize the formatter with specified format strings."""
        super().__init__(*args, **kwargs)
        self.colors = colors if colors else {}

    def format(self, record):
        """Format the specified record as text."""
        record.color = self.colors.get(record.levelname, "")
        record.reset = Style.RESET_ALL
        record.default_color = Fore.WHITE
        return super().format(record)


class JupyterFormatter(logging.Formatter):
    """A logging formatter designed for Jupyter Notebook/Lab with HTML output."""

    def __init__(
        self,
        fmt=None,
        datefmt=None,
        style="{",
        colors=None,
        default_color="white",
    ):
        super().__init__(fmt, datefmt, style)
        self.colors = colors if colors else {}
        self.default_color = default_color

    def format(self, record):
        """Format the specified record as text."""
        plain_message = super().format(record)

        parts = plain_message.split(" | ", 3)
        if len(parts) < 4:
            return f'<span style="color: {self.default_color};">{plain_message}</span>'

        asctime, name, levelname, message = parts
        color = self.colors.get(record.levelname, self.default_color)

        html_message = (
            f'<span style="color: {self.default_color};">{asctime} | {name} | </span>'
            f'<span style="color: {color};">{levelname}</span>'
            f'<span style="color: {self.default_color};"> | </span>'
            f'<span style="color: {color};">{message}</span>'
        )
        return html_message


class JupyterLogHandler(logging.Handler):
    """Logging handler for displaying logs as HTML in Jupyter."""

    def __init__(self, formatter=None):
        super().__init__()
        self.setFormatter(formatter)

    def emit(self, record):
        """Emit a record."""
        msg = self.format(record)
        display(HTML(msg))


def get_formatter(is_jupyter_env):
    """Return appropriate formatter based on the environment."""
    if is_jupyter_env:
        return JupyterFormatter(
            " {asctime} | {name} | {levelname:8} | {message} ",
            style="{",
            datefmt="%Y-%m-%d %H:%M:%S",
            colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "purple",
            },
            default_color="white",
        )
    else:
        return ColoredFormatter(
            "{default_color} {asctime} {reset}|{default_color} {name} {reset}|"
            "{color} {levelname:8} {reset}|{color} {message} {reset}",
            style="{",
            datefmt="%Y-%m-%d %H:%M:%S",
            colors={
                "DEBUG": Fore.CYAN,
                "INFO": Fore.GREEN,
                "WARNING": Fore.YELLOW,
                "ERROR": Fore.RED,
                "CRITICAL": Fore.RED + Back.WHITE + Style.BRIGHT,
            },
        )


def setup_logging(name="folioflex"):
    """
    Set up the logging.

    Returns
    -------
    logger : logging.Logger
        The logger

    """
    is_jupyter_env = is_jupyter()
    formatter = get_formatter(is_jupyter_env)

    # root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    if is_jupyter_env:
        handler = JupyterLogHandler(formatter)
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.WARNING)

    # folioflex logger
    folioflex_logger = logging.getLogger(name)
    folioflex_logger.setLevel(logging.INFO)

    return folioflex_logger


def set_log_level(new_level, module_prefix="folioflex"):
    """
    Set the log level.

    Parameters
    ----------
    new_level : int
        the new log level
    module_prefix : str
        the module logger prefix to set the log level for

    """
    options = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if new_level not in options:
        raise ValueError(f"Log level must be one of {options}")
    # update the log level for all project loggers
    for logger_name, logger in logging.Logger.manager.loggerDict.items():
        # Check if the logger's name starts with the specified prefix
        if logger_name.startswith(module_prefix):
            if isinstance(logger, logging.Logger):
                logger.setLevel(new_level)


def get_log_level(module_prefix="folioflex"):
    """
    Get the log level.

    Parameters
    ----------
    module_prefix : str
        the module logger prefix to get the log level for

    Returns
    -------
    str
        the log level

    """
    log_level = None
    for logger_name, logger in logging.Logger.manager.loggerDict.items():
        # Check if the logger's name starts with the specified prefix
        if logger_name.startswith(module_prefix):
            if isinstance(logger, logging.Logger):
                log_level = logging.getLevelName(logger.getEffectiveLevel())
                break
    return log_level


def test_logger(level="DEBUG"):
    """Test the logger."""
    logger = setup_logging(__name__)
    set_log_level(level)
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")


def is_jupyter():
    """Check if the code is running in a jupyter notebook."""
    try:
        from IPython import get_ipython

        if "IPKernelApp" not in get_ipython().config:  # pragma: no cover
            return False
    except Exception:
        return False
    return True
