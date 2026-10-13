'''
How to use the cashflow class:
1. Create a project object
2. Create activities for the project
3. The following 2 steps are usually done when activity is saved
    a. Create an Activity_cf object for each activity
    b. Generate the cashflow for each activity
    c. save the activity work and outflow in filed cashflowJson
    d. the cashflowJson field is a dictionary with keys: marginal_work, marginal_out_flow
5. Create a Project_cf object for the project
6. Generate the inflow for the project
7. Generate the outflow for the project
'''

from itertools import zip_longest
from math import exp
from re import sub

import click
from q_flow.models.activity import (
    Activity,
    effective_activity_mode,
    effective_distribution_type,
)
from matplotlib import pyplot as plt
from asciichartpy import plot
from prettytable import PrettyTable

from q_flow.models.cashflow import Cashflow


class Work():
    def __init__(self, d, s, c, ct="s") -> None:
        '''
        d: Duration
        s: Skewing factor between -0.9 and +0.9
        c: Cost
        ct: "s" for sigmoid and "l" for linear
        '''
        self.d = d
        self.s = s
        self.c = c
        self.ct = ct

    def __skewed(self, t):
        '''
        this method will return the total work performed at time (t) for a
        project with cost (c), duration (d) and skewing factor (s)
        '''
        # conditions
        assert self.s > -1 and self.s < 1
        assert t >= 0 and t <= self.d

        if self.ct == "l":
            return self.c/self.d * t
        return self.c*(self.s+1)/(
            (self.s+1)+exp(
                -(t/(0.1*self.d)+self.s**2-5)
            )
        )

    def __raw_cumulative_work(self) -> list:
        '''
        This method returns the cumulative work performed at each unit of time
        if uses the skewed method without adjusting for error.
        d: duration
        s: skew (-0.9, 0.9)
        c: cost
        '''
        t_work = []
        for t in range(0, self.d + 1):
            t_work.append(self.__skewed(t))
        return t_work

    def marginal_work(self) -> list:
        '''
        This method uses the raw cumulative work to calculate the marginal work
        from S curve to sigmoid curve. It adjusts for error in the work performed
        '''
        m_work = []
        t_work = self.__raw_cumulative_work()
        for t in range(0, self.d):
            if t <= self.d:
                m_work.append(t_work[t+1] - t_work[t])

        # calculate the error
        er = self.c - sum(m_work)

        # apply third degree polynomial to distribute the error
        # the error should be distributed over the duration of the activity
        # on the cumulative work.
        d = self.d
        for t in range(0, d + 1):
            error_dist = -(2*er*t**3)/(d**3) + (3*er*t**2)/(d**2)
            t_work[t] = t_work[t] + error_dist

        adjusted_m_work = []
        for t in range(0, d):
            if t <= d:
                adjusted_m_work.append(t_work[t+1] - t_work[t])

        return adjusted_m_work

    def cumulative_work(self) -> list:
        '''
        this method uses the error adjusted marginal work to create a new
        cumulative S curve.
        '''
        d = self.d
        mWork = self.marginal_work()
        t_work = [mWork[0]]
        for t in range(1, d):
            t_work.append(mWork[t] + t_work[t-1])
        return t_work


class CashflowCalculator():
    def __init__(self, project: Cashflow) -> None:
        self.project = project
        # Work is intentionally limited to physical/work activities. Outflow
        # includes every activity, including scheduled costs.
        self.work_cf = []
        self.outflow_cf = []
        self.activity_cashflows = {}

        for activity in project.activities:
            if activity.is_deleted:
                continue
            activity_cf = Activity_cf(activity)
            activity_work = activity_cf.marginal_work_as_json()["marginal_work"]
            activity_outflow = activity_cf.out_flow_as_json()["marginal_out_flow"]
            if effective_activity_mode(activity) == "work":
                self.work_cf.append(activity_work)
            self.outflow_cf.append(activity_outflow)
            self.activity_cashflows[activity.id] = {
                "marginal_work": self._round_flow(activity_work),
                "marginal_out_flow": self._round_flow(activity_outflow),
            }

        self.duration = max((len(work) for work in self.work_cf), default=0)
        self.work_cost = sum(sum(work) for work in self.work_cf)
        # Compatibility alias: historically calculator.cost was the denominator
        # used to scale activity-linked work to contract value.
        self.cost = self.work_cost

    @staticmethod
    def _round_flow(flow: list) -> list:
        rounded = [round(float(value), 2) for value in flow]
        return [0.0 if value == 0 else value for value in rounded]

    def workflow(self) -> list:
        return [sum(values) for values in zip_longest(
            *self.work_cf, fillvalue=0)]

    def factored_work(self) -> list:
        """Scale work-activity cost to the contract value."""
        t_work = self.workflow()
        if not t_work:
            return []
        if self.work_cost == 0:
            return [0.0 for _ in t_work]
        factor = self.project.contract_value / self.work_cost
        return [value * factor for value in t_work]

    def independent_contract_work(self) -> list:
        """Generate contract-value work independently over work duration."""
        if not self.work_cf or self.duration <= 0:
            return []

        curve_type = getattr(self.project, "inflow_curve_type", None)
        if curve_type == "linear":
            work_type = "l"
        elif curve_type == "s_curve":
            work_type = "s"
        else:
            raise ValueError(f"Unsupported inflow curve type: {curve_type}")

        skew = getattr(self.project, "inflow_curve_skew", 0.0)
        if skew is None:
            skew = 0.0

        return Work(
            self.duration,
            skew,
            self.project.contract_value,
            work_type,
        ).marginal_work()

    def contract_work(self) -> list:
        """Return the selected contract-value work series for client billing."""
        if (
            getattr(self.project, "use_independent_inflow_curve", None) is True
            and getattr(self.project, "inflow_curve_type", None) is not None
        ):
            return self.independent_contract_work()
        return self.factored_work()

    def inflow(self) -> list:
        """Calculate client receipts from work, payment terms, and retention."""
        t_work = self.contract_work()
        if not t_work:
            return []

        payment_factor = (
            1 - self.project.advance - self.project.retention
        )

        # Period zero always exists so payment delay has the same meaning
        # whether or not an advance payment is present. A delay of N moves
        # progress receipts exactly N periods after the billed work.
        inflow = [0.0 for _ in range(self.project.duration_for_payment + 1)]
        inflow[0] += self.project.advance * self.project.contract_value

        # WIEB is the share of each period's work billed in the next period.
        # It therefore applies from the first work period, not only from the
        # second period onward.
        previous_work = t_work[0]
        first_bill_work = t_work[0] * (1 - self.project.wieb)
        inflow[self.project.duration_for_payment] += (
            payment_factor * first_bill_work
        )

        for work in t_work[1:]:
            bill_work = (
                work * (1 - self.project.wieb)
                + previous_work * self.project.wieb
            )
            previous_work = work
            inflow.append(payment_factor * bill_work)

        # Carry the final WIEB balance into the following billing period.
        inflow.append(
            payment_factor * previous_work * self.project.wieb
        )

        value_of_retention = (
            self.project.retention * self.project.contract_value
        )
        inflow[-1] += (
            value_of_retention * self.project.release_retention_eop
        )

        remaining_retention = (
            value_of_retention * (1 - self.project.release_retention_eop)
        )
        if self.project.dlp == 0:
            inflow[-1] += remaining_retention
        else:
            for _ in range(1, self.project.dlp):
                inflow.append(0.0)
            inflow.append(remaining_retention)

        return inflow

    def ppc_base(self) -> list:
        """Return client PPC receipts, excluding advance and retention releases."""
        receipts = self.inflow()
        if not receipts:
            return []

        receipts[0] -= self.project.advance * self.project.contract_value
        retention = self.project.retention * self.project.contract_value
        if self.project.dlp == 0:
            receipts[-1] -= retention
        else:
            receipts[-1] -= retention * (1 - self.project.release_retention_eop)
            eop_period = len(receipts) - self.project.dlp - 1
            if eop_period >= 0:
                receipts[eop_period] -= retention * self.project.release_retention_eop
        return [max(0.0, value) for value in receipts]

    def ppc_issued(self) -> list:
        """Return net PPC values in certificate periods, before payment delay."""
        work = self.contract_work()
        if not work:
            return []

        payment_factor = 1 - self.project.advance - self.project.retention
        billed_work = [work[0] * (1 - self.project.wieb)]
        previous_work = work[0]
        for period_work in work[1:]:
            billed_work.append(
                period_work * (1 - self.project.wieb)
                + previous_work * self.project.wieb
            )
            previous_work = period_work
        billed_work.append(previous_work * self.project.wieb)
        return [value * payment_factor for value in billed_work]

    def outflow(self) -> list:
        """Sum all current activity outflows by period."""
        return [sum(values) for values in zip_longest(
            *self.outflow_cf, fillvalue=0)]

    def snapshot(self) -> dict:
        workflow = self.workflow()
        inflow = self.inflow()
        outflow = self.outflow()

        if not workflow and not outflow:
            empty_snapshot = {
                "workflow": [],
                "inflow": [],
                "outflow": [],
                "netflow": [],
                "outflow_with_interest": [],
                "duration": 0,
            }
            if getattr(self.project, "financing_facilities", None):
                return self._apply_facilities(empty_snapshot)
            return empty_snapshot

        netflow = [
            incoming - outgoing
            for incoming, outgoing in zip_longest(
                inflow, outflow, fillvalue=0
            )
        ]

        balance = 0.0
        outflow_with_interest = []
        for amount in netflow:
            if balance + amount < 0:
                balance = (balance + amount) * (1 + self.project.interest_rate)
            else:
                balance += amount
            outflow_with_interest.append(balance)

        snapshot = {
            "workflow": self._round_flow(workflow),
            "inflow": self._round_flow(inflow),
            "outflow": self._round_flow(outflow),
            "netflow": self._round_flow(netflow),
            "outflow_with_interest": self._round_flow(outflow_with_interest),
            "duration": self.duration,
        }
        if getattr(self.project, "financing_facilities", None):
            return self._apply_facilities(snapshot)
        return snapshot

    def _apply_facilities(self, snapshot):
        from q_flow.financing import calculate_financing

        result = calculate_financing(
            inflows=snapshot["inflow"],
            outflows=snapshot["outflow"],
            ppc_base=self._round_flow(self.ppc_base()),
            ppc_issued=self._round_flow(self.ppc_issued()),
            facilities=self.project.financing_facilities or [],
        )
        snapshot.update({
            "facility_rows": result["facilities"],
            "facility_inflow": result["facility_draws"],
            "facility_outflow": result["principal_repayments"],
            "facility_interest": result["facility_interest"],
            "facility_fees": result["facility_fees"],
            "funded_netflow": result["net_cash_flow"],
            "pre_financing_balance": result["pre_financing_balance"],
            "unfunded_shortfall": result["unfunded_shortfall"],
            "outflow_with_interest": result["funded_cash_balance"],
        })
        return snapshot

    def print_project_cashflow(self):
        cf = self
        inflow = cf.inflow()
        outflow = cf.outflow()
        table = PrettyTable(["Month", "Inflow", "Outflow"])
        table.align = "r"
        sum_inflow = click.style(str("%0.2f" % round(sum(inflow), 2)), fg="blue")
        sum_outflow = click.style(str("%0.2f" % round(sum(outflow), 2)), fg="blue")
        total_length = max([len(inflow), len(outflow)])
        for m in range(total_length):
            month = m+1
            inflow_value = "%0.2f" % round(inflow[m], 2) if m < len(inflow) else ""
            outflow_value = "%0.2f" % round(outflow[m], 2) if m < len(outflow) else ""
            table.add_row([month, inflow_value, outflow_value], divider=(True if m == total_length - 1 else False))
        table.add_row(["Total", sum_inflow, sum_outflow])
        click.echo(table)

    def printProject(self):
        click.echo(click.style("\n\n**** Project Parameters (red == not specified) ****", fg="blue"))
        table = PrettyTable(["Parameter", "Value"])
        table.add_row(["Name", self.project.name])
        table.add_row(["Description", self.project.description])
        table.add_row(["Advance", self.project.advance])
        table.add_row(["Retention", self.project.retention])
        table.add_row(["Release Retention EOP", self.project.release_retention_eop])
        table.add_row(["DLP", self.project.dlp])
        table.add_row(["Duration for Payment", self.project.duration_for_payment])
        table.add_row(["Interest Rate", self.project.interest_rate])
        table.add_row(["Contract Value", self.project.contract_value])
        table.add_row(["WIEB", self.project.wieb])
        table.add_row(["Work Cost", self.work_cost])
        table.align = "l"
        click.echo(table)

    def print_gantt(self):
        '''
        This method will print the gantt chart for the project. It will show the
        start and end of each activity and the total duration of the project.
        '''
        click.echo(click.style("\n\n**** Project Gantt Chart ****", fg="blue"))
        table = PrettyTable(["Activity", "Start", "End", "Duration"])
        table.align = "l"
        for activity in self.project.activities:
            table.add_row([activity.name, activity.start, activity.start + activity.duration, activity.duration])
        table.add_row(["Project", 1, self.duration, self.duration])
        click.echo(table)


# Compatibility for older integrations while callers move to the clearer name.
Project_cf = CashflowCalculator


class Activity_cf():
    '''
    Given an Activity Object, this class will generate the cashflow for the
    activity. Work activities may use a generated S-curve, generated linear
    curve, or a manual dense marginal schedule. Scheduled-cost activities
    produce direct outflow without creating physical/billable work.
    '''
    def __init__(self, activity: Activity) -> None:
        self.activity = activity
        self.activity_mode = effective_activity_mode(activity)
        self.distribution_type = effective_distribution_type(activity)
        self.work = None

        if self.activity_mode == "scheduled_cost":
            schedule = self.activity.cost_schedule_json or []
            self.marginal_work = [0.0 for _ in schedule]
            return

        if self.distribution_type == "manual":
            self.marginal_work = [
                float(value) for value in (self.activity.cost_schedule_json or [])
            ]
        else:
            work_type = "l" if self.distribution_type == "linear" else "s"
            self.work = Work(
                self.activity.duration,
                self.activity.skew,
                self.activity.cost,
                work_type,
            )
            self.marginal_work = self.work.marginal_work()

        # Pre-work/no-work periods are part of the existing work pipeline and
        # therefore apply equally to generated and manual work distributions.
        for _ in range(0, self.activity.mobilization_period):
            self.marginal_work.insert(0, 0.0)

    def subcontractor_bill_work(self) -> list:
        '''
        From the marginal work, this method calculates the work that will be
        billed by the subcontractor. result is marginal
        '''
        if self.activity_mode != "work":
            return []

        sub_bill_work = []
        m_work = self.marginal_work
        no_work = self.activity.mobilization_period
        no_bill = self.activity.no_billing_period

        # fill zeros for the no billing period
        for _ in range(0, no_bill):
            sub_bill_work.append(0)

        # add the first bill after the no billing period which is the sum of the
        # work performed during the no billing period
        first_bill_work = 0
        if no_bill > 0:
            first_bill_work = sum(m_work[0:(no_bill + 1)]) * self.activity.subcontracted
        else:
            first_bill_work = m_work[0] * self.activity.subcontracted
        sub_bill_work.append(first_bill_work)

        # remaining bill work:
        for t in range(no_bill + 1, self.activity.duration + no_work):
            sub_bill_work.append(m_work[t]*self.activity.subcontracted)

        # WIEB: work in excess of billing
        # adjust for WIEB work_in_excess of billing. this is the work that is
        # billed in the next billing period
        adjusted_sub_bill_work = []
        for t in range(0, len(sub_bill_work) + 1):
            if t == 0:
                adjusted_work = (sub_bill_work[t] * \
                    (1 - self.activity.work_in_excess))
            elif t == len(sub_bill_work):
                adjusted_work = (sub_bill_work[t-1] * \
                    self.activity.work_in_excess)
            else:
                adjusted_work = (
                    sub_bill_work[t] * (1 - self.activity.work_in_excess)
                    + sub_bill_work[t-1] * self.activity.work_in_excess
                )
            # adjust for retention and advance recovery
            adjusted_sub_bill_work.append(adjusted_work * \
                (1 - self.activity.retention - self.activity.advance))

        return adjusted_sub_bill_work

    def sub_payments(self) -> list:
        '''
        Having the subcontractor bill work, this method calculates the payments
        that will be made to the subcontractor. result is marginal.
        '''
        if self.activity_mode != "work":
            return []

        sub_payments = []
        sub_bill_work = self.subcontractor_bill_work()

        # add zeros to the duration_for_payment
        for _ in range(0, self.activity.duration_for_payment):
            sub_payments.append(0.0)

        # add remaining payments
        for payment in sub_bill_work:
            sub_payments.append(payment)

        # add advance payment
        sub_payments[0] = sub_payments[0] + self.activity.advance * self.activity.cost * self.activity.subcontracted

        # return first portion of retention
        value_of_retention = self.activity.cost * self.activity.subcontracted * \
            self.activity.retention
        sub_payments[-1] += value_of_retention * self.activity.release_retention_eop

        # Return the remaining retention exactly dlp periods after the
        # end-of-project release. With dlp == 0, both portions are released in
        # the same end period.
        remaining_retention = (
            value_of_retention * (1 - self.activity.release_retention_eop)
        )
        if self.activity.dlp == 0:
            sub_payments[-1] += remaining_retention
        else:
            for _ in range(1, self.activity.dlp):
                sub_payments.append(0.0)
            sub_payments.append(remaining_retention)
        return sub_payments

    def non_sub_payments(self) -> list:
        '''
        this method uses the marginal work list to calculate the payments that
        will be made to the non subcontractors. result is marginal.
        '''
        if self.activity_mode != "work":
            return []

        non_sub_payments = []
        m_work = self.marginal_work
        # pay all self-performed/direct cost as incurred
        for t in range(0, len(m_work)):
            non_sub_payments.append(m_work[t] * (1-self.activity.subcontracted))

        return non_sub_payments

    def out_flow(self) -> list:
        '''Return marginal activity outflow before the project start offset.'''
        if self.activity_mode == "scheduled_cost":
            return [
                float(value) for value in (self.activity.cost_schedule_json or [])
            ]

        sub_payments = self.sub_payments()
        non_sub_payments = self.non_sub_payments()
        return [sum(n) for n in zip_longest(
            sub_payments, non_sub_payments, fillvalue=0)]

    def marginal_work_as_json(self):
        # adjust for start
        m_work = [0.0 for _ in range(0, self.activity.start)]
        m_work.extend(self.marginal_work)
        return {
            "marginal_work": m_work,
        }

    def out_flow_as_json(self):
        # adjust for start
        out = [0.0 for _ in range(0, self.activity.start)]
        out.extend(self.out_flow())
        return {
            "marginal_out_flow": out,
        }

    def set_cashflow(self):
        '''
        This method will set the cashflow for the activity and commit it to the
        database. keys are: marginal_work, marginal_out_flow
        '''
        self.activity.cash_flow_json = {}
        self.activity.cash_flow_json.update(self.marginal_work_as_json())
        self.activity.cash_flow_json.update(self.out_flow_as_json())
        self.activity.commit()

    def printCashFlow(self, with_chart=False, with_text_chart=False, detailed=False):
        cf = self
        wr = list(cf.marginal_work)
        cw = []
        running = 0.0
        for value in wr:
            running += value
            cw.append(running)
        sub = cf.subcontractor_bill_work()
        sub_pay = cf.sub_payments()
        non_sub = cf.non_sub_payments()
        out = cf.out_flow()
        cum_out = []
        if detailed:
            table = PrettyTable(["Month", "Value", "Type", "Cumulative", "sub work", "sub pay", "non sub", "out"])
        else:
            table = PrettyTable(["Month", "Value", "out"])
        table.align = "r"
        # total of the lists
        sum_wr = click.style(str("%0.2f" % round(sum(wr), 2)), fg="blue")
        sum_sub = click.style(str("%0.2f" % round(sum(sub), 2)), fg="blue")
        sum_sub_pay = click.style(str("%0.2f" % round(sum(sub_pay), 2)), fg="blue")
        sum_out = click.style(str("%0.2f" % round(sum(out), 2)), fg="blue")
        sum_non_sub = click.style(str("%0.2f" % round(sum(non_sub), 2)), fg="blue")
        total_length = max([len(wr), len(cw), len(out), len(sub), len(sub_pay)], default=0)
        for m in range(total_length):
            month = m+1
            value = "%0.2f" % round(wr[m], 2) if m < len(wr) else ""
            outflow = "%0.2f" % round(out[m], 2) if m < len(out) else ""

            type = click.style(
                "Start" if m == 0 else "Finish" if m == len(wr) else ":", fg="green")
            cum = "%0.2f" % round(sum(out[:m+1]), 2)
            cum_out.append(sum(out[:m+1]))
            sw = "%0.2f" % round(sub[m], 2) if m < len(sub) else ""
            sp = "%0.2f" % round(sub_pay[m], 2) if m < len(sub_pay) else ""
            non_s_pay = "%0.2f" % round(non_sub[m], 2) if m < len(non_sub) else ""
            plan = ""
            if m == 0:
                cum = click.style(str(cum), fg="blue")
                plan = "Start"
            if m == len(wr)-1:
                cum = click.style(str(cum), fg="blue")
                plan = "Finish"
            if m == total_length-1:
                cum = click.style(str(cum), fg="blue")
                plan = "End DLP"

            type = click.style(plan, fg="green")
            if detailed:
                table.add_row(
                    [month, value, type, cum, sw, sp, non_s_pay, outflow],
                    divider=(True if m == total_length - 1 else False)
                )
            else:
                table.add_row([month, value, outflow], divider=(
                    True if m == total_length - 1 else False))

        if detailed:
            table.add_row(
                ["Total", sum_wr, "", "", sum_sub, sum_sub_pay, sum_non_sub, sum_out])
        else:
            table.add_row(["Total", sum_wr, sum_out])
        click.echo(table)

        if with_chart:
            fig, ax = plt.subplots(facecolor="black")
            ax.set_facecolor("black")
            ax.bar(range(1, len(out)+1), out, color="green", align="center", alpha=0.5)
            ax.set_xlabel("Month", color="green")
            ax.set_ylabel("Outflow", color="green")
            ax.set_title("Outflow", color="green")
            for text in ax.texts:
                text.set_color('white')
            ax.tick_params(axis='both', colors='white')
            plt.show()

        if with_text_chart:
            data = [out]
            p = plot(data, cfg={'height': 20})
            click.echo(p)
            p = plot([cum_out], cfg={'height': 20})
            click.echo(p)

    def printActivity(self):
        click.echo(click.style("\n\n**** Activity Parameters (red == not specified) ****", fg="blue"))
        table = PrettyTable(["Parameter", "Value"])
        print(self.activity.id)
        print(self.activity.name)
        table.add_row(["Start", self.activity.start])
        table.add_row(["Duration", self.activity.duration])
        table.add_row(["Cost", self.activity.cost])
        table.add_row(["Mode", self.activity_mode])
        table.add_row(["Distribution", self.distribution_type])
        table.add_row(["Skew", self.activity.skew])
        table.add_row(["Subcontracted", self.activity.subcontracted])
        table.add_row(["Advance", self.activity.advance])
        table.add_row(["Name", self.activity.name])
        table.add_row(["Type", self.activity.activity_type])
        table.add_row(["No Billing Period", self.activity.no_billing_period])
        table.add_row(["Duration for Payment", self.activity.duration_for_payment])
        table.add_row(["DLP", self.activity.dlp])
        table.add_row(["Retention", self.activity.retention])
        table.add_row(["Work in Excess", self.activity.work_in_excess])

        table.align = "l"
        click.echo(table)
