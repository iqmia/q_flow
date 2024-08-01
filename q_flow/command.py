import click
from flask.cli import with_appcontext
from q_flow.models.activity import Activity
from q_flow.cashflow import Activity_cf
import random

@click.command("createcf")
@click.option("--duration", "-d", help="The duration of the cashflow")
@click.option("--cost", "-c", help="The cost of the cashflow")
@click.option("--skew", "-skw", help="The skew of the cashflow")
@click.option("--subcontracted", "-sc", help="The subcontracted of the cashflow")
@click.option("--advance", "-adv", help="The advance of the cashflow")
@click.option("--name", "-n", help="The name of the cashflow")
@click.option("--type", "-t", help="The type of the cashflow")
@click.option("--no_billing", "-nbp", help="The no-billing-period of the cashflow")
@click.option("--duration_for_payment", "-dfp", help="The duration-for-payment of the cashflow")
@click.option("--dlp", "-dlp", help="The dlp of the cashflow")
@click.option("--retention", "-ret", help="The retention of the cashflow")
@click.option("--work_in_excess", "-wib", help="The work-in-excess of the cashflow")
@with_appcontext
def create_cf(
    duration: int, cost: float, skew: float, no_billing: int, dlp: int,
    duration_for_payment: int, retention: float, work_in_excess: float,
    subcontracted: float, advance=None, name=None, type=None):
    '''
    This function generates a new cashflow and prints it to the screen
    required parameters: duration, cost, skew
    optional parameters: name, type
    '''
    click.echo("create_cf called")
    assert duration not in [None, ""], "duration is required"
    assert cost not in [None, ""], "cost is required"
    activity = Activity(
        duration=int(duration),
        cost=float(cost),
        skew=float(skew or 0.0),
        name=name,
        subcontracted=float(subcontracted or 0.0),
        advance=float(advance or 0.0),
        no_billing_period=int(no_billing or 0),
        retention=float(retention or 0.0),
        work_in_excess=float(work_in_excess or 0.0),
        duration_for_payment=int(duration_for_payment or 0),
        dlp=int(dlp or 0),
        activity_type=type
    )
    cashflow = Activity_cf(activity)
    cashflow.printActivity()
    cashflow.printCashFlow(with_chart=True, with_text_chart=True, detailed=True)

def random_type():
    types = ["critical", "non-critical", "normal", ""]
    return random.choice(types)
