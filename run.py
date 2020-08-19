import sys
from functools import reduce
import itertools
import json
from datetime import datetime
import re

tax_years = dict()

class Transaction:

    def __init__(self, amount, date, description=''):
        self.amount = amount
        self.date = datetime.strptime(date, '%d/%m/%Y')
        self.description = description
        
class TaxYear:

    def __init__(self, year):
        self.year = year

    def summary(self):

        fed_tax_due = self.tax_due(self.federal_tax_brackets)
        prov_tax_due = self.tax_due(self.provincial_tax_brackets)
        total_tax_due = fed_tax_due + prov_tax_due
        prev_years_room = 0
        prev_years_withdrawals = 0
        
        if self.year-1 in tax_years:
            prev_years_room = tax_years[self.year-1].get_tfsa_cumulated_room()
            prev_years_withdrawals = tax_years[self.year-1].get_tfsa_withdrawals()

        summary_string = ''
        summary_string += '{}:\n--------\n'.format(self.year)
        summary_string += 'Income: ${:,.2f}\n'.format(self.income)
        summary_string += '\nRRSP Available Room: ${:,.2f}\n'.format(self.get_rrsp_cumulated_room())
        summary_string += 'TFSA Available Room: ${:,.2f}\n'.format(self.get_tfsa_cumulated_room())
        summary_string += '\nFederal Taxes Due: ${:,.2f}\n'.format(fed_tax_due)
        summary_string += 'Provincial ({}) Taxes Due: ${:,.2f}\n'.format(self.province, prov_tax_due)
        summary_string += 'Total Taxes Due: ${:,.2f}\n'.format(total_tax_due)

        return summary_string

    def get_rrsp_cumulated_room(self):

        prev_years_room = 0

        if self.year-1 in tax_years:
            prev_years_room = tax_years[self.year-1].get_rrsp_cumulated_room()

        curr_year_deposits = self.get_rrsp_deposits()

        return (self.get_rrsp_contribution_limit_current_year() + prev_years_room - curr_year_deposits)

    def get_rrsp_contribution_limit_current_year(self):
        return min(self.income*0.18, self.rrsp_gov_limit)

    def get_rrsp_deposits(self):

        rrsp_positive_transactions = list(filter(lambda x: x.amount > 0, self.rrsp_transactions ))
        rrsp_deposits = reduce(lambda sum, transaction: sum + transaction.amount, rrsp_positive_transactions, 0)
        
        return rrsp_deposits

    def get_tfsa_deposits(self):
        
        tfsa_positive_transactions = list(filter(lambda x: x.amount > 0, self.tfsa_transactions ))
        tfsa_deposits = reduce(lambda sum, transaction: sum + transaction.amount, tfsa_positive_transactions, 0)
        
        return tfsa_deposits

    def get_tfsa_cumulated_room(self):

        prev_years_room = 0
        prev_years_withdrawals = 0

        if self.year-1 in tax_years:
            prev_years_room = tax_years[self.year-1].get_tfsa_cumulated_room()
            prev_years_withdrawals = tax_years[self.year-1].get_tfsa_withdrawals()

        curr_year_deposits = self.get_tfsa_deposits()

        return (self.tfsa_gov_limit + prev_years_room + prev_years_withdrawals - curr_year_deposits)

    def get_tfsa_withdrawals(self):
        tfsa_negative_transactions = list(filter(lambda x: x.amount < 0, self.tfsa_transactions ))
        tfsa_withdrawals = reduce(lambda sum, transaction: sum + transaction.amount, tfsa_negative_transactions, 0)
        
        return abs(tfsa_withdrawals)

    def tax_due(self, tax_brackets):

        taxable_income = max(0, self.income - self.get_rrsp_deposits())

        for key, elem in tax_brackets.items():

            income_portion = 0
            if key == 1:
                income_portion = taxable_income if taxable_income < elem['upper_bound'] else elem['upper_bound']
            elif key == len(tax_brackets):
                if taxable_income < tax_brackets[key-1]['upper_bound']: income_portion = 0
                elif taxable_income > tax_brackets[key-1]['upper_bound']: income_portion = taxable_income - tax_brackets[key-1]['upper_bound']
            else:
                if taxable_income < tax_brackets[key-1]['upper_bound']: income_portion = 0
                elif taxable_income < elem['upper_bound']: income_portion = taxable_income - tax_brackets[key-1]['income portion']
                else: income_portion = elem['upper_bound']

            elem['income portion'] = income_portion
            elem['tax due'] = income_portion * elem['percent']
        
        return reduce(lambda sum, elem: sum + elem['tax due'], dict(itertools.islice(tax_brackets.items(), key)).values(), 0)


def subset_summary(start=None,end=None):

    if start is None and end is None: start,end = 0,3000
    elif start is not None and end is None: end = start

    string = ''
    for year, content in sorted(tax_years.items()):
        if year >= start and year <= end: string += content.summary() + '\n'
    return string

def load_data(personal_file, public_file='public-data.json'):
    
    personal_data = None
    public_data = None

    print('loading data... ', end='')
    try:
        with open(personal_file) as f:
            personal_data = json.load(f)
    except Exception as e:
        print('\n', e)
        exit(0)

    try:
        with open(public_file) as f:
            public_data = json.load(f)
    except Exception as e:
        print('\n', e)
        exit(0)

    try:
        for year, content in personal_data.items():
            
            new_year = TaxYear(int(year))
            new_year.province = content['province']
            new_year.income = content['income']
            new_year.monthly_savings_target = content['monthly_savings_target']
            new_year.rrsp_gov_limit = public_data[year]['rrsp']['gov_limit']
            new_year.rrsp_transactions = []
            new_year.tfsa_gov_limit = public_data[year]['tfsa']['gov_limit']
            new_year.tfsa_transactions = []
            new_year.federal_tax_brackets = dict()
            new_year.provincial_tax_brackets = dict()

            for contrubution in content['rrsp']['transactions']:
                new_year.rrsp_transactions.append(Transaction(contrubution['amount'], contrubution['date'], contrubution['description']))

            for contrubution in content['tfsa']['transactions']:
                new_year.tfsa_transactions.append(Transaction(contrubution['amount'], contrubution['date'], contrubution['description']))

            for key, bracket_content in public_data[year]['tax_brackets']['federal'].items():
                new_year.federal_tax_brackets[int(key)] = bracket_content

            for key, bracket_content in public_data[year]['tax_brackets']['provincial'][new_year.province].items():
                new_year.provincial_tax_brackets[int(key)] = bracket_content
            
            tax_years[int(year)] = new_year
    except Exception as e: print('\n', e)
    print('done')


def yearly_submenu(start,end=None):

    while True:

        print('\nYear{}: {}{}'.format('' if not end else 's' , start, '' if not end else (' to ' + str(end))))

        print('1. Income ')
        print('2. TFSA ')
        print('3. RRSP ')
        print('4. Taxes')
        print('5. Brief summary')
        print('\nPress \'b\' to select a different year or \'q\' to terminate\n')

        user_input = input()
        if user_input == 'b': break
        elif user_input == 'q': sys.exit(0)

        if not end: end = start

        print()
        print('-'*50)
        if user_input == '1':
            total = 0
            for year in range(start, end+1):
                print('{}: ${:,.2f}'.format(year, tax_years[year].income))
                total += tax_years[year].income
            print('\nTotal: ${:,.2f}'.format(total))

        elif user_input == '2':
            for year in range(start, end+1):
                print('{}:'.format(year))
                print('* Deposits: ${:,.2f}'.format(tax_years[year].get_tfsa_deposits()))
                print('* Withdrawals: ${:,.2f}'.format(tax_years[year].get_tfsa_withdrawals()))
                print('* Accumulated room: ${:,.2f}\n'.format(tax_years[year].get_tfsa_cumulated_room()))

        elif user_input == '3':
            for year in range(start, end+1):
                print('{}:'.format(year))
                print('* Income: ${:,.2f}'.format(tax_years[year].income))
                print('* Contribution limit: ${:,.2f}'.format(tax_years[year].get_rrsp_contribution_limit_current_year()))
                print('* Deposits: ${:,.2f}'.format(tax_years[year].get_rrsp_deposits()))
                print('* Accumulated room: ${:,.2f}\n'.format(tax_years[year].get_rrsp_cumulated_room()))

        elif user_input == '4':
            total = 0
            for year in range(start, end+1):
                federal_tax = tax_years[year].tax_due(tax_years[year].federal_tax_brackets)
                provincial_tax = tax_years[year].tax_due(tax_years[year].provincial_tax_brackets)
                total += federal_tax + provincial_tax
                print('{}:'.format(year))
                print('* Income: ${:,.2f}'.format(tax_years[year].income))
                print('* Federal tax: ${:,.2f}'.format(federal_tax))
                print('* Provincial ({}) tax: ${:,.2f}'.format(tax_years[year].province, provincial_tax))
                print('* Total tax: ${:,.2f}\n'.format(federal_tax + provincial_tax))

            print('Total: ${:,.2f}'.format(total))

        elif user_input == '5':
            print(subset_summary(start, end))
        print('-'*50)


def yearly_menu():

    start = None
    end = None

    while True:

        print()
        print('Enter a range (e.g. 2018-2020)')
        print('Press \'b\' to back to the main menu or \'q\' to terminate\n')

        user_input = input()
        if user_input == 'b': break
        elif user_input == 'q': sys.exit(0)
        
        pattern = re.compile('^(\d{4})(?:-(\d{4}))?$')
        re_match = pattern.match(user_input)

        if not (re_match):
            print('This doesn\'t seem to be a valid range. Please try again.\n')
            continue

        if re_match.group(1): start = int(re_match.group(1))
        if re_match.group(2): end = int(re_match.group(2))

        yearly_submenu(start, end)

def main_menu():
    while True:

        print()
        print('1. Select specific year(s)')
        print('2. See summary for all years')
        print('3. Enter a transaction')
        print('\nPress \'q\' to terminate\n')
        
        user_input = input()

        if user_input == '1': yearly_menu()
        elif user_input == '2':
            print('-'*50)
            print(subset_summary())
            print('-'*50)

        if user_input == 'q': break

if __name__ == '__main__':
    
    personal_file = 'data.json'
    load_data(personal_file)
    main_menu()
    