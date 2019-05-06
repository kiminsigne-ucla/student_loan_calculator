from bokeh.plotting import figure, output_notebook, show, ColumnDataSource, output_file
from bokeh.models import Legend, LegendItem
from bokeh.models.tools import HoverTool, BoxSelectTool, BoxZoomTool, PanTool, \
WheelZoomTool, SaveTool, ResetTool
from bokeh.models.tickers import FixedTicker
from bokeh.models.widgets import CheckboxGroup, RangeSlider, Tabs, TextInput, \
Button, RadioGroup, RadioButtonGroup, Select, Paragraph, Div, DataTable, \
TableColumn, NumberFormatter
from bokeh.layouts import column, row, WidgetBox, Spacer, gridplot
from bokeh.models import Panel, Range1d, LinearAxis
from bokeh.io import show, curdoc
import os
import pandas as pd
import numpy as np
from math import pi
from copy import deepcopy




global poverty_df

def discretionary_income(gross_income, size, region, poverty_df):

	if size > 8:
		if region == 'Alaska':
			bonus = 5530 * (size - 8)
		elif region == 'Hawaii':
			bonus = 5080 * (size - 8)
		else:
			bonus = 4420 * (size - 8)
	else:
		bonus = 0

	# 150% above poverty level
	poverty_level = poverty_df.amount[
	(poverty_df['size'] == size) &
	(poverty_df['region'] == region)].values[0] + bonus

	discretionary = gross_income - (1.5 * poverty_level)

	return discretionary


def calculate_interest(loan, interest_rate, loan_years, subsidy=0):
	# interest rate should be in decimal, not percentage
	interest_annual = loan * interest_rate
	interest = loan_years * interest_annual
	interest_paid = interest - (interest * subsidy)
	return interest_paid


# income_based_payments(202000, 0.10, 0.035, 20, 410000, 0.067, 0.50)
def income_based_payments(income, income_growth, loan_years,
loan, interest_rate, plan_type, income_percentage=0.10):
	# income percentage, income_growth and interest_rate should be in decimal, 
	# not percentage
	payment_total = 0
	income_growing = income
	loan_remaining = loan

	# REPAYE has interest subsidy, PAYE does not
	if plan_type == 'REPAYE':
		subsidy = 0.50
	else:
		subsidy = 0

	# save yearly payment info to display with Bokeh data table
	payment_month_list = []
	interest_subsidy_list = []
	payment_total_list = []
	loan_remaining_list = []
	interest_list = []
	income_list = []

	for i in range(loan_years):

		# print "Year:", i
		payment_annual = income_growing * income_percentage
		income_list.append(income_growing)
		# print "Payment annual:", payment_annual
		payment_month = payment_annual / 12.
		# print "Monthly payment:", payment_month
	
		
		if i == 0:
			payment_first_month = payment_annual / 12.

		interest_annual = min(loan, loan_remaining) * interest_rate
		interest_remaining = interest_annual - payment_annual
		

		if interest_remaining > 0 and subsidy != 0:
			# add interest subsidy, 50% from government
			interest_subsidy = interest_remaining * subsidy
			# do not add remaining unpaid interest, only add interest equal to 
			# annual payment and subsidy, so loan balance does not change
			payment_annual += interest_subsidy
			interest_list.append(payment_annual)
		else:
			interest_subsidy = 0
			loan_remaining += interest_annual
			loan_remaining -= payment_annual
			interest_list.append(interest_annual)

		# print "Interest subsidy:", interest_subsidy


		payment_total += payment_annual
		# print "Total payment:", payment_total
		
		# print "Remaining loan:", loan_remaining

		income_growing += income_growing * income_growth

		payment_month_list.append(round(payment_month, 2))
		interest_subsidy_list.append(max(0.0, round(interest_subsidy, 2)))
		payment_total_list.append(round(payment_total, 2))
		loan_remaining_list.append(round(loan_remaining, 2))


	payments = dict(
		years = [i+1 for i in range(loan_years)],
		payment_month = payment_month_list,
		interest_subsidy = interest_subsidy_list,
		payment_total = payment_total_list,
		loan_remaining = loan_remaining_list,
		interest_annual = interest_list,
		income_annual = income_list
	)

	# add field for annual payment for debugging
	payments['payment_annual'] = [x * 12 for x in payments['payment_month']]


	return payments


def standard_plan(loan, income, income_growth, interest_rate):

	payment_annual = loan / 10.
	payment_month = payment_annual / 12.

	payment_toal_list = []
	loan_remaining_list = []
	interest_list = []
	income_list = []

	income_growing = income
	loan_remaining = loan

	for i in range(10):
		# print "Year:", i
		income_list.append(income_growing)
		

		interest_annual = min(loan, loan_remaining) * interest_rate

		loan_remaining += interest_annual
		loan_remaining -= payment_annual
		
		interest_list.append(interest_annual)

		payment_total += payment_annual
		# print "Total payment:", payment_total
		
		# print "Remaining loan:", loan_remaining

		income_growing += income_growing * income_growth

		payment_total_list.append(round(payment_total, 2))
		loan_remaining_list.append(round(loan_remaining, 2))


	payments = dict(
		years = [i+1 for i in range(10)],
		payment_month = 12 * [payment_month],
		interest_subsidy = 12 * [0.0],
		payment_total = payment_total_list,
		loan_remaining = loan_remaining_list,
		interest_annual = interest_list,
		income_annual = income_list
	)

	return payments


def calculate_loan_payment(plan_type, loan_years, loan, interest_rate, 
	income_ag, income_growth, size, region, marital_status, income_spouse):

	# determine income. If REPAYE, joint income considered regardless of 
	# filing status
	if marital_status != 'single':
		if marital_status == 'married filing separate':
			if plan_type != 'REPAYE':
				income_total_gross = income_ag
			else:
				income_total_gross = income_ag + income_spouse
		else: # married filing jointly
			income_total_gross = income_ag + income_spouse
	else:
		income_total_gross = income_ag

	if plan_type == 'standard':
		plan = standard_plan(loan, income_ag, income_growth, interest_rate)

	else:
		income_discretionary = discretionary_income(
			income_total_gross, 
			size, 
			region, 
			poverty_df)

		plan = income_based_payments(
			income_discretionary,
			income_growth,
			loan_years,
			loan,
			interest_rate,
			plan_type)

	return plan



def recalculate(attr, old, new):
	# get current list of relevant variables
	plan_type = plan_choice.labels[plan_choice.active]
	loan_years = int(term_input.value)
	loan = float(loan_input.value)
	interest_rate = float(interest_input.value) / 100.
	income = float(income_input.value)
	income_growth = float(growth_input.value) / 100.
	size = int(size_input.value)
	region = region_choice.value
	marital_status = marital_choice.value
	income_spouse = float(income_spouse_input.value)

	income_discretionary_new = discretionary_income(
	income, 
	size, 
	region, 
	poverty_df)

	new_plan = calculate_loan_payment(plan_type, loan_years, loan, interest_rate, 
		income, income_growth, size, region, marital_status, income_spouse)

	source.data.update(new_plan)

############################ Read in data ######################################

poverty_df = pd.read_table('poverty_levels.txt')

############################ Define widgets ####################################

# plan and loan information
plan_choice = RadioGroup(
	labels=['REPAYE', 'PAYE', 'standard (10 loan years)'], active=0)
plan_choice.on_change('active', recalculate)

term_input = TextInput(value='20', title='Loan term (loan years)')
term_input.on_change('value', recalculate)

loan_input = TextInput(value='411000', title='Loan amount')
loan_input.on_change('value', recalculate)

interest_input = TextInput(value='6.04', title='Interest rate (%)')
interest_input.on_change('value', recalculate)


# personal information
income_text = Div(text='''Adjusted gross income. Discretionary income will 
	be calculated based on state and family size''')
income_input = TextInput(value='225000', title='Adjusted gross income')
income_input.on_change('value', recalculate)

growth_text = Div(text='''Your income grows over time, so your income based 
	repayments will increase as well. Need to estimate how your income will 
	grow over time.''')
growth_input = TextInput(value='3.5', title='''Income growth (3.5% is 
	historic average)''')
growth_input.on_change('value', recalculate)

size_text = Div(text='''Income percentage is based on discretionary income, 
	which is your AGI minus 150% of the poverty line for your family size.
	***Currently, poverty line does not increase with inflation so discretionary income
	over time is higher than it should be. This results in higher monthly payments compared
	to online REPAYE calculators.***''')
size_input = TextInput(value='1', title='Family size')
size_input.on_change('value', recalculate)

region_choice = Select(title='State:', value='contiguous 48', 
	options=['contiguous 48', 'Alaska', 'Hawaii'])
region_choice.on_change('value', recalculate)

marital_text = Div(text='''REPAYE considers joint income whether filing 
	separately or jointly. Compares tax differences when filing 
	jointly/separately''')
marital_choice = Select(title='Marital status', value='single',
	options=['single', 'married filing separate', 'married filing jointly'])
marital_choice.on_change('value', recalculate)

income_spouse_input = TextInput(value='0', title='Spouse income')
income_spouse_input.on_change('value', recalculate)


box1 = WidgetBox(plan_choice, loan_input, term_input, interest_input,
                    income_text, income_input,
                     growth_text, growth_input,)
    
box2 = WidgetBox(
    size_text, size_input,
    region_choice,
    marital_text, marital_choice, income_spouse_input)
 

############################## Initialize ######################################

plan_type = plan_choice.labels[plan_choice.active]
loan_years = int(term_input.value)
loan = float(loan_input.value)
interest_rate = float(interest_input.value) / 100.
income = float(income_input.value)
income_growth = float(growth_input.value) / 100.
size = int(size_input.value)
region = region_choice.value
marital_status = marital_choice.value
income_spouse = float(income_spouse_input.value)


initial_plan = calculate_loan_payment(plan_type, loan_years, loan, interest_rate, income,
	income_growth, size, region, marital_status, income_spouse)


# display table
source = ColumnDataSource(initial_plan)
columns = [
	TableColumn(field='years', title='Year'),
	TableColumn(field='income_annual', title='Annual discretionary income',
		formatter=NumberFormatter()),
	TableColumn(field='payment_month', title='Monthly payment',
		formatter=NumberFormatter()),
	TableColumn(field='payment_annual', title='Annual payment',
		formatter=NumberFormatter()),
	TableColumn(field='interest_annual', title='Annual interest accrued',
		formatter=NumberFormatter()),
	TableColumn(field='interest_subsidy', title='Annual interest subsidy'),
	TableColumn(field='payment_total', title='Total loan payment', 
		formatter=NumberFormatter()),
	TableColumn(field='loan_remaining', title='Remaining loan balance',
		formatter=NumberFormatter())
]

payment_table = DataTable(source=source, columns=columns, width=1200, height=800)

# show(payment_table)

################################# Layout ######################################

layout = row(box1, box2, payment_table)

# make tab with layout
tab = Panel(child=layout, title = 'Income-driven repayment comparison')

tabs = Tabs(tabs=[tab])

# add to current document (displays plot)
curdoc().add_root(tabs)


# after two more years of paying at resident salary, loan total will be 458,031.
# four years paid in residency with 21 years left on loan

