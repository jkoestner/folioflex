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
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver
from seleniumbase import SB, Driver

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
    nbr_windows = len(open_windows)
    logger.info(f"close {nbr_windows-1} open windows")
    for window in open_windows:
        sb.driver.switch_to.window(window)
        nbr_windows = len(sb.driver.window_handles)
        if url not in sb.get_current_url() and nbr_windows > 1:
            sb.driver.close()
    open_windows = sb.driver.window_handles
    sb.driver.switch_to.window(open_windows[0])


def scrape_selenium(
    url,
    xvfb=None,
    screenshot=False,
    port=None,
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
    port : int (optional)
        port to use for debugging
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
    chromium_arg = None

    # use xvfb if running a linux os and xvfb is not specified
    if xvfb is None and os.name == "posix" and not headless2:
        logger.info("using xvfb for browser")
        xvfb = True
    if port:
        logger.info(f"using port {port} for browser debugging")
        chromium_arg = f"--remote-debugging-port={port}"

    if binary_location or config_helper.BROWSER_LOCATION:
        logger.info("using binary location for browser")
        binary_location = binary_location or config_helper.BROWSER_LOCATION
    if extension_dir or config_helper.BROWSER_EXTENSION:
        logger.info("using extension location for browser")
        extension_dir = extension_dir or config_helper.BROWSER_EXTENSION
    if proxy:
        logger.info("using proxy for browser")

    # specific landing page
    #
    # this breaks frequently. added the following due to breaks
    # good issue describing the detection:
    # https://github.com/seleniumbase/SeleniumBase/issues/2842
    #
    # incognito=True, to avoid detection
    # xvfb=True, uc works better when display is shown and linux usually needs xvfb
    # headless2=False, uc works better when display is shown
    if re.match(r"https://www\.w.j\.com/finance", url, re.IGNORECASE):
        with SB(
            uc=True,
            incognito=True,
            xvfb=xvfb,
            headless2=headless2,
            binary_location=binary_location,
            extension_dir=extension_dir,
            proxy=proxy,
            chromium_arg=chromium_arg,
            **kwargs,
        ) as sb:
            sb.sleep(2)
            close_windows(sb, url)
            logger.info("obtaining the landing page")
            sb.driver.uc_open_with_reconnect(url, reconnect_time=wait_time + 5)
            try:
                sb.driver.uc_click(
                    "(//p[contains(text(), 'View All')])[1]", reconnect_time=wait_time
                )
                url = sb.get_current_url()
                logger.info(f"scraping {url}")
                soup = sb.get_beautiful_soup()
                if screenshot:
                    logger.info("screenshot saved to 'screenshot.png'")
                    sb.driver.save_screenshot("screenshot.png")
            except Exception:
                logger.error("probably flagged bot: returning None")
                html_content = "<html><body><p>could not scrape</p></body></html>"
                soup = BeautifulSoup(html_content, "html.parser")
                if screenshot:
                    logger.info("screenshot saved to 'screenshot.png'")
                    sb.driver.save_screenshot("screenshot.png")
                return soup, url

    else:
        with SB(
            uc=True,
            incognito=True,
            xvfb=xvfb,
            headless2=headless2,
            binary_location=binary_location,
            extension_dir=extension_dir,
            proxy=proxy,
            chromium_arg=chromium_arg,
            **kwargs,
        ) as sb:
            sb.sleep(2)
            close_windows(sb, url)
            logger.info("initializing the driver")
            sb.driver.uc_open_with_reconnect(url, reconnect_time=wait_time)
            logger.info(f"scraping {url}")
            soup = sb.get_beautiful_soup()
            if screenshot:
                logger.info("screenshot saved to 'screenshot.png'")
                sb.driver.save_screenshot("screenshot.png")

    logger.info("scraped")

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


def scrape_test(url, **kwargs):
    """
    Test basic functionality of seleniumbase scraper.

    When debugging a website it is useful if able to able to find the cause of
    the error from the function or from another source. This function creates
    a pause when connecting to the website that will temporarily stop the selenium
    driver.

    Here are some common test sites:
    - pixelscan.net
    - fingerprint.com/products/bot-detection/
    - nowsecure.nl

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
    driver = Driver(
        uc=True,
        headless2=False,
    )
    driver.sleep(2)
    close_windows(driver, url)
    logger.info("connecting to website")
    driver.uc_open_with_reconnect(url, reconnect_time="breakpoint")
    logger.info("exit site")
    driver.quit()


def attach_to_session(executor_url, session_id, options=None):
    """
    Attach to an existing browser session.

    Parameters
    ----------
    executor_url : str
        The URL of the WebDriver server to connect to.
    session_id : str
        The ID of the session to attach to.
    options : Options, optional
        The options to use when attaching to the session.

    Returns
    -------
    WebDriver
        A WebDriver instance that is attached to the existing session.

    """
    # save the original execute method of driver
    original_execute = WebDriver.execute

    def override_execute_method(self, command, params=None):
        """
        Override for the newSession command.

        Parameters
        ----------
        self : WebDriver
            The WebDriver instance to execute the command on.
        command : str
            The name of the command to execute.
        params : dict, optional
            The parameters for the command.

        Returns
        -------
        dict
            The result of the command execution.

        """
        # point to the existing session
        if command == "newSession":
            return {"value": {"sessionId": session_id, "capabilities": {}}}
        else:
            return original_execute(self, command, params)

    # override the execute method with the original session
    WebDriver.execute = override_execute_method

    # create the driver
    if options is None:
        options = Options()
    driver = WebDriver(command_executor=executor_url, options=options)
    driver.session_id = session_id

    # restore the method
    WebDriver.execute = original_execute

    return driver
