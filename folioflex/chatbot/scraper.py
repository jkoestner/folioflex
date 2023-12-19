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
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumbase import Driver
from webdriver_manager.chrome import ChromeDriverManager

from folioflex.utils import config_helper

# create logger
logging.config.fileConfig(
    os.path.join(config_helper.CONFIG_PATH, "logging.ini"),
)
logger = logging.getLogger(__name__)


def uc_create_options(location=None, extension=None, **kwargs):
    """
    Create options for undetected_chromedriver (uc).

    Parameters
    ----------
    location : str (optional)
        location of the binary file for the browser
    extension : str (optional)
        location of the extension file for the browser that would like to load
    **kwargs : dict (optional)
        keyword arguments for the options of the driver

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


def create_driver(options, version=None, headless=True):
    """
    Create the scraping driver for undetected_chromedriver (uc).

    This does not apply to the selenium webdriver.

    Parameters
    ----------
    options : ChromeOptions
        options for the uc driver
    version : int (optional)
        version of the ChromeDriver to use
    headless : bool (optional)
        whether to run the driver in headless mode, default is True

        note
        ----
        headless is nice however it can cause issues with some websites
        as noted here
        https://github.com/ultrafunkamsterdam/undetected-chromedriver/issues/589

    Returns
    -------
    driver : Chrome
        the Chrome driver
    """
    try:
        # try to create a driver with the latest ChromeDriver version
        return uc.Chrome(options=options, version_main=version, headless=headless)
    except WebDriverException as e:
        if "This version of ChromeDriver only supports Chrome version" in e.msg:
            try:
                # trying to get correct version from error message
                correct_version = int(
                    e.msg.split("Current browser version is ")[1].split(".")[0]
                )
                logger.info(f"using version {correct_version} of ChromeDriver")
                return uc.Chrome(options=options, version_main=correct_version)
            except Exception:
                # couldn't parse correct version, raising same exception
                raise e from None
        else:
            raise e from None


def get_driver(driver="sb", **kwargs):
    """
    Get the scraping driver.

    Parameters
    ----------
    driver : str (optional)
        driver to use, default is "uc"
        - sb: selenium base
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
        return create_driver(options, **kwargs)
    elif driver == "selenium":
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    elif driver == "sb":
        return Driver(undetectable=True, **kwargs)
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
    logger.info(f"loading {url}")

    if url.startswith("https://www.wsj.com/livecoverage/"):
        logger.info("wsj has specific landing page")
        url = "https://www.wsj.com/livecoverage/stock-market-today-dow-jones-12-11-2023"
        driver.open(url)
        driver.click('a:contains("Action")')

        logger.info(f"scraping {driver.current_url}")
        time.sleep(3)  # wait for page to load
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        # removing the html tags
        scrape_text = soup.get_text(separator=" ", strip=True)
        scrape_text = scrape_text.replace("\xa0", " ").replace("\\", "")

        logger.info("cleaning the text")
        # Use regex to find everything between "LIVE UPDATES" and "What to Read Next"
        pattern = r"LIVE(.*?)— By"
        match = re.search(pattern, scrape_text, re.DOTALL)
        try:
            scrape_text = match.group(1)
        except AttributeError:
            logger.info("no match found")

    # TODO: think about adding in https://www.bloomberg.com/ here

    else:
        driver.open(url)
        time.sleep(2)  # wait for page to load

        logger.info(f"scraping {url}")
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        scrape_text = str(soup)

    logger.info("closing the driver")
    # close all tabs
    driver.quit()

    return scrape_text
