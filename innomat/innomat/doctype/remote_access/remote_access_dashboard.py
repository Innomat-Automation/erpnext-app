# -*- coding: utf-8 -*-
# Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
# For license information, please see license.txt

from frappe import _

def get_data():
   return {
      'fieldname': 'remote_access',
      'transactions': [
         {
            'label': _('Equipment'),
            'items': ['Equipment']
         }
      ]
   }
