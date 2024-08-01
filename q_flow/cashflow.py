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
from q_flow.models.activity import Activity
from matplotlib import pyplot as plt
from asciichartpy import plot
from prettytable import PrettyTable

from q_flow.models.project import Project

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
            if t <=  self.d:
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

class Project_cf():
    def __init__(self, project: Project) -> None:
        self.project = project
        self.work_cf = []
        self.outflow_cf = []

        work_dur = []
        work_total = []
        out_dur = []
        out_total = []
        activity: Activity
        activities = project.activities
        for activity in activities:
            if not activity.cash_flow_json:
                activity_cf = Activity_cf(activity)
                activity.cash_flow_json = {}
                activity.cash_flow_json.update(activity_cf.marginal_work_as_json())
                activity.cash_flow_json.update(activity_cf.out_flow_as_json())
            activity_cf_json = activity.cash_flow_json
            activity_work: list = activity_cf_json.get("marginal_work")
            activity_outflow: list = activity_cf_json.get("marginal_out_flow")
            # # adjust for start
            # for _ in range(0, activity.start):
            #     activity_work.insert(0, 0)
            #     activity_outflow.insert(0, 0)
            # project cashflow matrix
            self.work_cf.append(activity_work)
            self.outflow_cf.append(activity_outflow)
            work_dur.append(len(activity_work))
            work_total.append(sum(activity_work))
            out_dur.append(len(activity_outflow))
            out_total.append(sum(activity_outflow))

        self.duration = max(work_dur)
        self.cost = sum(work_total)

    def factored_work(self) -> list:
        '''
        this method calculates the inflow for the project. It sums the cashflow
        of all activities and adjusts for the contract value.
        '''
        t_work = [sum(n) for n in zip_longest(*self.work_cf, fillvalue=0)]
        factor = self.project.contract_value / self.cost
        t_work = [n * factor for n in t_work]
        return t_work

    def inflow(self) -> list:
        '''
        This method calculates the inflow considering:
        1. advance payment
        2. retention
        3. dlp
        4. duration for payment
        5. release retention at eop
        6. release retention at dlp
        7. activity work
        '''
        inflow = []
        # add advance payment
        inflow.append(self.project.advance * self.project.contract_value)

        # add 0 for the duration for payment
        for _ in range(0, self.project.duration_for_payment):
            inflow.append(0)

        # add the factored work
        previous_work = 0
        for work in self.factored_work():
            bill_work = work *(1 - self.project.wieb) + previous_work * self.project.wieb
            previous_work = work
            inflow.append((1-(self.project.advance + self.project.retention)) * bill_work)
        inflow.append(
            (1-(self.project.advance + self.project.retention)) * previous_work * self.project.wieb)

        # add retention release at eop as per contract
        inflow[-1] += self.project.retention * self.project.contract_value * self.project.release_retention_eop

        # add zeros for the dlp
        for _ in range(1, self.project.dlp):
            inflow.append(0)

        # add retention release at dlp as per contract
        inflow.append(self.project.retention * self.project.contract_value * (1 - self.project.release_retention_eop))
        return inflow

    def outflow(self) -> list:
        '''
        This method calculates the outflow for the project. It sums the cashflow
        of all activities and adjusts for the contract value.
        '''
        outflow = [sum(n) for n in zip_longest(*self.outflow_cf, fillvalue=0)]
        return outflow

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
        table.add_row(["Cost", self.cost])
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

class Activity_cf():
    '''
    Given an Activity Object, this class will generate the cashflow for the
    activity. It will generate the following cashflow's:
    1. Marginal Work
    2. Cumulative Work
    3. Subcontractor Bill Work
    4. Subcontractor Payments
    5. Non Subcontractor Payments
    6. Outflow

    Definition of terms:
    
    no_billing_period: This variable specifies the number of periods for which
    the subcontractor will not issue invoices. After this period concludes,
    the subcontractor will bill for all work completed during this time. It’s
    important to set this period accurately; if it’s shorter than the no work
    period (mobilization period), it will not affect billing because no billable
    work occurs during the mobilization period.

    no_work_period (previously mobilization period): This period is when the 
    subcontractor prepares for the main work but does not perform any billable 
    activities on site. Therefore, no invoices are issued during this time. 
    If the contract includes an advance payment, it will be provided at the 
    beginning of this period. The actual billable work begins after the no work 
    period ends.

    duration_for_payment: This is the timeframe within which the subcontractor 
    is paid after issuing an invoice. It is crucial for managing cash flow and
    payment expectations.

    start: This is the commencement date of the subcontractor’s activities, 
    marking the beginning of the no work period. Billable work will only begin 
    once this period is over, so it’s essential that this date is set with 
    precision to ensure accurate scheduling and billing.
    '''
    def __init__(self, activity: Activity) -> None:
        self.activity = activity
        if activity.activity_type == "linear":
            self.work = Work(
                self.activity.duration, self.activity.skew, self.activity.cost, "l")
        else:
            self.work = Work(
                self.activity.duration, self.activity.skew, self.activity.cost)
        self.marginal_work = self.work.marginal_work()

        # add 0's for mobilization period
        for _ in range(0, self.activity.mobilization_period):
            self.marginal_work.insert(0, 0)

    def subcontractor_bill_work(self) -> list:
        '''
        From the marginal work, this method calculates the work that will be
        billed by the subcontractor. result is marginal
        '''
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

        # return 50% of retention
        value_of_retention = self.activity.cost * self.activity.subcontracted * \
            self.activity.retention
        sub_payments[-1] += value_of_retention * self.activity.release_retention_eop

        # return the remaining 50% of retention at the end of dlp
        for _ in range(1, self.activity.dlp):
            sub_payments.append(0.0)
        sub_payments[-1] += value_of_retention * (1-self.activity.release_retention_eop)
        return sub_payments

    def non_sub_payments(self) -> list:
        '''
        this method uses the marginal work list to calculate the payments that
        will be made to the non subcontractors. result is marginal.
        '''
        non_sub_payments = []
        m_work = self.marginal_work
        # add zero to period 1 --- removed
        # non_sub_payments.append(0)
        # pay all bills
        for t in range(0, len(m_work)):
            non_sub_payments.append(m_work[t] * (1-self.activity.subcontracted))

        return non_sub_payments

    def out_flow(self) -> list:
        '''
        this method calculates the total outflow for the activity. It sums the
        subcontractor payments and the non subcontractor payments. result is
        marginal.
        '''
        sub_payments = self.sub_payments()
        non_sub_payments = self.non_sub_payments()
        outflow = [sum(n) for n in zip_longest(
            sub_payments, non_sub_payments, fillvalue=0)]
        return outflow

    def marginal_work_as_json(self):
        # adjust for start
        m_work = [] 
        for _ in range(0, self.activity.start):
            m_work.insert(0, 0.0)
        m_work.extend(self.marginal_work)
        return {
            "marginal_work": m_work,
        }

    def out_flow_as_json(self):
        # adjust for start
        out = []
        for _ in range(0, self.activity.start):
            out.insert(0, 0.0)
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
        wr = cf.work.marginal_work()
        cw = cf.work.cumulative_work()
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
        total_length = max([len(wr), len(cw), len(out), len(sub), len(sub_pay)])
        for m in range(total_length):
            month = m+1
            # Always show two decimal places for value
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
            # create a a line plot x-axis is month and y-axis is outflow
            fig, ax = plt.subplots(facecolor="black")
            ax.set_facecolor("black")
            ax.bar(range(1, len(out)+1), out, color="green", align="center", alpha=0.5)
            ax.set_xlabel("Month", color="green")
            ax.set_ylabel("Outflow", color="green")
            ax.set_title("Outflow", color="green")
            # Set the text color of labels to white
            for text in ax.texts:
                text.set_color('white')
            ax.tick_params(axis='both', colors='white')
            plt.show()
        
        if with_text_chart:
            data = [out]
            p = plot(data, cfg={'height': 20})
            click.echo(p)
            
            # plot the cumulative for the outflow
            p = plot([cum_out], cfg={'height': 20})
            click.echo(p)
            # click.echo(wr)

    def printActivity(self):
        click.echo(click.style("\n\n**** Activity Parameters (red == not specified) ****", fg="blue"))
        table = PrettyTable(["Parameter", "Value"])
        print(self.activity.id)
        print(self.activity.name)
        table.add_row(["Start", self.activity.start])
        table.add_row(["Duration", self.activity.duration])
        table.add_row(["Cost", self.activity.cost])
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