from datetime import datetime
from enum import Enum

import gspread
from rich.console import Console
from rich.table import Table

from deployer.file_acquisition import get_decrypted_file


class CostTableOutputFormats(Enum):
    """
    Output formats supported by the generate-cost-table command
    """

    terminal = "terminal"
    google_sheet = "google-sheet"


def output_cost_table(output, google_sheet_url, rows):
    """
    Writes rows to output
    Args:
        rows: pandas.DataFrame of {
                    "month": period,
                    "project": r.project,
                    "total_with_credits": float(r.total_with_credits),
                }
    """
    last_period = None

    if output == CostTableOutputFormats.google_sheet:
        # A service account (https://console.cloud.google.com/iam-admin/serviceaccounts/details/113674037014124702779?project=two-eye-two-see)
        # It is created with no permissions, and the google sheet we want to write to
        # must give write permissions to the email account for the service account
        # In this case, it is  billing-spreadsheet-writer@two-eye-two-see.iam.gserviceaccount.com .
        with get_decrypted_file(
            "config/secrets/enc-billing-gsheets-writer-key.secret.json"
        ) as f:
            gsheets = gspread.service_account(filename=f)

        spreadsheet = gsheets.open_by_url(google_sheet_url)
        worksheet = spreadsheet.get_worksheet(0)
        worksheet.clear()

        worksheet.append_row(
            [
                "WARNING: Do not manually modify, this sheet is autogenerated by the generate-cost-table subcommand of the deployer"
            ]
        )
        worksheet.append_row([f"Last Updated: {datetime.utcnow().isoformat()}"])

        worksheet.append_row(
            [
                "Period",
                "Project",
                "Cost (after Credits)",
            ]
        )

        worksheet.append_rows(
            [
                [
                    index.strftime("%Y-%m"),
                    r["project"],
                    round(float(r["total_with_credits"]), 2),
                ]
                for index, r in rows.iterrows()
            ]
        )
    else:
        table = Table(title="Project Costs")

        table.add_column("Period", justify="right", style="cyan", no_wrap=True)
        table.add_column("Project", style="white")
        table.add_column("Cost (after credits)", justify="right", style="green")

        # Note JSON serialization that gspread uses doesn't support decimal.Decimal so use floats below.
        for index, r in rows.iterrows():
            if last_period != None and index != last_period:
                table.add_section()
            table.add_row(
                index.strftime("%Y-%m"),
                r["project"],
                round(float(r["total_with_credits"]), 2),
            )
            last_period = index

        console = Console()
        console.print(table)
