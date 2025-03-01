"""Components - dash formats."""

from folioflex.utils import custom_logger

logger = custom_logger.setup_logging(__name__)


def get_column_defs(table, edit=None):
    """
    Get the column definitions.

    Parameters
    ----------
    table : pd.DataFrame
        The table
    edit : list
        The list of columns that can be edited

    Returns
    -------
    column_defs : list
        The column definitions

    """
    if edit is None:
        edit = []
    column_defs = []
    for col in table.columns:
        if col in edit:
            editable = True
        else:
            editable = False
        # specific case for columns
        if any(substring in col.lower() for substring in ["amount", "current_balance"]):
            column_defs.append(
                {
                    "field": col,
                    "headerName": col,
                    "valueFormatter": {"function": "d3.format(',.2f')(params.value)"},
                    "editable": editable,
                }
            )
        # update integer columns
        elif table[col].dtype.kind in "i":
            if any(substring in col.lower() for substring in ["year", "id"]):
                column_defs.append(
                    {
                        "field": col,
                        "headerName": col,
                        "valueFormatter": {"function": "d3.format('d')(params.value)"},
                        "editable": editable,
                    }
                )
            else:
                column_defs.append(
                    {
                        "field": col,
                        "headerName": col,
                        "valueFormatter": {"function": "d3.format(',')(params.value)"},
                        "editable": editable,
                    }
                )
        # update float columns
        elif table[col].dtype.kind in "f":
            if any(substring in col.lower() for substring in ["pct"]):
                column_defs.append(
                    {
                        "field": col,
                        "headerName": col,
                        "valueFormatter": {
                            "function": "d3.format('.2%')(params.value)"
                        },
                        "editable": editable,
                    }
                )
            else:
                column_defs.append(
                    {
                        "field": col,
                        "headerName": col,
                        "valueFormatter": {
                            "function": "d3.format(',.1f')(params.value)"
                        },
                        "editable": editable,
                    }
                )
        # update other types
        else:
            column_defs.append(
                {
                    "field": col,
                    "headerName": col,
                    "editable": editable,
                }
            )
    return column_defs


def remove_column_defs(column_defs, col_name):
    """
    Remove a column from the column definitions.

    Parameters
    ----------
    column_defs : list
        The column definitions
    col_name : str
        The column name to remove

    Returns
    -------
    column_defs : list
        The column definitions

    """
    for col in column_defs:
        if col["field"] == col_name:
            column_defs.remove(col)
    return column_defs
