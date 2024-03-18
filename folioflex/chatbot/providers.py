"""
Creates chatbots from different providers.

This section will be a work in progress as integrations will be refined
over time depending on the openness and reliability of the data sources are.
"""

import g4f
import nest_asyncio
from hugchat import hugchat
from hugchat.login import Login
from openai import OpenAI

from folioflex.chatbot import scraper
from folioflex.utils import config_helper, custom_logger

logger = custom_logger.setup_logging(__name__)


class GPTchat:
    """
    Generic wrapper for gpt chat providers.

    Class that provides functions that use HugChat.
    """

    def __init__(self, provider=None, **kwargs):
        """
        Initialize the GPTchat class.

        Parameters
        ----------
        provider : ChatBotProvider
            the name of the provider
            - (g4f, hugchat, openai)
        kwargs : dict
            keyword arguments to pass to the get_chatbot method

        """
        if provider is None:
            self.provider = G4FProvider()
        elif provider == "g4f":
            self.provider = G4FProvider()
        elif provider == "hugchat":
            self.provider = HugChatProvider()
        elif provider == "openai":
            self.provider = OpenaiProvider()
        else:
            raise ValueError(
                f"provider must be one of ['g4f', 'hugchat', 'openai'] and "
                f"not `{provider}`"
            )
        self.chatbot = self.provider.get_chatbot(**kwargs)

    def chat(self, query, scrape_url=None, **kwargs):
        """
        Chat with the provider.

        Parameters
        ----------
        query : str
            the query to send to the chatbot
        scrape_url : str
            the url to scrape
        kwargs : dict
            keyword arguments to pass to the get_query method

        Returns
        -------
        response : str
            the response from the chatbot

        """
        response = self.provider.get_query(query, scrape_url=scrape_url, **kwargs)
        return response


class ChatBotProvider:
    """
    Wrapper for GPT providers.

    Class that provides the base structure for chatbot providers.
    """

    def get_chatbot(self):
        """Get chatbot subclass structure."""
        raise NotImplementedError("Subclasses must implement this method")

    def get_query(self, query, scrape_url=None, **kwargs):
        """Get query subclass structure."""
        raise NotImplementedError("Subclasses must implement this method")


class G4FProvider(ChatBotProvider):
    """
    Wrapper for GPT4Free.

    Class that provides functions that use GPT4Free.
    reference: https://github.com/xtekky/gpt4free

    There are some known issues with GPT4Free that were not working at time
    of writing (12/7/2023):
       - Bard: Bard is not printing the entire response (better to use Bard api)
       - OpenaiChat: OpenaiChat requires an access token so may be difficult
            to automate (better to use Openai api)

    Parameters
    ----------
    ChatBotProvider : class
        base structure for chatbot providers

    """

    def get_chatbot(
        self, g4f_provider=g4f.Provider.Bing, auth=False, access_token=None
    ):
        """
        G4F chatbot.

        Parameters
        ----------
        g4f_provider : g4f.Provider
            the provider to use
        auth : bool
            whether to use authentication
        access_token : str
            the access token to use for OpeanaiChat
            go to https://chat.openai.com/api/auth/session for key

        Returns
        -------
        chatbot : chatbot
            the chatbot object

        """
        # Create a ChatBot
        self.chatbot = {
            "model": g4f.models.default,
            "provider": g4f_provider,
            "auth": auth,
            "access_token": access_token,
        }

        return self.chatbot

    def get_query(self, query, scrape_url=None, **kwargs):
        """
        Get query from chatbot.

        Parameters
        ----------
        query : str
            the query to send to the chatbot
        scrape_url : str
            the url to scrape
        kwargs : dict
            keyword arguments for the options of the chromedriver

        Returns
        -------
        formatted_response : str
            the response from the chatbot

        """
        nest_asyncio.apply()
        scrape_text = None
        url = None
        formatted_response = ""
        if not self.chatbot:
            raise ValueError("Please initialize the chatbot first.")
        if scrape_url:
            scrape_results = scraper.scrape_html(scrape_url, **kwargs)
            scrape_text = scrape_results["text"]
            url = scrape_results["url"]
            formatted_response = f"{url}\n\n"
            if scrape_text is None:
                return f"Did not find any text to scrape at {url}."

        logger.info(
            f"querying the chatbot - G4F with {self.chatbot['provider'].__module__}"
        )
        response = g4f.ChatCompletion.create(
            model=self.chatbot["model"],
            messages=[
                {
                    "role": "user",
                    "content": f"{query} {scrape_text}",
                }
            ],
            provider=self.chatbot["provider"],
            auth=self.chatbot["auth"],
            access_token=self.chatbot["access_token"],
        )

        formatted_response += response

        return formatted_response


class HugChatProvider(ChatBotProvider):
    """
    Wrapper for Hugging Face GPT - HugChat.

    Class that provides functions that use HugChat.

    reference: https://github.com/Soulter/hugging-chat-api

    Parameters
    ----------
    ChatBotProvider : class
        base structure for chatbot providers

    """

    def get_chatbot(self, hugchat_login=None, hugchat_password=None):
        """
        Login to HugChat.

        Parameters
        ----------
        hugchat_login : str
            the email address
        hugchat_password : str
            the password

        Returns
        -------
        chatbot : chatbot
            the chatbot object

        """
        self.hugchat_login = hugchat_login or config_helper.HUGCHAT_LOGIN
        self.hugchat_password = hugchat_password or config_helper.HUGCHAT_PASSWORD
        if not self.hugchat_login or not self.hugchat_password:
            raise ValueError(
                "Please provide a HugChat login and password "
                "or set them in the config file."
            )

        logger.info("logging in to HugChat")
        sign = Login(self.hugchat_login, self.hugchat_password)
        cookies = sign.login()

        # Create a ChatBot
        self.chatbot = hugchat.ChatBot(cookies=cookies.get_dict())

        return self.chatbot

    def get_query(self, query, scrape_url=None, **kwargs):
        """
        Get query from chatbot.

        Parameters
        ----------
        query : str
            the query to send to the chatbot
        scrape_url : str
            the url to scrape
        kwargs : dict
            keyword arguments for the options of the chromedriver

        Returns
        -------
        formatted_response : str
            the response from the chatbot

        """
        scrape_text = None
        url = None
        web_search = kwargs.get("web_search", False)
        formatted_response = ""
        if not self.chatbot:
            raise ValueError("Please initialize the chatbot first.")
        if scrape_url:
            scrape_results = scraper.scrape_html(scrape_url, **kwargs)
            scrape_text = scrape_results["text"]
            url = scrape_results["url"]
            formatted_response = f"{url}\n\n"
            if scrape_text is None:
                return f"Did not find any text to scrape at {url}."

        logger.info(f"querying the chatbot - HugChat - web_search: {web_search}")
        response = self.chatbot.query(
            f"{query} {scrape_text}",
            web_search=web_search,
        )
        formatted_response = [response["text"]]
        for source in response["web_search_sources"]:
            formatted_response.append(source["link"])
            formatted_response.append(source["title"])
            formatted_response.append(source["hostname"])

        return formatted_response


class OpenaiProvider(ChatBotProvider):
    """
    Wrapper for OpenAI.

    Class that provides functions that use OpenAI.
    reference: https://platform.openai.com/docs/quickstart?context=python

    pricing: https://openai.com/pricing

    Parameters
    ----------
    ChatBotProvider : class
        base structure for chatbot providers

    """

    def get_chatbot(self):
        """
        OpenAI chatbot.

        Returns
        -------
        chatbot : chatbot
            the chatbot object

        """
        # Create a ChatBot
        logger.info("create a chatbot with OpenAI")
        self.chatbot = OpenAI(api_key=config_helper.OPENAI_API_KEY)

        return self.chatbot

    def get_query(self, query, scrape_url=None, model="gpt-4-1106-preview", **kwargs):
        """
        Get query from chatbot.

        reference docs: https://platform.openai.com/docs/api-reference/chat/create

        Parameters
        ----------
        query : str
            the query to send to the chatbot
        scrape_url : str
            the url to scrape
        model : str
            the model to use
        kwargs : dict
            keyword arguments for the options of the chromedriver

        Returns
        -------
        formatted_response : str
            the response from the chatbot

        """
        scrape_text = None
        url = None
        formatted_response = ""
        if not self.chatbot:
            raise ValueError("Please initialize the chatbot first.")
        if scrape_url:
            scrape_results = scraper.scrape_html(scrape_url, **kwargs)
            scrape_text = scrape_results["text"]
            url = scrape_results["url"]
            formatted_response = f"{url}\n\n"
            if scrape_text is None:
                return f"Did not find any text to scrape at {url}."

        logger.info("querying the chatbot - OpenAI")
        response = self.chatbot.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": f"{query} {scrape_text}",
                }
            ],
        )

        # TODO add in handler for rate limits

        formatted_response += response.choices[0].message.content

        return formatted_response
