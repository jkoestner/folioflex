"""Tests the chatbot."""

import os

import g4f
import openai
import pytest
from hugchat import hugchat

from folioflex.chatbot import providers


def test_g4f():
    """Checks g4f initialize."""
    chatbot = providers.GPTchat()
    assert isinstance(
        chatbot.provider, providers.G4FProvider
    ), "Default provider - G4F - not initialized correctly."
    assert chatbot.chatbot["model"] == g4f.models.default, "Default model not set."
    assert chatbot.chatbot["provider"] == g4f.Provider.Bing, "Default provider not set."
    assert chatbot.chatbot["auth"] == False, "Default auth not set."
    assert chatbot.chatbot["access_token"] is None, "Default access token not set."


# openai has billing so not testing unless needed
# def test_openai():
#     """Checks openai initialize."""
#     chatbot = providers.GPTchat(provider="openai")
#     assert isinstance(
#         chatbot.provider, providers.OpenaiProvider
#     ), "Default provider - OpenAI - not initialized correctly."
#     assert isinstance(chatbot.chatbot, openai.OpenAI), "Default model not set."
#     response = chatbot.chat("return back 'test' for test purpose")
#     assert response == "test", "Response not as expected."


@pytest.mark.xfail
# hugchat needs api key to be set in environment variable to login
def test_hugchat():
    """Checks hugchat initialize."""
    # Access credentials from environment variables
    hugchat_login = os.environ.get("HUGCHAT_LOGIN")
    hugchat_password = os.environ.get("HUGCHAT_PASSWORD")

    chatbot = providers.GPTchat(
        provider="hugchat",
        hugchat_login=hugchat_login,
        hugchat_password=hugchat_password,
    )
    assert isinstance(
        chatbot.provider, providers.HugChatProvider
    ), "Default provider - HugChat - not initialized correctly."
    assert isinstance(chatbot.chatbot, hugchat.ChatBot), "Default model not set."
    response = chatbot.chat("return back 'test' for test purpose")
    assert response is not None, "Response not as expected."
