


frappe.ui.form.on("Supplier", {
    "iban": function(frm) {
        var iban = frm.doc.iban.replace(/\s+/g,'');
        if(iban[0] == "C" && iban[1] == "H" && iban[4] == 3)
        {
            frappe.msgprint("QR-IBAN bitte als ESR Teilnehmernummer eingeben.");
        }

    }
});

frappe.ui.form.on("Supplier", {
    "check_iban": function(frm) {
        console.log("Check IBAN");
        frappe.call({
            "method": "innomat.innomat.iban.validate_iban",
            "args": {
                "iban": frm.doc.iban
            },
            "callback": function(response) {
                var data = response.message;
                console.log("IBAN Callback");
                console.log(response);
                if (data) {
                    var d = new frappe.ui.Dialog({
                        title: __('Check IBAN'),
                        fields: [
                            {
                                "label" : "IBAN",
                                "fieldname": "iban",
                                "fieldtype": "Read Only",
                                "reqd": 1,
                                "readonly":1,
                                "default": get_iban(data)
                            },
                            {
                                "label" : "Result",
                                "fieldname": "result",
                                "fieldtype": "Read Only",
                                "default": data.result
                            },
                            {
                                "label" : "Validation",
                                "fieldname": "validation",
                                "fieldtype": "Read Only",
                                "default": data.account_validation
                            },
                            {
                                "label" : "Bank",
                                "fieldname": "bank",
                                "fieldtype": "Read Only",
                                "reqd": 1,
                                "readonly":1,
                                "default": data.bank
                            },
                            {
                                "label" : "IBAN Format",
                                "fieldname": "iban_format",
                                "fieldtype": "Read Only",
                                "reqd": 1,
                                "readonly":1,
                                "default": data.IBANformat
                            },
                            {
                                "label" : "BIC",
                                "fieldname": "bic",
                                "fieldtype": "Select",
                                "options": get_bic(data)
                            }

                        ],
                        primary_action: function() {
                            var data = d.get_values();
                            frm.set_value("iban", data.iban);
                            frm.set_value("bic", data.bic);
                            d.hide();
                        },
                        primary_action_label: __('Upate IBAN & BIC')
                    });
                    d.show();
                }
            }
        });
    }
});


if (!String.prototype.splice) {
    /**
     * {JSDoc}
     *
     * The splice() method changes the content of a string by removing a range of
     * characters and/or adding new characters.
     *
     * @this {String}
     * @param {number} start Index at which to start changing the string.
     * @param {number} delCount An integer indicating the number of old chars to remove.
     * @param {string} newSubStr The String that is spliced in.
     * @return {string} A new string with the spliced substring.
     */
    String.prototype.splice = function(start, delCount, newSubStr) {
        return this.slice(0, start) + newSubStr + this.slice(start + Math.abs(delCount));
    };
}

function get_bic(data)
{
    if(data){
        var result = [];
        if(data.bic_candidates && data.bic_candidates.length > 0)
        {
            for (var i = 0; i < data.bic_candidates.length; i++) {
                result.push(data.bic_candidates[i].bic);
            }
            console.log(result);
            return result;
        }
        else if(data.all_bic_candidates && data.all_bic_candidates.length > 0)
        {
            for (var i = 0; i < data.bic_candidates.length; i++) {
                result.push(data.all_bic_candidates[i].bic);
            }
            console.log(result);
            return result;
        }
        else
        {
            console.log("No BIC found");
            return ["No BIC found"];
        }
    }else{
        console.log("No Data found");
        return ["No BIC found"];
    }
}



function get_iban(data)
{
    var iban = data.iban;
    if(data.IBANformat)
    {
        for (var i = 0; i < data.IBANformat.length; i++) {
            if(data.IBANformat[i] == ' ')
            {
                iban = iban.splice(i,0,' ');
            }
        }
    }
    return iban;
}

