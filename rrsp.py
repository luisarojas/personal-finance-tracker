from functools import reduce
import itertools
import json

tax_years = dict()

class Transaction:

    def __init__(self, amount, date):
        self.amount = amount
        self.date = date
        
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
        summary_string += '\n{}:\n--------\n'.format(self.year)
        summary_string += 'Income: ${:,.2f}\n'.format(self.income)
        summary_string += '\nRRSP Available Room: ${:,.2f}\n'.format(self.get_rrsp_cumulated_room())
        summary_string += 'TFSA Available Room: ${:,.2f}\n'.format(self.get_tfsa_cumulated_room())
        summary_string += 'Federal Taxes Due: ${:,.2f}\n'.format(fed_tax_due)
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
        return min(self.income*0.18, self.rrsp_gov_set_limit)

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

        return (self.tfsa_gov_set_limit + prev_years_room + prev_years_withdrawals - curr_year_deposits)

    def get_tfsa_withdrawals(self):
        tfsa_negative_transactions = list(filter(lambda x: x.amount < 0, self.tfsa_transactions ))
        tfsa_withdrawals = reduce(lambda sum, transaction: sum + transaction.amount, tfsa_negative_transactions, 0)
        
        return abs(tfsa_withdrawals)

    def tax_due(self, tax_brackets):

        taxable_income = max(0, self.income - self.get_rrsp_deposits())

        for key, elem in tax_brackets.items():

            income_portion = 0
            if key == 1:
                income_portion = taxable_income if taxable_income < elem['upper'] else elem['upper']
            elif key == len(tax_brackets):
                if taxable_income < tax_brackets[key-1]['upper']: income_portion = 0
                elif taxable_income > tax_brackets[key-1]['upper']: income_portion = taxable_income - tax_brackets[key-1]['upper']
            else:
                if taxable_income < tax_brackets[key-1]['upper']: income_portion = 0
                elif taxable_income < elem['upper']: income_portion = taxable_income - tax_brackets[key-1]['income portion']
                else: income_portion = elem['upper']

            elem['income portion'] = income_portion
            elem['tax due'] = income_portion * elem['perc']
        
        return reduce(lambda sum, elem: sum + elem['tax due'], dict(itertools.islice(tax_brackets.items(), key)).values(), 0)


if __name__ == '__main__':

    try:
        with open('data.json') as f:
            data = json.load(f)
    except Exception as e: print(e)

    for year, content in data.items():
        
        new_year = TaxYear(int(year))
        new_year.province = content['province']
        new_year.income = content['income']
        new_year.monthly_savings_target = content['monthly_savings_target']
        new_year.rrsp_gov_set_limit = content['rrsp_gov_limit']
        new_year.rrsp_transactions = []
        new_year.tfsa_gov_set_limit = content['tfsa_gov_limit']
        new_year.tfsa_transactions = []
        new_year.federal_tax_brackets = dict()
        new_year.provincial_tax_brackets = dict()

        for contrubution in content['rrsp_transactions'].values():
            new_year.rrsp_transactions.append(Transaction(contrubution['amount'], contrubution['date']))

        for contrubution in content['tfsa_transactions'].values():
            new_year.tfsa_transactions.append(Transaction(contrubution['amount'], contrubution['date']))

        for key, bracket_content in content['federal_tax_brackets'].items():
            new_year.federal_tax_brackets[int(key)] = bracket_content

        for key, bracket_content in content['provincial_tax_brackets'].items():
            new_year.provincial_tax_brackets[int(key)] = bracket_content
        
        tax_years[int(year)] = new_year

for year, content in tax_years.items():
    print(content.summary())