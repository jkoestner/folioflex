"""Personal dashboard."""

import datetime

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from dateutil.relativedelta import relativedelta
from flask_login import current_user

from folioflex.budget import budget, models
from folioflex.dashboard.utils import dashboard_helper
from folioflex.utils import custom_logger

logger = custom_logger.setup_logging(__name__)

dash.register_page(__name__, path="/budget", title="folioflex - Budget", order=5)

# get the prior month
prior_month = (datetime.datetime.now() - relativedelta(months=1)).strftime("%Y-%m")


#   _                            _
#  | |    __ _ _   _  ___  _   _| |_
#  | |   / _` | | | |/ _ \| | | | __|
#  | |__| (_| | |_| | (_) | |_| | |_
#  |_____\__,_|\__, |\___/ \__,_|\__|
#              |___/


def layout():
    """Create layout for the personal dashboard."""
    if not current_user.is_authenticated:
        return html.Div(["Please ", dcc.Link("login", href="/login"), " to continue"])
    return html.Div(
        [
            # adding variables needed that are used in callbacks.
            *dashboard_helper.get_defaults(),
            # ---------------------------------------------------------------
            dbc.Row(
                [
                    dbc.Col(
                        html.Label("Date (YYYY-MM)"),
                        width="auto",
                    ),
                    dbc.Col(
                        dcc.Input(
                            id="budget-chart-input",
                            value=prior_month,
                            type="text",
                        ),
                        width="auto",
                    ),
                ]
            ),
            # budget chart
            dbc.Row(
                [
                    dbc.Col(
                        html.Button("Budget Chart", id="budget-chart-button"),
                        width="auto",
                    ),
                    dbc.Col(
                        html.Button(
                            "Update Budget Database",
                            id="budget-update-db-button",
                        ),
                        width="auto",
                    ),
                ]
            ),
            dcc.Graph(
                id="budget-chart",
            ),
            html.Div(id="budget-chart-labels", children=""),
            dbc.Toast(
                "Updated database tables.",
                id="toast-update-db",
                header="Updated Database",
                is_open=False,
                dismissable=True,
                icon="success",
            ),
            # income chart
            dbc.Col(
                html.Button("Income Chart", id="income-chart-button", n_clicks=0),
            ),
            dcc.Graph(
                id="income-chart",
            ),
            # compare chart
            dbc.Col(
                html.Button("Compare Chart", id="budget-compare-button", n_clicks=0),
            ),
            dcc.Graph(
                id="compare-chart",
            ),
        ]
    )


#    ____      _ _ _                _
#   / ___|__ _| | | |__   __ _  ___| | _____
#  | |   / _` | | | '_ \ / _` |/ __| |/ / __|
#  | |__| (_| | | | |_) | (_| | (__|   <\__ \
#   \____\__,_|_|_|_.__/ \__,_|\___|_|\_\___/


# budget expense chart
@callback(
    [
        Output("budget-chart", "figure"),
        Output("budget-chart-labels", "children"),
    ],
    [Input("budget-chart-button", "n_clicks")],
    [State("budget-chart-input", "value")],
    prevent_initial_call=True,
)
def update_budgetchart(n_clicks, input_value):
    """Provide budget info chart."""
    bdgt = budget.Budget(config_path="budget_personal.ini", budget="personal")
    budget_df = bdgt.get_transactions()
    budget_df = bdgt.modify_transactions(budget_df)
    budget_view = bdgt.budget_view(
        budget_df, target_date=input_value, exclude_labels=["income"]
    )
    budget_chart = bdgt.display_budget_view(budget_view)
    len_label = len(budget_df[~budget_df["label"].isnull()])
    len_unlabel = len(budget_df[budget_df["label"].isnull()])

    return budget_chart, f"Labeled: {len_label} | Unlabeled: {len_unlabel}"


# income chart
@callback(
    Output("income-chart", "figure"),
    [Input("income-chart-button", "n_clicks")],
    [State("budget-chart-input", "value")],
    prevent_initial_call=True,
)
def update_incomeview(n_clicks, input_value):
    """Provide income info chart."""
    bdgt = budget.Budget(config_path="budget_personal.ini", budget="personal")
    budget_df = bdgt.get_transactions()
    budget_df = bdgt.modify_transactions(budget_df)
    income_chart = bdgt.display_income_view(budget_df)

    return income_chart


# budget compare chart
@callback(
    Output("compare-chart", "figure"),
    [Input("budget-compare-button", "n_clicks")],
    [State("budget-chart-input", "value")],
    prevent_initial_call=True,
)
def update_comparechart(n_clicks, input_value):
    """Provide budget compare info chart."""
    bdgt = budget.Budget(config_path="budget_personal.ini", budget="personal")
    budget_df = bdgt.get_transactions()
    budget_df = bdgt.modify_transactions(budget_df)
    compare_chart = bdgt.display_compare_expenses_view(
        budget_df, target_date=input_value, avg_months=3
    )

    return compare_chart


# update budget db
@callback(
    Output("toast-update-db", "is_open"),
    [Input("budget-update-db-button", "n_clicks")],
    prevent_initial_call=True,
)
def update_budget_db(n_clicks):
    """Provide budget compare info chart."""
    # get the unlabeled transactions
    bdgt = budget.Budget(config_path="budget_personal.ini", budget="personal")
    budget_df = bdgt.get_transactions()
    train_df = budget_df[~budget_df["label"].isna()]
    unlabeled_df = budget_df[budget_df["label"].isna()]

    # use trained model to predict labels
    model = models.Classifier(train_df=train_df)
    model.load_model(model_name="components.pkl")
    predict_df = model.predict_labels(
        unlabeled_df=unlabeled_df, components=model.components
    )

    # update the database with the predicted labels
    bdgt.update_labels_db(tx_df=predict_df, label_column="predicted_label")

    return True
