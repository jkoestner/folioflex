"""
Scraper module.

This module contains functions to scrape the html of a website to be able
to share to a gpt.

"""

import http.client
import os
import re

import requests
from bs4 import BeautifulSoup
from seleniumbase import SB

from folioflex.utils import config_helper, custom_logger

logger = custom_logger.setup_logging(__name__)


def scrape_html(
    url,
    scraper="selenium",
    **kwargs,
):
    """
    Scrape the html of a website.

    Parameters
    ----------
    url : str
        url of the website to scrape
    scraper : str (optional)
        scraper to use, seleniumbase by default
    **kwargs : dict (optional)
        keyword arguments for the options of the driver

    Returns
    -------
    scrape_results : dict
        dictionary with the url and the text of the website

    """
    scrape_results = {"url": url, "text": None}
    logger.info(f"scraping '{url}' with '{scraper}'")
    if scraper == "selenium":
        soup, url = scrape_selenium(url, **kwargs)
    elif scraper == "bee":
        soup = scrape_bee(url, **kwargs)

    # removing the html tags
    scrape_text = soup.get_text(separator=" ", strip=True)
    scrape_text = scrape_text.replace("\xa0", " ").replace("\\", "")

    if url.startswith("https://www.wsj.com/livecoverage"):
        # Use regex to find everything between "LIVE UPDATES"
        # and "What to Read Next"
        logger.info("cleaning the text")
        pattern = r"LIVE(.*?)By "
        match = re.search(pattern, scrape_text, re.DOTALL)
        try:
            scrape_text = match.group(1)
        except AttributeError:
            logger.info("no match found")

        scrape_results = {"url": url, "text": scrape_text}

    return scrape_results


def close_windows(sb, url):
    """
    Close windows except url.

    Parameters
    ----------
    sb : seleniumbase.SB
        seleniumbase instance
    url : str
        url of the website to scrape

    """
    open_windows = sb.driver.window_handles
    logger.info(f"close {len(open_windows)-1} open windows")
    for window in open_windows:
        sb.driver.switch_to.window(window)
        if url not in sb.get_current_url():
            sb.driver.close()
    open_windows = sb.driver.window_handles
    sb.driver.switch_to.window(open_windows[0])


def scrape_selenium(
    url,
    xvfb=None,
    screenshot=False,
    **kwargs,
):
    """
    Scrape the html of a website using seleniumbase.

    seleniumbase has a lot of methods that can be used in kwargs shown here:
    https://github.com/seleniumbase/SeleniumBase/blob/af3d9545473e55b2a25cdbab8be0b1ed5e1f6afa/seleniumbase/plugins/sb_manager.py



    Parameters
    ----------
    url : str
        url of the website to scrape
    xvfb : bool (optional)
        It's recommended if using uc=True to not run the headless2=True option and to
        have xvfb=True if running in linux.
    screenshot : bool (optional)
        take a screenshot of the website
    **kwargs : dict (optional)
        keyword arguments for the options of the driver

    Returns
    -------
    soup : bs4.BeautifulSoup
        beautiful soup object with the html of the website
    url : str
        url of the website

    """
    # kwargs defaults
    binary_location = kwargs.pop("binary_location", None)
    extension_dir = kwargs.pop("extension_dir", None)
    headless2 = kwargs.pop("headless2", False)
    wait_time = kwargs.pop("wait_time", 10)
    proxy = kwargs.pop("proxy", None)

    # use xvfb if running a linux os and xvfb is not specified
    if xvfb is None and os.name == "posix":
        logger.info("using xvfb for browser")
        xvfb = True

    if binary_location or config_helper.BROWSER_LOCATION:
        logger.info("using binary location for browser")
        binary_location = binary_location or config_helper.BROWSER_LOCATION
    if extension_dir or config_helper.BROWSER_EXTENSION:
        logger.info("using extension location for browser")
        extension_dir = extension_dir or config_helper.BROWSER_EXTENSION
    if proxy:
        logger.info("using proxy for browser")

    # wsj has a specific landing page
    if url.startswith("https://www.wsj.com/finance"):
        with SB(
            uc=True,
            xvfb=xvfb,
            headless2=headless2,
            binary_location=binary_location,
            extension_dir=extension_dir,
            proxy=proxy,
            **kwargs,
        ) as sb:
            logger.info("obtaining the landing page")
            sb.driver.uc_open_with_reconnect(url, reconnect_time=wait_time)
            close_windows(sb, url)
            try:
                selector = "//p[contains(text(), 'View All')]/ancestor::a[1]"
                url = sb.get_attribute(
                    selector=selector,
                    attribute="href",
                    by="xpath",
                    timeout=6,
                    hard_fail=True,
                )
            except Exception:
                logger.error("WSJ probably flagged bot: returning None")
                html_content = "<html><body><p>could not scrape wsj</p></body></html>"
                soup = BeautifulSoup(html_content, "html.parser")
                if screenshot:
                    logger.info(
                        "screenshot saved to 'folioflex/configs/screenshot.png'"
                    )
                    sb.driver.save_screenshot("folioflex/configs/screenshot.png")
                return soup

    # scrape the website
    with SB(
        uc=True,
        xvfb=xvfb,
        headless2=headless2,
        binary_location=binary_location,
        extension_dir=extension_dir,
        proxy=proxy,
        **kwargs,
    ) as sb:
        logger.info("initializing the driver")
        sb.driver.uc_open_with_reconnect(url, reconnect_time=wait_time)
        close_windows(sb, url)
        logger.info(f"scraping {sb.get_current_url()}")
        sb.sleep(wait_time)  # wait for page to load
        soup = sb.get_beautiful_soup()
        if screenshot:
            logger.info("screenshot saved to 'folioflex/configs/screenshot.png'")
            sb.driver.save_screenshot("folioflex/configs/screenshot.png")

    return soup, url


def scrape_bee(url, **kwargs):
    """
    Scrape the html of a website using scrapingbee.

    Parameters
    ----------
    url : str
        url of the website to scrape
    **kwargs : dict (optional)
        keyword arguments for the options of the driver

    Returns
    -------
    soup : bs4.BeautifulSoup
        beautiful soup object with the html of the website

    """
    # increase the max headers to avoid error
    http.client._MAXHEADERS = 1000
    api_key = config_helper.SCRAPINGBEE_API
    stealth_proxy = kwargs.get("stealth_proxy", "true")
    response = requests.get(
        url="https://app.scrapingbee.com/api/v1/",
        params={
            "api_key": api_key,
            "url": url,
            "stealth_proxy": stealth_proxy,
        },
    )
    soup = BeautifulSoup(response.content, "html.parser")

    return soup
