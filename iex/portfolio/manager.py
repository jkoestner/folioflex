"""
Creates a portfolio manager class.

There are function in class as well:
   - get_summary : this function will provide the summary of portfolio performances
"""

import pandas as pd

pd.options.display.float_format = "{:,.2f}".format


class Manager:
    """An object containing information about portfolio.

    Parameters
    ----------
    portfolios : list
        list of portfolios to analyze. Needs to have transaction history.
    """

    def __init__(
        self,
        portfolios,
    ):
        portfolio_repr = ", ".join([portfolio.name for portfolio in portfolios])
        print(f"Summarizing following portfolios: [{portfolio_repr}]")
        self.portfolios = portfolios
        self.summary = self.get_summary()

    def get_summary(self, date=None):
        """Get summary of portfolios.

        Parameters
        ----------
        date : date (default is max date in portfolio)
            the date the asset summary should be as of.
            If none we use the max date.

        Returns
        ----------
        summary : DataFrame
            the summary of portfolios
                - cash
                - equity
                - market value
                - return
                - benchmark return

        """
        summary = pd.DataFrame()
        for port in self.portfolios:
            df = port.get_performance()
            df = df[df.index == "portfolio"]
            df = df.rename(index={"portfolio": port.name})
            summary = pd.concat([df, summary])

        return summary
