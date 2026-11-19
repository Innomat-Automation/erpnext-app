# Copyright (c) 2026, asprotec ag and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.manufacturing.doctype.bom.bom import BOM

# keep a reference to the standard implementation for the fallback
_standard_get_valuation_rate = BOM.get_valuation_rate

def get_valuation_rate(self, args):
    """Prefer the valuation rate maintained in the item master.

    Standard ERPNext v12 computes the BOM valuation rate from the current
    stock value (Bin) or the last Stock Ledger Entry and only falls back to
    the item master as a last resort. Innomat maintains the valuation rate
    on the item master (see innomat.innomat.scripts.item.set_price_list),
    so that rate takes precedence when it is set. If it is not set (0 or
    empty), the standard logic applies.
    """
    item_valuation_rate = flt(frappe.db.get_value("Item", args.get('item_code'), "valuation_rate"))
    if item_valuation_rate > 0:
        return item_valuation_rate

    return _standard_get_valuation_rate(self, args)

def apply_bom_overrides():
    """Monkey patch BOM methods (Frappe v12 has no override_doctype_class hook)."""
    BOM.get_valuation_rate = get_valuation_rate

# apply on import: the doc_events hooks below are resolved (imported) by
# Document.run_method *before* the document method itself runs, so the
# override is always in place before any BOM rate is computed
apply_bom_overrides()

def ensure_bom_overrides(self, method=None, *args, **kwargs):
    """doc_events handler for BOM (validate, update_cost, get_bom_material_detail).

    Intentionally a no-op: importing this module applies the override.
    """
    pass

@frappe.whitelist()
def enqueue_update_cost():
    """Override for BOM Update Tool ('Update latest price in all BOMs').

    Enqueues the innomat wrapper instead of the standard function so that
    the background worker imports this module (and thereby the override)
    before recalculating the BOM costs.
    """
    frappe.enqueue("innomat.innomat.scripts.bom.update_cost_all_boms")
    frappe.msgprint(_("Queued for updating latest price in all Bill of Materials. It may take a few minutes."))

def update_cost_all_boms():
    from erpnext.manufacturing.doctype.bom_update_tool.bom_update_tool import update_cost
    update_cost()

@frappe.whitelist()
def preview_update_cost(bom):
    """Return old and new rates of the BOM items without writing anything.

    Used by the innomat 'Update Cost' button on submitted BOMs so that the
    user can review the new prices before they are persisted (the standard
    update_cost writes to the database even with save=False).
    """
    doc = frappe.get_doc("BOM", bom)
    doc.check_permission("read")
    items = []
    for d in doc.get("items"):
        rate = doc.get_rm_rate({
            "item_code": d.item_code,
            "bom_no": d.bom_no,
            "qty": d.qty,
            "uom": d.uom,
            "stock_uom": d.stock_uom,
            "conversion_factor": d.conversion_factor
        })
        items.append({
            "item_code": d.item_code,
            "item_name": d.item_name,
            "qty": d.qty,
            "uom": d.uom,
            "old_rate": flt(d.rate),
            # update_cost keeps the old rate if no new rate is found
            "new_rate": flt(rate) or flt(d.rate)
        })
    return items
