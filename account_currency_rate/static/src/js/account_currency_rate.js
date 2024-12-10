//** @odoo-module */
import { registry } from "@web/core/registry";
import { many2OneField, Many2OneField } from "../many2one/many2one_field";

export class Many2OneFieldCurrency extends Many2OneField {
    console.log("Many2OneFieldCurrency");
    setup() {
        super.setup();
        console.log("Many2OneFieldCurrency setup");
        this.currency = this.props.currency;
    }
}

