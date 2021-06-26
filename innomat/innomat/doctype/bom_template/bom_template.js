// Copyright (c) 2021, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt

frappe.provide("innomat.bom_template");

frappe.ui.form.on('BOM Template', {
	setup: function(frm) {
		frm.set_query("bom_no", "items", function() {
			return {
				filters: {
					'currency': frm.doc.currency,
					'company': frm.doc.company
				}
			};
		});

		frm.set_query("source_warehouse", "items", function() {
			return {
				filters: {
					'company': frm.doc.company
				}
			};
		});
		frm.set_query("item_code", "items", function() {
			return {
				query: "erpnext.controllers.queries.item_query",
				filters: [["Item", "name", "!=", cur_frm.doc.item]]
			};
		});

		frm.set_query("bom_no", "items", function(doc, cdt, cdn) {
			var d = locals[cdt][cdn];
			return {
				filters: {
					'item': d.item_code,
					'is_active': 1,
					'docstatus': 1
				}
			};
		});
	},

	onload_post_render: function(frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},
	// refresh: function(frm) {

	// }
});

frappe.ui.form.on("BOM Item", "qty", function(frm, cdt, cdn) {
	var d = locals[cdt][cdn];
	d.stock_qty = d.qty * d.conversion_factor;
	refresh_field("stock_qty", d.name, d.parentfield);
});



innomat.bom_template.BomController = erpnext.TransactionController.extend({

	item_code: function(doc, cdt, cdn){
		var child = locals[cdt][cdn];
		if (child.bom_no) {
			child.bom_no = '';
		}

		get_bom_material_detail(doc, cdt, cdn, false);
	},
});

$.extend(cur_frm.cscript, new innomat.bom_template.BomController({frm: cur_frm}));


cur_frm.cscript.bom_no	= function(doc, cdt, cdn) {
	get_bom_material_detail(doc, cdt, cdn, false);
};

var get_bom_material_detail= function(doc, cdt, cdn, scrap_items) {
	var d = locals[cdt][cdn];
	if (d.item_code) {
		return frappe.call({
			doc: doc,
			method: "get_bom_material_detail",
			args: {
				'item_code': d.item_code,
				'bom_no': d.bom_no != null ? d.bom_no: '',
				"scrap_items": scrap_items,
				'qty': d.qty,
				"stock_qty": d.stock_qty,
				"include_item_in_manufacturing": d.include_item_in_manufacturing,
				"uom": d.uom,
				"stock_uom": d.stock_uom,
				"conversion_factor": d.conversion_factor
			},
			callback: function(r) {
				d = locals[cdt][cdn];
				$.extend(d, r.message);
				refresh_field("items");

				doc = locals[doc.doctype][doc.name];
			},
			freeze: true
		});
	}
};
