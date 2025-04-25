from odoo import fields, models
from datetime import timedelta, datetime
import xlsxwriter
from io import BytesIO
import base64

class ReportCheckinSelectionWizard(models.TransientModel):
    _name = 'report.checkin.selection.wizard'
    _transient_max_count = 100
    _description = 'Check-in Counter Report Selection Wizard'

    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.context_today(self) - timedelta(days=30)
    )
    end_date = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    xlsx_file = fields.Binary(string='Excel File', attachment=False)
    xlsx_filename = fields.Char(string='Excel Filename')

    def action_generate_report(self):
        data = {
            'start_date': fields.Date.to_string(self.start_date),
            'end_date': fields.Date.to_string(self.end_date),
            'ids': self.ids,
            'model': 'report.checkin.selection.wizard',
        }
        return self.env.ref('yacl_airline.action_checkin_summary_report').report_action(self, data=data)

    def action_generate_excel_report(self):
        # Get report data
        checkins = self.env['checkin.counter.line'].search([
            ('start_time', '>=', self.start_date),
            ('end_time', '<=', self.end_date),
        ])

        # Prepare data
        summary = {}
        for line in checkins:
            airline = line.checkin_counter_id.airline_id.name
            if airline not in summary:
                summary[airline] = {
                    'airline': airline,
                    'frequency': 0,
                    'unique_flights': set(),
                    'amount': 0
                }

            # for line in checkin.checkin_counter_line_ids:
            summary[airline]['frequency'] += 1
            date = line.end_time.date()
            flight_no = line.flightno_id if line.flightno_id else False
            if flight_no:
                summary[airline]['unique_flights'].add((date, flight_no))
            summary[airline]['amount'] += line.amount

        # Create Excel file
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Check-in Counter Report')

        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': '#1a73e8',
            'font_color': 'white',
            'border': 1
        })

        cell_format = workbook.add_format({
            'align': 'left',
            'border': 1
        })

        number_format = workbook.add_format({
            'align': 'right',
            'border': 1,
            'num_format': '#,##0.00'
        })

        # Headers
        worksheet.write(0, 0, 'International Flight Departure Counter Usage', header_format)
        worksheet.write(2, 0, f"Period: {self.start_date} to {self.end_date}", header_format)

        headers = ['Sr.No.', 'Airlines', 'Frequency', 'Counter Usage Qty', 'Amount USD']
        for col, header in enumerate(headers):
            worksheet.write(4, col, header, header_format)

        # Data
        row = 5
        total_frequency = 0
        total_counter = 0
        total_amount = 0

        for i, (airline, data) in enumerate(summary.items(), 1):
            worksheet.write(row, 0, i, cell_format)
            worksheet.write(row, 1, airline, cell_format)
            worksheet.write(row, 2, len(data['unique_flights']), number_format)
            worksheet.write(row, 3, data['frequency'], number_format)
            worksheet.write(row, 4, data['amount'], number_format)

            total_frequency += len(data['unique_flights'])
            total_counter += data['frequency']
            total_amount += data['amount']
            row += 1

        # Totals
        worksheet.write(row, 0, 'Total', header_format)
        worksheet.write(row, 1, '', header_format)
        worksheet.write(row, 2, total_frequency, number_format)
        worksheet.write(row, 3, total_counter, number_format)
        worksheet.write(row, 4, total_amount, number_format)

        # Adjust column widths
        worksheet.set_column('A:A', 8)
        worksheet.set_column('B:B', 40)
        worksheet.set_column('C:E', 15)

        workbook.close()
        output.seek(0)
        xlsx_data = output.read()
        self.xlsx_file = base64.b64encode(xlsx_data)

        filename = f'Checkin_Counter_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        self.xlsx_filename = filename

        output.seek(0)
        xlsx_data = output.read()
        self.xlsx_file = base64.b64encode(xlsx_data)
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model={self._name}&id={self.id}&field=xlsx_file&filename={filename}&download=true',
            'target': 'self',
        }

    def action_generate_detail_excel_report(self):
        # Get report data
        checkins = self.env['checkin.counter.line'].search([
            ('start_time', '>=', self.start_date),
            ('end_time', '<=', self.end_date),
        ])

        # Create Excel file
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Check-in Counter Report')

        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': '#90EE90',  # Light green background like in the photo
            'border': 1
        })

        cell_format = workbook.add_format({
            'align': 'center',
            'border': 1
        })

        number_format = workbook.add_format({
            'align': 'right',
            'border': 1,
            'num_format': '#,##0'
        })

        # Headers
        headers = ['Sr. No', 'Date', 'Flight No.', 'Aircraft Type', 'Check in Counter Start Time',
                   'Check in Counter Close', 'Service Time', 'Amount']

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Data
        row = 1
        sr_no = 1

        for line in checkins:
            # for line in checkin.checkin_counter_line_ids:
                # Convert datetime to local timezone
            start_time = fields.Datetime.context_timestamp(self, line.start_time)
            end_time = fields.Datetime.context_timestamp(self, line.end_time)

            # Calculate service time in minutes
            service_time = (end_time - start_time).total_seconds() / 60

            worksheet.write(row, 0, sr_no, cell_format)  # Sr. No
            worksheet.write(row, 1, line.start_time.date().strftime('%d.%m.%Y'), cell_format)  # Date
            worksheet.write(row, 2, line.flightno_id if line.flightno_id else '', cell_format)  # Flight No
            worksheet.write(row, 3, line.flight_aircraft or '', cell_format)  # Aircraft Type
            worksheet.write(row, 4, start_time.strftime('%H:%M'), cell_format)  # Start Time
            worksheet.write(row, 5, end_time.strftime('%H:%M'), cell_format)  # Close Time
            worksheet.write(row, 6, f"{int(service_time)} Mins", cell_format)  # Service Time
            worksheet.write(row, 7, line.amount, number_format)  # Amount

            row += 1
            sr_no += 1

        # Adjust column widths
        worksheet.set_column('A:A', 8)  # Sr. No
        worksheet.set_column('B:B', 12)  # Date
        worksheet.set_column('C:C', 15)  # Flight No
        worksheet.set_column('D:D', 15)  # Aircraft Type
        worksheet.set_column('E:F', 20)  # Start/Close Time
        worksheet.set_column('G:G', 15)  # Service Time
        worksheet.set_column('H:H', 10)  # Amount

        workbook.close()
        output.seek(0)
        xlsx_data = output.read()
        self.xlsx_file = base64.b64encode(xlsx_data)

        filename = f'Checkin_Counter_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        self.xlsx_filename = filename

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model={self._name}&id={self.id}&field=xlsx_file&filename={filename}&download=true',
            'target': 'self',
        }