"""Budget dashboard."""

import datetime

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, callback, dcc, html
from dateutil.relativedelta import relativedelta
from flask_login import current_user

from folioflex.budget import budget, models
from folioflex.dashboard.components import dash_formats
from folioflex.dashboard.utils import dashboard_helper
from folioflex.portfolio import assets, loans
from folioflex.utils import custom_logger, database

logger = custom_logger.setup_logging(__name__)

dash.register_page(__name__, path="/budget", title="folioflex - Budget", order=5)

# get the prior month
prior_month = (datetime.datetime.now() - relativedelta(months=1)).strftime("%Y-%m")


def layout():
    """Create layout for the budget dashboard."""
    if not current_user.is_authenticated:
        return html.Div(["Please ", dcc.Link("login", href="/login"), " to continue"])

    return dbc.Container(
        [
            # Hidden defaults needed for callbacks
            *dashboard_helper.get_defaults(),
            # Header
            html.H2("Budget Dashboard", className="text-center my-4"),
            # Input Controls Card
            dbc.Card(
                [
                    dbc.CardHeader(html.H4("Budget Controls")),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Date (YYYY-MM)"),
                                            dcc.Input(
                                                id="budget-chart-input",
                                                value=prior_month,
                                                type="text",
                                                className="form-control",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Budget Name"),
                                            dcc.Input(
                                                id="budget-section-input",
                                                placeholder="budget name",
                                                type="text",
                                                className="form-control",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "Update Budget Database",
                                                id="budget-update-db-button",
                                                color="primary",
                                                className="mt-4",
                                            ),
                                        ],
                                        width=3,
                                    ),
                                ],
                                className="g-3",
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),
            # Main Content Accordion
            dbc.Accordion(
                [
                    # Budget Chart Section
                    dbc.AccordionItem(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Button(
                                            "Budget Chart",
                                            id="budget-chart-button",
                                            color="primary",
                                            className="mb-3",
                                        ),
                                        width="auto",
                                    ),
                                ]
                            ),
                            html.Div(
                                id="budget-chart-line",
                                children="",
                                className="text-muted mt-2",
                            ),
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            dcc.Loading(
                                                id="loading-budget-chart",
                                                type="dot",
                                                children=html.Div(id="budget-chart"),
                                            ),
                                            html.Div(
                                                id="budget-chart-labels",
                                                children="",
                                                className="text-muted mt-2",
                                            ),
                                        ]
                                    ),
                                ]
                            ),
                            dbc.Toast(
                                "Updated database tables.",
                                id="toast-update-db",
                                header="Updated Database",
                                is_open=False,
                                dismissable=True,
                                icon="success",
                            ),
                        ],
                        title="Budget Chart",
                    ),
                    # Label Analysis Section
                    dbc.AccordionItem(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "Label Chart",
                                                id="label-chart-button",
                                                color="primary",
                                                className="mb-3",
                                            ),
                                        ],
                                        width="auto",
                                    ),
                                ]
                            ),
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            dbc.Label("Select Label"),
                                            dcc.Dropdown(
                                                id="label-dropdown",
                                                className="mb-3",
                                            ),
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        dcc.Loading(
                                                            id="loading-expense-chart",
                                                            type="dot",
                                                            children=html.Div(
                                                                id="expense-chart"
                                                            ),
                                                        ),
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        dcc.Loading(
                                                            id="loading-expense-table",
                                                            type="dot",
                                                            children=html.Div(
                                                                id="expense-table"
                                                            ),
                                                        ),
                                                        width=6,
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                ]
                            ),
                        ],
                        title="Label Analysis",
                    ),
                    # Income Section
                    dbc.AccordionItem(
                        [
                            dbc.Button(
                                "Income Chart",
                                id="income-chart-button",
                                color="primary",
                                className="mb-3",
                            ),
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        dcc.Loading(
                                            id="loading-income-chart",
                                            type="dot",
                                            children=html.Div(id="income-chart"),
                                        ),
                                    ),
                                ]
                            ),
                        ],
                        title="Income Analysis",
                    ),
                    # Expense Comparison Section
                    dbc.AccordionItem(
                        [
                            dbc.Button(
                                "Compare Chart",
                                id="budget-compare-button",
                                color="primary",
                                className="mb-3",
                            ),
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        dcc.Loading(
                                            id="loading-compare-chart",
                                            type="dot",
                                            children=html.Div(id="compare-chart"),
                                        ),
                                    ),
                                ]
                            ),
                        ],
                        title="Expense Comparison",
                    ),
                    # Subscription Section
                    dbc.AccordionItem(
                        [
                            dbc.Button(
                                "Subscription Table",
                                id="subscription-button",
                                color="primary",
                                className="mb-3",
                            ),
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        dcc.Loading(
                                            id="loading-subscription-table",
                                            type="dot",
                                            children=html.Div(id="subscription-table"),
                                        ),
                                    ),
                                ]
                            ),
                        ],
                        title="Subscriptions",
                    ),
                    # Assets Section
                    dbc.AccordionItem(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Button(
                                            "Assets Table",
                                            id="assets-button",
                                            color="primary",
                                            className="mb-3",
                                        ),
                                    ),
                                    dbc.Col(
                                        dbc.Button(
                                            "Update Assets Values",
                                            id="assets-retrieve-button",
                                            color="secondary",
                                            className="mb-3",
                                        ),
                                    ),
                                ]
                            ),
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        dcc.Loading(
                                                            id="loading-assets-table",
                                                            type="dot",
                                                            children=html.Div(
                                                                id="assets-table"
                                                            ),
                                                        ),
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        dcc.Loading(
                                                            id="loading-assets-chart",
                                                            type="dot",
                                                            children=html.Div(
                                                                id="assets-chart"
                                                            ),
                                                        ),
                                                        width=6,
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                ]
                            ),
                        ],
                        title="Assets",
                    ),
                    # Loans Section
                    dbc.AccordionItem(
                        [
                            dbc.Button(
                                "Loans Table",
                                id="loans-button",
                                color="primary",
                                className="mb-3",
                            ),
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        dcc.Loading(
                                            id="loading-loans-table",
                                            type="dot",
                                            children=html.Div(id="loans-table"),
                                        ),
                                    ),
                                ]
                            ),
                        ],
                        title="Loans",
                    ),
                ],
                start_collapsed=True,
                always_open=True,
            ),
        ],
        fluid=True,
    )


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/


# budget chart
@callback(
    [
        Output("budget-chart", "children"),
        Output("budget-chart-labels", "children"),
        Output("budget-chart-line", "children"),
    ],
    [Input("budget-chart-button", "n_clicks")],
    [State("budget-chart-input", "value"), State("budget-section-input", "value")],
    prevent_initial_call=True,
)
def update_budgetchart(n_clicks, input_value, budget_section):
    """Provide budget info chart."""
    if budget_section is None:
        logger.error("Budget section input is not defined.")
        return dash.no_update
    bdgt = budget.Budget(config_path="config.yml", budget=budget_section)
    budget_df = bdgt.get_transactions()
    budget_df = bdgt.modify_transactions(budget_df)
    budget_view = bdgt.budget_view(
        budget_df, target_date=input_value, exclude_labels=["income"]
    )
    budget_chart = bdgt.display_budget_view(budget_view)
    len_label = len(budget_df[~budget_df["label"].isnull()])
    len_unlabel = len(budget_df[budget_df["label"].isnull()])

    budget_chart_labels = f"Labeled: {len_label} | Unlabeled: {len_unlabel}"
    budget_chart_line = (
        f"the following categories are not included in the budget: {bdgt.zero_txs}"
    )

    return dcc.Graph(figure=budget_chart), budget_chart_labels, budget_chart_line


# income chart
@callback(
    Output("income-chart", "children"),
    [Input("income-chart-button", "n_clicks")],
    [State("budget-chart-input", "value"), State("budget-section-input", "value")],
    prevent_initial_call=True,
)
def update_incomeview(n_clicks, input_value, budget_section):
    """Provide income info chart."""
    if budget_section is None:
        logger.error("Budget section input is not defined.")
        return dash
    bdgt = budget.Budget(config_path="config.yml", budget=budget_section)
    budget_df = bdgt.get_transactions()
    budget_df = bdgt.modify_transactions(budget_df)
    income_chart = bdgt.display_income_view(budget_df)

    return dcc.Graph(figure=income_chart)


# budget compare chart
@callback(
    Output("compare-chart", "children"),
    [Input("budget-compare-button", "n_clicks")],
    [State("budget-chart-input", "value"), State("budget-section-input", "value")],
    prevent_initial_call=True,
)
def update_comparechart(n_clicks, input_value, budget_section):
    """Provide budget compare info chart."""
    if budget_section is None:
        logger.error("Budget section input is not defined.")
        return dash.no_update
    bdgt = budget.Budget(config_path="config.yml", budget=budget_section)
    budget_df = bdgt.get_transactions()
    budget_df = bdgt.modify_transactions(budget_df)
    compare_chart = bdgt.display_compare_expenses_view(
        budget_df, target_date=input_value, avg_months=3
    )

    return dcc.Graph(figure=compare_chart)


# update budget db
@callback(
    Output("toast-update-db", "is_open"),
    [Input("budget-update-db-button", "n_clicks")],
    State("budget-section-input", "value"),
    prevent_initial_call=True,
)
def update_budget_db(n_clicks, budget_section):
    """Provide budget compare info chart."""
    # get the unlabeled transactions
    if budget_section is None:
        logger.error("Budget section input is not defined.")
        return dash.no_update
    bdgt = budget.Budget(config_path="config.yml", budget=budget_section)
    budget_df = bdgt.get_transactions()
    train_df = budget_df[~budget_df["label"].isna()]
    unlabeled_df = budget_df[budget_df["label"].isna()]

    # use trained model to predict labels
    model = models.Classifier(train_df=train_df)
    model.load_model(model_name=bdgt.model)
    predict_df = model.predict_labels(
        unlabeled_df=unlabeled_df, components=model.components
    )

    # update the database with the predicted labels
    bdgt.update_labels_db(tx_df=predict_df, label_column="predicted_label")

    return True


@callback(
    Output("expense-chart", "children"),
    Output("label-dropdown", "options"),
    [Input("label-chart-button", "n_clicks"), Input("label-dropdown", "value")],
    State("budget-section-input", "value"),
    prevent_initial_call=True,
)
def update_category_chart(n_clicks, selected_label, budget_section):
    """Display category chart."""
    if budget_section is None:
        logger.error("Budget section input is not defined.")
        return dash.no_update
    bdgt = budget.Budget(config_path="config.yml", budget=budget_section)
    budget_df = bdgt.get_transactions()
    budget_df = bdgt.modify_transactions(budget_df)

    labels = budget_df["label"].dropna().unique()
    labels.sort()
    label_options = [{"label": label, "value": label} for label in labels]
    if selected_label is None:
        selected_label = labels[0]

    expense_chart = bdgt.display_category_trend(budget_df, selected_label)

    return dcc.Graph(figure=expense_chart, id="expense-chart-fig"), label_options


@callback(
    Output("expense-table", "children"),
    [Input("expense-chart-fig", "clickData"), Input("label-dropdown", "value")],
    State("budget-section-input", "value"),
    prevent_initial_call=True,
)
def update_expenses_table(clickData, selected_label, budget_section):
    """Update the table with expenses for the selected label and month."""
    if clickData is None:
        return dash.no_update
    if budget_section is None:
        logger.error("Budget section input is not defined.")
        return dash.no_update

    clicked_month = clickData["points"][0]["x"]
    clicked_month = pd.to_datetime(clicked_month).strftime("%Y-%m")
    logger.info(f"Selected month: {clicked_month}")

    bdgt = budget.Budget(config_path="config.yml", budget=budget_section)
    budget_df = bdgt.get_transactions()
    budget_df = bdgt.modify_transactions(budget_df)

    expense_tbl = bdgt.category_tx_view(
        tx_df=budget_df, target_date=clicked_month, category=selected_label
    )

    # create the table
    expense_table_div = html.Div(
        [
            dag.AgGrid(
                id="grid-expense",
                rowData=expense_tbl.to_dict("records"),
                columnDefs=dash_formats.get_column_defs(expense_tbl),
            )
        ]
    )

    return expense_table_div


@callback(
    Output("subscription-table", "children"),
    [Input("subscription-button", "n_clicks")],
    State("budget-section-input", "value"),
    prevent_initial_call=True,
)
def update_subscription_table(clickData, budget_section):
    """Update the table with possible subscriptions."""
    if clickData is None:
        return dash.no_update
    if budget_section is None:
        logger.error("Budget section input is not defined.")
        return dash.no_update

    bdgt = budget.Budget(config_path="config.yml", budget=budget_section)
    budget_df = bdgt.get_transactions()
    budget_df = bdgt.modify_transactions(budget_df)

    subscription_tbl = bdgt.identify_subscriptions(tx_df=budget_df)

    # create the table
    subscription_tbl_div = html.Div(
        [
            dag.AgGrid(
                id="grid-subscription",
                rowData=subscription_tbl.to_dict("records"),
                columnDefs=dash_formats.get_column_defs(subscription_tbl),
            )
        ]
    )

    return subscription_tbl_div


@callback(
    [Output("assets-table", "children"), Output("assets-chart", "children")],
    [Input("assets-button", "n_clicks")],
    State("budget-section-input", "value"),
    prevent_initial_call=True,
)
def update_assets_table(clickData, budget_section):
    """Update the table with assets."""
    if clickData is None:
        return dash.no_update
    if budget_section is None:
        logger.error("Budget section input is not defined.")
        return dash.no_update

    engine = database.Engine(config_path="config.yml")
    # get asset_df
    asset_df = assets.get_asset_df(engine=engine, user=budget_section, current=True)

    # create the table
    assets_tbl_div = html.Div(
        [
            dag.AgGrid(
                id="grid-assets",
                rowData=asset_df.to_dict("records"),
                columnDefs=dash_formats.get_column_defs(asset_df),
            )
        ]
    )

    # create the chart
    unfiltered_asset_df = assets.get_asset_df(
        engine=engine, user=budget_section, current=False
    )
    asset_chart = assets.display_asset_trend(unfiltered_asset_df)

    return assets_tbl_div, dcc.Graph(figure=asset_chart)


@callback(
    Output("loans-table", "children"),
    [Input("loans-button", "n_clicks")],
    State("budget-section-input", "value"),
    prevent_initial_call=True,
)
def update_loans_table(clickData, budget_section):
    """Update the table with loans."""
    if clickData is None:
        return dash.no_update
    if budget_section is None:
        logger.error("Budget section input is not defined.")
        return dash.no_update

    engine = database.Engine(config_path="config.yml")
    # get loans in config
    loans_df = loans.get_loan_df(
        config_path="config.yml", engine=engine, user=budget_section
    )

    # create the table
    loans_tbl_div = html.Div(
        [
            dag.AgGrid(
                id="grid-assets",
                rowData=loans_df.to_dict("records"),
                columnDefs=dash_formats.get_column_defs(loans_df),
            )
        ]
    )

    return loans_tbl_div


@callback(
    [Input("assets-retrieve-button", "n_clicks")],
    prevent_initial_call=True,
)
def retrieve_asset_values(clickData):
    """Get new asset values."""
    if clickData is None:
        return dash.no_update
    assets.update_asset_info(config_path="config.yml", db_write=True)
    return dash.no_update
