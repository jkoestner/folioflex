"""Provide cli for folioflex."""

import argparse
import ast
from argparse import ArgumentDefaultsHelpFormatter

from folioflex.dashboard import app
from folioflex.portfolio.portfolio import Manager, Portfolio
from folioflex.utils import mailer


def _parse_input_to_list(input_str):
    """
    Parse the input string.

    Parameters
    ----------
    input_str : str
        string to parse

    Returns
    -------
    result : list
        list of parsed input

    """
    try:
        # Safely evaluate the string
        result = ast.literal_eval(input_str)

        # Check if the result is a list
        if isinstance(result, list):
            return result
        else:
            raise argparse.ArgumentTypeError(f"'{input_str}' is not a valid list")
    except ValueError as err:
        raise argparse.ArgumentTypeError(f"'{input_str}' is not a valid list") from err


def _create_argparser():
    description = """Provides a portfolio tracker and manager."""
    _parser = argparse.ArgumentParser(
        description=description,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )

    # creating subparsers for separate commands
    _subparsers = _parser.add_subparsers(dest="command", help="command to choose")

    # subparser: portfolio
    _portfolio_parser = _subparsers.add_parser("portfolio", help="portfolio command")
    _portfolio_parser.add_argument(
        "-c",
        "--config_path",
        type=str,
        default="portfolio_personal.ini",
        help="The path that has portfolio configuration",
    )

    _portfolio_parser.add_argument(
        "-p",
        "--portfolio",
        type=str,
        default="all",
        help="The portfolio to use for performance calculations",
    )

    _portfolio_parser.add_argument(
        "-d",
        "--date",
        type=str,
        default=None,
        help=(
            "The date to use for performance calculations (YYYY-MM-DD). "
            "None is the max date"
        ),
    )

    _portfolio_parser.add_argument(
        "-l",
        "--lookback",
        type=int,
        default=None,
        help=(
            "The number of days to look back for portfolio performance calculations. "
            "None is all dates"
        ),
    )

    # subparser: manager
    _manager_parser = _subparsers.add_parser("manager", help="manager command")
    _manager_parser.add_argument(
        "-c",
        "--config_path",
        type=str,
        default="portfolio_personal.ini",
        help="The path that has portfolio configuration",
    )

    _manager_parser.add_argument(
        "-p",
        "--portfolios",
        type=ast.literal_eval,
        default=[None],
        help=(
            "The portfolios to use for manager summary calculations. "
            "None is all portfolios"
        ),
    )

    _manager_parser.add_argument(
        "-d",
        "--date",
        type=str,
        default=None,  # None is the max date
        help=(
            "The date to use for performance calculations (YYYY-MM-DD). "
            "None is the max date"
        ),
    )

    _manager_parser.add_argument(
        "-l",
        "--lookback",
        type=ast.literal_eval,
        default=[None],
        help=(
            "The number of days to look back for manager summary "
            "calculations. None is all dates"
        ),
    )

    # subparser: email
    _email_parser = _subparsers.add_parser("email", help="email command")

    _email_parser.add_argument(
        "-el",
        "--email_list",
        type=ast.literal_eval,
        help="The recipients of the email.",
    )

    _email_parser.add_argument(
        "-hm",
        "--heatmap_market",
        type=ast.literal_eval,
        default=None,
        help=(
            "Heatmap function `get_heatmap()` dictionary. Keys are:\n"
            "  - config_path (optional)\n"
            "  - portfolio (optional)\n"
            "  - lookback (optional)"
        ),
    )

    _email_parser.add_argument(
        "-hp",
        "--heatmap_portfolio",
        type=ast.literal_eval,
        default=None,
        help=(
            "Heatmap function `get_heatmap()` dictionary. Keys are:\n"
            "  - config_path (optional)\n"
            "  - portfolio (optional)\n"
            "  - lookback (optional)"
        ),
    )

    _email_parser.add_argument(
        "-mp",
        "--manager_performance",
        type=ast.literal_eval,
        default=None,
        help=(
            "Manager object dictionary. Keys are:\n"
            "  - config_path\n"
            "  - portfolios (optional)\n"
            "  - date (optional)\n"
            "  - lookbacks (optional)\n"
            "  - get_chart (optional)\n"
            "  - chart_lookback (optional)\n"
            "  - chart_benchmarks (optional)"
        ),
    )

    _email_parser.add_argument(
        "-pp",
        "--portfolio_performance",
        type=ast.literal_eval,
        default=None,
        help=(
            "Portfolio object dictionary. Keys are:\n"
            "  - config_path\n"
            "  - portfolio\n"
            "  - date (optional)\n"
            "  - lookback (optional)"
        ),
    )

    _email_parser.add_argument(
        "-c",
        "--chatbot",
        type=ast.literal_eval,
        default=False,
        help=("Whether to use the chatbot to get the query"),
    )

    _email_parser.add_argument(
        "-p",
        "--proxy",
        type=str,
        default=None,
        help=("The proxy to use for the chatbot - user:password@ip:port"),
    )

    _email_parser.add_argument(
        "-pt",
        "--port",
        type=int,
        default=None,
        help=("The remote debugging port to use for the chatbot"),
    )

    _email_parser.add_argument(
        "-s",
        "--scraper",
        type=str,
        default="selenium",
        help=("The scraper to use for the chatbot - 'bee' or 'selenium'"),
    )

    # subparser: dashboard
    _dash_parser = _subparsers.add_parser("dash", help="dashboard command")

    return _parser


parser = _create_argparser()


def cli():
    """Command line interface."""
    args = parser.parse_args()

    if args.command == "portfolio":
        portfolio = Portfolio(config_path=args.config_path, portfolio=args.portfolio)
        portfolio_performance = portfolio.get_performance(
            date=args.date, lookback=args.lookback
        )
        print(portfolio_performance)

    elif args.command == "manager":
        manager = Manager(config_path=args.config_path, portfolios=args.portfolios)
        manager_summary = manager.get_summary(
            date=args.date,
            lookbacks=args.lookback,
        )
        print(manager_summary)

    elif args.command == "email":
        email_status = mailer.generate_report(
            email_list=args.email_list,
            heatmap_market=args.heatmap_market,
            heatmap_portfolio=args.heatmap_portfolio,
            manager_performance=args.manager_performance,
            portfolio_performance=args.portfolio_performance,
            chatbot=args.chatbot,
            proxy=args.proxy,
            port=args.port,
            scraper=args.scraper,
        )
        print(f"status sent: {email_status}")

    elif args.command == "dash":
        app.app.run_server(debug=True)


if __name__ == "__main__":
    cli()
