# Copyright (c) 2026, Innomat and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import patch

import frappe

from innomat.innomat_reporting.report.jahresergebnis_projekte_mitarbeiter import jahresergebnis_projekte_mitarbeiter as report


class TestRevenueAllocation(unittest.TestCase):
    def test_revenue_is_shared_by_project_hours(self):
        times = [frappe._dict(employee='A', project='P', hours=2),
                 frappe._dict(employee='B', project='P', hours=1),
                 frappe._dict(employee='A', project='Q', hours=1),
                 frappe._dict(employee='B', project=None, hours=5)]
        result = report.allocate_revenue({'P': 300, 'Q': 60}, times)
        self.assertEqual(result['A'], 260)
        self.assertEqual(result['B'], 100)

    def test_projects_without_hours_remain_unallocated(self):
        times = [frappe._dict(employee='A', project='P', hours=0)]
        self.assertEqual(dict(report.allocate_revenue({'P': 100, 'Q': 300}, times)), {})


class TestActualCosts(unittest.TestCase):
    @patch.object(report.frappe, 'get_all')
    @patch.object(report, 'gl_totals', return_value=(400, 320))
    @patch.object(report, 'project_costs')
    @patch.object(report, 'invoice_revenue')
    @patch.object(report, 'time_costs')
    @patch.object(report, 'salary_costs', return_value={'A': 100, 'B': 80})
    def test_project_and_employee_reconcile_with_gl(self, salaries, time_costs,
                                                     revenues, costs, totals, get_all):
        time_costs.return_value = [frappe._dict(employee='A', project='P', hours=6),
                                   frappe._dict(employee='A', project=None, hours=4),
                                   frappe._dict(employee='B', project='P', hours=8)]
        revenues.return_value = [frappe._dict(project='P', revenue=400)]
        costs.return_value = ([frappe._dict(project='P', amount=40)], [], [])
        get_all.side_effect = lambda doctype, **kwargs: [
            frappe._dict(name='P', project_name='Project') if doctype == 'Project'
            else frappe._dict(name=name, employee_name=name)
            for name in (['P'] if doctype == 'Project' else ['A', 'B'])]

        basis = report.actual_cost_basis('Company', '2025-01-01', '2025-12-31')
        self.assertEqual(basis['salary_rates'], {'A': 10, 'B': 10})
        self.assertEqual(basis['labor_by_project']['P'], 140)
        self.assertEqual(basis['remaining_expense'], 100)
        self.assertEqual(basis['project_pool'], 140)  # includes 40 internal salary

        projects = report.project_data('Company', '2025-01-01', '2025-12-31')
        employees = report.employee_data('Company', '2025-01-01', '2025-12-31')
        self.assertEqual(projects[0]['profit'], 80)
        self.assertAlmostEqual(sum(r['contribution'] for r in employees), 80)
        self.assertAlmostEqual(sum(r['overhead'] for r in employees), 100)

    @patch.object(report.frappe, 'get_all', return_value=[])
    @patch.object(report, 'gl_totals', return_value=(0, 50))
    @patch.object(report, 'project_costs', return_value=([], [], []))
    @patch.object(report, 'invoice_revenue', return_value=[])
    @patch.object(report, 'time_costs', return_value=[])
    @patch.object(report, 'salary_costs', return_value={'A': 20})
    def test_no_hours_leaves_expense_unallocated(self, *mocks):
        basis = report.actual_cost_basis('Company', '2025-01-01', '2025-12-31')
        self.assertEqual(basis['salary_rates'], {})
        rows = report.project_data('Company', '2025-01-01', '2025-12-31')
        self.assertEqual(rows[0]['overhead'], 50)
        self.assertEqual(rows[0]['profit'], -50)

    @patch.object(report, 'gl_totals', return_value=(0, 80))
    @patch.object(report, 'project_costs', return_value=([], [], []))
    @patch.object(report, 'invoice_revenue', return_value=[])
    @patch.object(report, 'time_costs', return_value=[
        frappe._dict(employee='A', project='P', hours=8)])
    @patch.object(report, 'salary_costs', return_value={})
    def test_missing_slip_is_not_replaced_with_estimated_rate(self, *mocks):
        basis = report.actual_cost_basis('Company', '2025-01-01', '2025-12-31')
        self.assertEqual(basis['labor_by_project']['P'], 0)
        self.assertEqual(basis['project_pool'], 80)
        self.assertEqual(report.allocate_by_hours(basis['project_pool'],
                                                 basis['project_hours'])['P'], 80)