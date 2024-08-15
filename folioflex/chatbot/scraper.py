"""
Scraper module.

This module contains functions to scrape the html of a website to be able
to share to a gpt.

"""

import datetime
import http.client
import re

import requests
from bs4 import BeautifulSoup
from seleniumbase import SB

from folioflex.portfolio import helper
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
    if url.startswith("https://www.wsj.com/finance"):
        # get todays date and make sure it's a valid trading day to use in url
        now = datetime.datetime.now()
        start_hour = 8
        if now.hour < start_hour:
            today = datetime.date.today() - datetime.timedelta(days=1)
        else:
            today = datetime.date.today()
        today = helper.check_stock_dates(today, fix=True, warning=False)["fix_tx_df"][
            "date"
        ][0]
        formatted_today = today.strftime("%m-%d-%Y")

        # go to url
        url = (
            "https://www.wsj.com/livecoverage/stock-market-today-dow-jones-earnings-"
            + formatted_today
        )

    logger.info(f"scraping '{url}' with '{scraper}'")
    if scraper == "selenium":
        soup = scrape_selenium(url, **kwargs)
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
    **kwargs,
):
    """
    Scrape the html of a website using seleniumbase.

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
    # kwargs defaults
    binary_location = kwargs.pop("binary_location", None)
    extension_dir = kwargs.pop("extension_dir", None)
    headless2 = kwargs.pop("headless2", False)
    wait_time = kwargs.pop("wait_time", 10)
    proxy = kwargs.pop("proxy", None)

    if binary_location or config_helper.BROWSER_LOCATION:
        logger.info("using binary location for browser")
        binary_location = binary_location or config_helper.BROWSER_LOCATION
    if extension_dir or config_helper.BROWSER_EXTENSION:
        logger.info("using extension location for browser")
        extension_dir = extension_dir or config_helper.BROWSER_EXTENSION
    if proxy:
        logger.info("using proxy for browser")

    with SB(
        uc=True,
        headless2=headless2,
        binary_location=binary_location,
        extension_dir=extension_dir,
        proxy=proxy,
        **kwargs,
    ) as sb:
        logger.info("initializing the driver")
        # wsj has a specific landing page
        if url.startswith("https://www.wsj.com/livecoverage"):
            url = "https://www.wsj.com/finance"
            sb.driver.uc_open_with_reconnect(url, reconnect_time=wait_time)
            close_windows(sb, url)
            try:
                logger.info("wsj has specific landing page")
                selector = "//p[contains(text(), 'View All')]/ancestor::a[1]"
                url = sb.get_attribute(
                    selector=selector,
                    attribute="href",
                    by="xpath",
                    timeout=6,
                    hard_fail=True,
                )
                sb.driver.uc_open_with_reconnect(url, reconnect_time=wait_time)
                close_windows(sb, url)
            except Exception:
                logger.error("WSJ probably flagged bot: returning None")
                html_content = "<html><body><p>could not scrape wsj</p></body></html>"
                soup = BeautifulSoup(html_content, "html.parser")
                return soup
        # all other
        else:
            sb.driver.uc_open_with_reconnect(url, reconnect_time=wait_time)
            close_windows(sb, url)
        logger.info(f"scraping {sb.get_current_url()}")
        sb.sleep(wait_time)  # wait for page to load
        soup = sb.get_beautiful_soup()

    return soup


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
