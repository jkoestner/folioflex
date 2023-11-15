"""
Creates integrations from different repositories.

This section will be a work in progress as integrations will be refined
over time depending on the openness and reliability of the data sources are.

"""

import logging

from hugchat import hugchat
from hugchat.login import Login

from folioflex.utils import config_helper

# logging options https://docs.python.org/3/library/logging.html
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
if logger.hasHandlers():
    logger.handlers.clear()

formatter = logging.Formatter(fmt="%(levelname)s: %(message)s")

# provides the logging to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)


class ChatBotProvider:
    def get_chatbot(self):
        raise NotImplementedError("Subclasses must implement this method")

    def get_query(self, query):
        raise NotImplementedError("Subclasses must implement this method")


class HugChatProvider(ChatBotProvider):
    """Wrapper for Hugging Face gpt - HugChat.

    Class that provides functions that use HugChat.

    reference: https://github.com/Soulter/hugging-chat-api

    Parameters
    ----------
    ChatBotProvider : class
        base structure for chatbot providers
    """

    def get_chatbot(self, hugchat_login=None, hugchat_password=None):
        """Login to HugChat.

        Parameters
        ----------
        hugchat_login : str
            the email address
        hugchat_password : str
            the password

        Returns
        ----------
        chatbot : chatbot
            the chatbot object
        """
        self.hugchat_login = hugchat_login or config_helper.HUGCHAT_LOGIN
        self.hugchat_password = hugchat_password or config_helper.HUGCHAT_PASSWORD
        if not self.hugchat_login or not self.hugchat_password:
            raise ValueError(
                "Please provide a HugChat login and password or set them in the config file."
            )

        logger.info("logging in to HugChat with {}")
        sign = Login(self.hugchat_login, self.hugchat_password)
        cookies = sign.login()

        # Create a ChatBot
        self.chatbot = hugchat.ChatBot(cookies=cookies.get_dict())

        return self.chatbot

    def get_query(self, query):
        """Get query from chatbot.

        Parameters
        ----------
        query : str
            the query to send to the chatbot

        Returns
        ----------
        formatted_response : str
            the response from the chatbot
        """
        if not self.chatbot:
            raise ValueError("Please initialize the chatbot first.")
        response = self.chatbot.query(
            query,
            web_search=True,
        )
        formatted_response = [response["text"]]
        for source in response.web_search_sources:
            formatted_response.append(source.link)
            formatted_response.append(source.title)
            formatted_response.append(source.hostname)

        # join as new lines
        formatted_response = "\n".join(formatted_response)

        return formatted_response


class GPTchat:
    """Generic wrapper for gpt chat providers.

    Class that provides functions that use HugChat.
    """

    def __init__(self, provider=HugChatProvider()):
        """Initialize the Gptchat class.

        Parameters
        ----------
        provider : ChatBotProvider
            the name of the provider
        """
        self.provider = provider

    def chat(self, query):
        # Use the provider's methods to process the chat
        self.provider.get_chatbot()
        response = self.provider.get_query(query)
        return response

    def get_stock_news(self):
        # Use the provider's methods to process the chat
        self.provider.get_chatbot()
        query = "what's the stock market news today and only use wsj.com, reuters.com, and yahoo.finance"
        response = self.provider.get_query(query)

        return response
