"""Stores constants."""

import os


def get_remote_path():
    """Provide the remote path.

    Returns
    -------
    remote_path : str
       path that should be used depending on local or heroku
    """
    if os.path.isfile(r"/app/files/transactions.xlsx"):
        remote_path = r"/app/files/"

    elif os.path.isfile(r"files/transactions.xlsx"):
        remote_path = r"files/"

    else:
        remote_path = "No files found"

    return remote_path


iex_api_live = os.environ["IEX_API_LIVE"]
iex_api_sandbox = os.environ["IEX_API_SANDBOX"]
aws_tx_file = os.environ["AWS_TX_FILE"]
remote_path = get_remote_path()
