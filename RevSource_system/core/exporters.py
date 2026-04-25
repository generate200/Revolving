"""
Export utilities for generating CSV and Excel files from querysets
"""
import csv
import io
from datetime import datetime
from django.http import HttpResponse
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
import pandas as pd


class DataExporter:
    """Utility class for exporting data to CSV and Excel formats"""
    
    @staticmethod
    def export_to_csv(queryset, fields, filename):
        """
        Export queryset to CSV file
        
        Args:
            queryset: Django queryset to export
            fields: List of field names to include
            filename: Name of the output file
        
        Returns:
            HttpResponse with CSV file
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow(fields)
        
        # Write data rows
        for obj in queryset:
            row = []
            for field in fields:
                if '__' in field:
                    # Handle foreign key fields (e.g., 'product__name')
                    value = obj
                    for part in field.split('__'):
                        value = getattr(value, part, '')
                    row.append(str(value) if value else '')
                else:
                    value = getattr(obj, field, '')
                    # Format datetime objects
                    if hasattr(value, 'strftime'):
                        value = value.strftime('%Y-%m-%d %H:%M')
                    row.append(str(value) if value else '')
            writer.writerow(row)
        
        return response
    
    @staticmethod
    def export_to_excel(queryset, fields, filename, sheet_name='Data'):
        """
        Export queryset to Excel file with formatting
        
        Args:
            queryset: Django queryset to export
            fields: List of field names to include
            filename: Name of the output file
            sheet_name: Name of the Excel sheet
        
        Returns:
            HttpResponse with Excel file
        """
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_name
        
        # Styles
        header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Write headers
        for col, field in enumerate(fields, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = field.replace('_', ' ').title()
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = border
        
        # Write data rows
        for row_num, obj in enumerate(queryset, 2):
            for col, field in enumerate(fields, 1):
                cell = ws.cell(row=row_num, column=col)
                
                if '__' in field:
                    # Handle foreign key fields
                    value = obj
                    for part in field.split('__'):
                        value = getattr(value, part, '')
                    cell.value = str(value) if value else ''
                else:
                    value = getattr(obj, field, '')
                    # Format datetime objects
                    if hasattr(value, 'strftime'):
                        value = value.strftime('%Y-%m-%d %H:%M')
                    cell.value = str(value) if value else ''
                
                cell.border = border
                cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        
        # Auto-adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column].width = adjusted_width
        
        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        
        return response
    
    @staticmethod
    def get_timestamp_filename(base_name):
        """Generate filename with timestamp"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{base_name}_{timestamp}"
