// Copyright (c) 2025, Innomat, Asprotec and libracore and contributors
// For license information, please see license.txt

frappe.ui.form.on('Innomat Budget', {
    onload(frm) {
        apply_account_filter(frm);
    },

    company(frm) {
        apply_account_filter(frm);
        populate_if_empty(frm);
    },

    cost_center(frm) {
        frappe.db.get_value("Cost Center", frm.doc.cost_center, "company").then(r => {
            if(r.message && r.message.company) {
                frm.set_value("company", r.message.company);
            }
        });
    },

    refresh(frm) {
        frm.add_custom_button(__("Konten ergänzen"), () => {
            let account_list = frm.doc.accounts.map(acc => acc.account);
            add_missing_accounts(frm, account_list);
        });
        frm.add_custom_button(__("Leerzeilen entfernen"), () => {
            remove_empty_rows(frm);
        });
        frm.add_custom_button(__("Konten sortieren"), () => {
            sort_rows(frm);
        });
    },

    validate(frm) {
        frm.doc.accounts.forEach(acc => {
            update_account_total(frm, acc.doctype, acc.name);
        });
        update_grand_total(frm);
    }
});

frappe.ui.form.on('Innomat Budget Account', {
    budget_01(frm, cdt, cdn) { update_totals(frm, cdt, cdn); },
    budget_02(frm, cdt, cdn) { update_totals(frm, cdt, cdn); },
    budget_03(frm, cdt, cdn) { update_totals(frm, cdt, cdn); },
    budget_04(frm, cdt, cdn) { update_totals(frm, cdt, cdn); },
    budget_05(frm, cdt, cdn) { update_totals(frm, cdt, cdn); },
    budget_06(frm, cdt, cdn) { update_totals(frm, cdt, cdn); },
    budget_07(frm, cdt, cdn) { update_totals(frm, cdt, cdn); },
    budget_08(frm, cdt, cdn) { update_totals(frm, cdt, cdn); },
    budget_09(frm, cdt, cdn) { update_totals(frm, cdt, cdn); },
    budget_10(frm, cdt, cdn) { update_totals(frm, cdt, cdn); },
    budget_11(frm, cdt, cdn) { update_totals(frm, cdt, cdn); },
    budget_12(frm, cdt, cdn) { update_totals(frm, cdt, cdn); },
});


function apply_account_filter(frm) {
  frm.set_query('account', 'accounts', function() {
    return {
      filters: get_account_filters(frm)
    };
  });
}

function populate_if_empty(frm) {
    if(frm.doc.__islocal && frm.doc.company) {
        for(const acc of frm.doc.accounts) {
            if(acc.annual_budget) {
                return;
            }
        }
        frm.set_value("accounts",[]);
        add_missing_accounts(frm);
    }
}

function update_totals(frm, cdt, cdn) {
    update_account_total(frm, cdt, cdn);
    update_grand_total(frm);
}

function update_account_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let sum = 0;
    for(let i=1; i<=12; i++) {
        let month_str = ("0"+i).substr(-2);
        sum += row['budget_'+month_str] || 0;
    }
    frappe.model.set_value(cdt, cdn, "annual_budget", sum);
}

function update_grand_total(frm) {
    let total = 0;
    frm.doc.accounts.forEach(acc => {
        total += (acc.annual_budget || 0);
    });
    frm.set_value("total", total);
}

function add_missing_accounts(frm, account_list = []) {
    frappe.dom.freeze(__("Kontenplan wird geladen..."));
    frappe.db.get_list('Account', {
        fields: ['name', 'account_number'],
        filters: get_account_filters(frm),
        order_by: 'account_number asc',
        limit: 999
    }).then(accounts => {
        let cnt = 0;
        accounts.forEach(acc => {
            if(!account_list.includes(acc.name)) {
                let row = frm.add_child('accounts');
                row.account = acc.name;
                cnt++;
            }
        });
        frm.refresh_field('accounts');
        frappe.dom.unfreeze();
        frappe.show_alert({message: __("{0} Konten hinzugefügt", [cnt]), indicator: 'green'});
    });
}

function remove_empty_rows(frm) {
    let used_accounts = [];
    let idx = 1;
    for(const [i, acc] of frm.doc.accounts.entries()) {
        if(acc.annual_budget) {
            acc.idx = idx;
            used_accounts.push(acc);
            idx++;
        }
    }
    let cnt = frm.doc.accounts.length - used_accounts.length;
    frm.doc.accounts = used_accounts;
    frm.refresh_field('accounts');
    frappe.show_alert({message: __("{0} Konten entfernt", [cnt]), indicator: 'green'});
}

function get_account_filters(frm) {
    return {
        company: frm.doc.company,
        is_group: 0,
        disabled: 0,
        report_type: 'Profit and Loss'
    };
}

function sort_rows(frm) {
    let sorted = frm.doc.accounts.sort((a,b) => {
        const val_a = a && a.account ? parseInt(a.account.substr(0,4)) || 0 : 0;
        const val_b = b && b.account ? parseInt(b.account.substr(0,4)) || 0 : 0;
        return val_a - val_b;
    });
    for(let i=0;i<sorted.length;i++){
        sorted[i].idx = i+1;
    }
    frm.doc.accounts = sorted;
    frm.refresh_field('accounts');
}