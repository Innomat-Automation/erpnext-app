
import frappe
from zeep import Client
from zeep import helpers
import os
import json


@frappe.whitelist()
def validate_iban(iban):
    validator_settings = frappe.get_doc("IBAN Validator")
    client = Client(validator_settings.validator_url)
    data = client.service.validate_iban(iban=iban,user=validator_settings.username,password=validator_settings.get_password('password'),account_holder="")
    return helpers.serialize_object(data,dict)


@frappe.whitelist()
def test_validate_iban(iban):
    data = {
            'iban': iban,
            'result': 'passed',
            'return_code': '0',
            'checks': [
                'length',
                'bank_code',
                'account_number',
                'iban_checksum'
            ],
            'bic_candidates': [
                {
                'bic': 'KBSGCH22XXX',
                'zip': '9001',
                'city': 'St. Gallen',
                'wwwcount': 0,
                'sampleurl': None
                }
            ],
            'all_bic_candidates': [
                {
                'bic': 'KBSGCH22XXX',
                'zip': '9001',
                'city': 'St. Gallen',
                'wwwcount': 0,
                'sampleurl': None
                }
            ],
            'country': 'CH',
            'bank_code': '30781',
            'bank': 'St. Galler Kantonalbank AG',
            'bank_address': '                                   \n9001       St. Gallen',
            'bank_url': None,
            'branch': None,
            'branch_code': None,
            'in_scl_directory': 'yes',
            'sct': 'yes',
            'sdd': 'no',
            'cor1': 'no',
            'b2b': 'no',
            'scc': 'no',
            'account_number': '610241872000',
            'account_validation_method': None,
            'account_validation': '03: CH-/LI-IBAN in Input-Record, daher IBAN nach Prüfung von Länge, PZ und IID in Output-Record übernommen',
            'length_check': 'passed',
            'account_check': 'passed',
            'bank_code_check': 'passed',
            'iban_checksum_check': 'passed',
            'data_age': '20210816',
            'iban_www_occurrences': 0,
            'www_seen_from': None,
            'www_seen_until': None,
            'iban_url': None,
            'url_rank': None,
            'url_category': None,
            'url_min_depth': None,
            'www_prominence': None,
            'iban_reported_to_exist': 0,
            'iban_last_reported': None,
            'IBANformat': 'CHkk BBBB BCCC CCCC CCCC C',
            'formatcomment': 'B = bank code, C = account No.',
            'balance': 8
        }
