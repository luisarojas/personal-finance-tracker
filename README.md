
# 💰 Personal Finance Tracker

![GitHub repo size](https://img.shields.io/github/repo-size/luisarojas/personal-finance-tracker) ![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/luisarojas/personal-finance-tracker) ![GitHub last commit](https://img.shields.io/github/last-commit/luisarojas/personal-finance-tracker) ![GitHub issues](https://img.shields.io/github/issues-raw/luisarojas/personal-finance-tracker)

### Requirements:

* `python 3.7+`

### How to execute

```
$ python run.py
```

### What does it do?

Given the needed information about income and RRSP/TFSA transactions, calculates the available room for both.

`// TODO`: Also calculate the optimal savings distribution between the two.

### Input JSON Schema
```json
{
    "2013": {
        "province": "ON",
        "income": 0,
        "monthly_savings_target": 0,
        "rrsp": {
            "transactions": [
                {
                    "amount": 0,
                    "date": "DD/MM/YYYY",
                    "description": ""
                }
            ]
        },
        "tfsa": {
            "transactions": [
                {
                    "amount": 0,
                    "date": "DD/MM/YYYY",
                    "description": ""
                }
            ]
        }
    }
}
```
*Note: Template is included*