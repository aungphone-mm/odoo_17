from odoo import api, fields, models


class TopTenOutstandingWizard(models.TransientModel):
    _name = 'top.ten.outstanding.wizard'
    _description = 'Wizard for Top Ten Outstanding Report'

    # You can add filters here if needed in the future
    # For example, company_id, date range, etc.

    def action_generate_report(self):
        """Generate the top ten outstanding report"""
        # The report doesn't need specific parameters since it always shows top 10
        # But we could pass filters here in the future if needed
        return self.env.ref('yacl_airline.action_report_top_ten_outstanding').report_action(self, data={}, config=False)