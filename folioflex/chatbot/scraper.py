"""
Scraper module.

This module contains functions to scrape the html of a website to be able
to share to a gpt.

"""

import logging
import logging.config
import os
import re
import time

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from folioflex.utils import config_helper

# create logger
logging.config.fileConfig(
    os.path.join(config_helper.CONFIG_PATH, "logging.ini"),
)
logger = logging.getLogger(__name__)


def uc_create_options(location=None, extension=None):
    """
    Create options for undetected_chromedriver (uc).

    Parameters
    ----------
    location : str (optional)
        location of the binary file for the browser
    extension : str (optional)
        location of the extension file for the browser that would like to load

    Returns
    -------
    options : ChromeOptions
        options for the uc driver
    """
    # list of options https://peter.sh/experiments/chromium-command-line-switches/
    options = uc.ChromeOptions()
    if location or config_helper.BROWSER_LOCATION:
        logger.info("using binary location for browser")
        options.binary_location = location or config_helper.BROWSER_LOCATION
    if extension or config_helper.BROWSER_EXTENSION:
        logger.info("using extension location for browser")
        options.add_argument(
            f"--load-extension={extension or config_helper.BROWSER_EXTENSION}"
        )
    options.add_argument("enable-automation")
    # options.add_argument("--disable-extensions")
    options.add_argument("--disable-browser-side-navigation")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-gpu")
    return options


def create_driver(options, version=None):
    """
    Create the scraping driver for undetected_chromedriver (uc).

    This does not apply to the selenium webdriver.

    Parameters
    ----------
    options : ChromeOptions
        options for the uc driver
    version : int (optional)
        version of the ChromeDriver to use

    Returns
    -------
    driver : Chrome
        the Chrome driver
    """
    try:
        # try to create a driver with the latest ChromeDriver version
        return uc.Chrome(options=options, version_main=version, headless=True)
    except WebDriverException as e:
        if "This version of ChromeDriver only supports Chrome version" in e.msg:
            try:
                # trying to get correct version from error message
                correct_version = int(
                    e.msg.split("Current browser version is ")[1].split(".")[0]
                )
                print(f"using version {correct_version} of ChromeDriver")
                return uc.Chrome(options=options, version_main=correct_version)
            except Exception:
                # couldn't parse correct version, raising same exception
                raise e from None
        else:
            raise e from None


def get_driver(driver="uc", **kwargs):
    """
    Get the scraping driver.

    Parameters
    ----------
    driver : str (optional)
        driver to use, default is "uc"
        - uc: undetected_chromedriver
        - selenium: selenium webdriver
    **kwargs : dict (optional)
        keyword arguments for the options of the driver

    Returns
    -------
    driver : Chrome
        the Chrome driver
    """
    if driver == "uc":
        options = uc_create_options(**kwargs)
        return create_driver(options)
    elif driver == "selenium":
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    else:
        raise ValueError(f"option {driver} not supported")


def scrape_html(url, **kwargs):
    """
    Scrape the html of a website.

    Parameters
    ----------
    url : str
        url of the website to scrape
    **kwargs : dict (optional)
        keyword arguments for the options of the driver

    Returns
    -------
    scrape_text : str
        the html of the website
    """
    # use the driver to get the valid html
    logger.info("initializing the driver")
    driver = get_driver(**kwargs)
    driver.get(url)
    time.sleep(3)  # wait for page to load

    logger.info(f"scraping {url}")
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    scrape_text = str(soup)

    if url.startswith("https://www.wsj.com/livecoverage/stock-market-today-dow-jones"):
        logger.info("cleaning the text")
        # Use regex to find everything between "LIVE UPDATES" and "What to Read Next"
        pattern = r"LIVE UPDATES(.*?)What to Read Next"
        match = re.search(pattern, scrape_text, re.DOTALL)
        try:
            result = match.group(1)
        except AttributeError:
            logger.info("no match found")
            result = scrape_text

        # convert string to soup object, to be able to parse
        soup = BeautifulSoup(result, "html.parser")
        scrape_text = soup.get_text(separator=" ", strip=True)
        scrape_text = scrape_text.replace("\xa0", " ").replace("\\", "")

    # think about adding in https://www.bloomberg.com/ here

    logger.info("closing the driver")
    # close all tabs
    driver.quit()

    return scrape_text
