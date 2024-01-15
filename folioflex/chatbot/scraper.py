"""
Scraper module.

This module contains functions to scrape the html of a website to be able
to share to a gpt.

"""

import logging
import logging.config
import os
import re

from seleniumbase import SB

from folioflex.utils import config_helper

# create logger
logging.config.fileConfig(
    os.path.join(config_helper.CONFIG_PATH, "logging.ini"),
)
logger = logging.getLogger(__name__)


def scrape_html(url, binary_location=None, extension_dir=None, headless=True, **kwargs):
    """
    Scrape the html of a website.

    Parameters
    ----------
    url : str
        url of the website to scrape
    binary_location : str (optional)
        location of the binary for the browser
    extension_dir : str (optional)
        location of the extension for the browser
    headless : bool (optional)
        whether to run the browser in headless mode
        True by default
    **kwargs : dict (optional)
        keyword arguments for the options of the driver

    Returns
    -------
    scrape_text : str
        the html of the website
    """
    if binary_location or config_helper.BROWSER_LOCATION:
        logger.info("using binary location for browser")
        binary_location = binary_location or config_helper.BROWSER_LOCATION
    if extension_dir or config_helper.BROWSER_EXTENSION:
        logger.info("using extension location for browser")
        extension_dir = extension_dir or config_helper.BROWSER_EXTENSION
    with SB(
        uc=True,
        headless=headless,
        binary_location=binary_location,
        extension_dir=extension_dir,
    ) as sb:
        logger.info("initializing the driver")
        sb.sleep(2)
        # sb needs only one tab
        open_windows = sb.driver.window_handles
        if len(open_windows) >= 2:
            sb.driver.switch_to.window(open_windows[1])
            sb.driver.close()
            sb.driver.switch_to.window(open_windows[0])
        logger.info(f"loading {url}")

        if url.startswith("https://www.wsj.com/livecoverage/"):
            logger.info("wsj has specific landing page")
            url = "https://www.wsj.com/livecoverage/stock-market-today-dow-jones-12-11-2023"
            sb.driver.uc_open_with_tab(url)
            sb.sleep(2)
            sb.driver.uc_click('span:contains("Today\'s Action")')

            logger.info(f"scraping {sb.get_current_url()}")
            sb.sleep(2)  # wait for page to load
            soup = sb.get_beautiful_soup()

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
            sb.driver.uc_open_with_tab(url)
            sb.sleep(2)  # wait for page to load

            logger.info(f"scraping {url}")
            soup = sb.get_beautiful_soup()
            scrape_text = str(soup)

    return scrape_text
