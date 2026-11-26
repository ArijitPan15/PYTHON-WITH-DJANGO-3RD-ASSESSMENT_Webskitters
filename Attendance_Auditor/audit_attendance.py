import csv
import re
import time
from datetime import datetime, timedelta
from typing import Callable, TextIO


class InvalidHeaderError(Exception):
    pass

    
class InvalidTimestampError(Exception):
    pass


# Decorator to measure the execution time of the audit function.
def execution_time(func: Callable[[], None]) -> Callable[[], None]:
    def wrapper() -> None:
        start_time = time.time()
        try:
            func()
        finally:
            print('Execution time:', time.time() - start_time)
    return wrapper


def parse_punch_time(value: str) -> datetime:
    try:
        punch_time = datetime.strptime(value, '%d-%m-%Y %H:%M:%S')
        # Check the exact timestamp format after parsing.
        if punch_time.strftime('%d-%m-%Y %H:%M:%S') != value:
            raise ValueError
        return punch_time
    except ValueError:
        raise InvalidTimestampError('Invalid timestamp')


def validate_row(row: dict[str, str]) -> str:
    for value in row.values():
        if not value:
            return 'Missing or empty field'
    if not re.fullmatch(r'E[0-9]{3}', row['employee_id']):
        return 'Invalid employee ID'
    device_ip = row['device_ip']
    if not re.fullmatch(r'([0-9]{1,3}\.){3}[0-9]{1,3}', device_ip):
        return 'Invalid IP'
    # Each part of an IPv4 address must be between 0 and 255.
    for octet in device_ip.split('.'):
        if int(octet) > 255:
            return 'Invalid IP'
    if row['punch_type'] not in ['IN', 'OUT']:
        return 'Invalid punch type'
    if not re.fullmatch(r'KOL-[A-Z]', row['building_code']):
        return 'Invalid building code'
    try:
        parse_punch_time(row['punch_time'])
    except InvalidTimestampError as error:
        return str(error)
    return ''


def get_punch_time(row: dict[str, str]) -> datetime:
    return parse_punch_time(row['punch_time'])


# Write multiple report lines using *args.
def write_report(file: TextIO, *lines: str) -> None:
    for line in lines:
        file.write(str(line) + '\n')


@execution_time
def audit_attendance() -> None:
    field_names = ['employee_id', 'employee_name', 'device_ip',
              'punch_type', 'punch_time', 'building_code']
    # Read the input CSV and validate its header.
    with open('raw_punches.csv', 'r', newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != field_names:
            raise InvalidHeaderError('Invalid CSV header')
        raw_rows = list(reader)

    valid_rows: list[dict[str, str]] = []
    nonduplicate_rows: list[dict[str, str]] = []
    clean_rows: list[dict[str, str]] = []
    rejected_rows: list[dict[str, str]] = []
    status_counts: dict[str, int] = {'Clean': 0, 'Duplicate': 0, 'Suspicious': 0, 'Rejected': 0}

    # Copy and validate each row without changing the original data.
    for original_row in raw_rows:
        row = original_row.copy()
        clean_row: dict[str, str] = {}
        for field in field_names:
            clean_row[field] = (row[field] or '').strip()
        if None in row:
            validation_error = 'Extra columns'
        else:
            validation_error = validate_row(clean_row)
        row = clean_row
        row['working_date'] = ''
        if validation_error:
            row['status'] = 'Rejected'
            row['reason'] = validation_error
            rejected_rows.append(row)
        else:
            valid_rows.append(row)

    # Sort valid punches in chronological order before checking duplicates.
    valid_rows.sort(key=get_punch_time)
    previous_punches: dict[tuple[str, str, str], datetime] = {}
    employee_buildings: dict[tuple[str, str], set[str]] = {}

    for row in valid_rows:
        punch_time = get_punch_time(row)
        punch_date = punch_time.strftime('%d-%m-%Y')
        row['working_date'] = punch_date
        # Assign early morning OUT punches to the previous working date.
        if row['punch_type'] == 'OUT' and punch_time.hour < 4:
            row['working_date'] = (punch_time - timedelta(days=1)).strftime('%d-%m-%Y')

        # Use a set to store unique buildings for each employee and date.
        building_key = (row['employee_id'], punch_date)
        if building_key not in employee_buildings:
            employee_buildings[building_key] = set()
        employee_buildings[building_key].add(row['building_code'])

        # Compare punches with the same employee, punch type and device.
        punch_key = (row['employee_id'], row['punch_type'], row['device_ip'])
        if punch_key in previous_punches and (punch_time - previous_punches[punch_key]).total_seconds() <= 60:
            row['status'] = 'Duplicate'
            row['reason'] = 'Repeated punch within 60 seconds'
            rejected_rows.append(row)
        else:
            nonduplicate_rows.append(row)
        previous_punches[punch_key] = punch_time

    # Check nonduplicate punches for building switches and day rollover.
    for row in nonduplicate_rows:
        punch_time = get_punch_time(row)
        punch_date = punch_time.strftime('%d-%m-%Y')
        building_key = (row['employee_id'], punch_date)
        reasons = []
        if len(employee_buildings[building_key]) > 1:
            reasons.append('Building switch')
        if row['working_date'] != punch_date:
            reasons.append('Day rollover')
        if reasons:
            row['status'] = 'Suspicious'
            row['reason'] = ', '.join(reasons)
            rejected_rows.append(row)
        else:
            row['status'] = 'Clean'
            row['reason'] = ''
            clean_rows.append(row)

    # Count each status and prepare the employee-wise summary.
    audited_rows = clean_rows + rejected_rows
    employees = {row['employee_id'] or 'Unknown' for row in audited_rows}
    employee_summary = {employee_id: status_counts.copy() for employee_id in employees}
    for row in audited_rows:
        employee_id = row['employee_id'] or 'Unknown'
        status = row['status']
        status_counts[status] += 1
        employee_summary[employee_id][status] += 1

    # Write clean records and all flagged records to separate CSV files.
    field_names += ['working_date', 'status', 'reason']
    for file_name, output_rows in [('clean_punches.csv', clean_rows), ('rejected_punches.csv', rejected_rows)]:
        with open(file_name, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=field_names)
            writer.writeheader()
            writer.writerows(output_rows)

    # Generate the final audit report.
    with open('audit_summary.txt', 'w', encoding='utf-8') as file:
        write_report(file, 'Attendance Audit Summary', 'Total rows: ' + str(len(raw_rows)))
        for status in status_counts:
            write_report(file, status + ': ' + str(status_counts[status]))
        for employee_id in sorted(employee_summary):
            write_report(file, '', 'Employee ID: ' + employee_id)
            for status in employee_summary[employee_id]:
                write_report(file, status + ': ' + str(employee_summary[employee_id][status]))
    print('Total rows:', len(raw_rows))
    print(status_counts)
    print('Audit completed')


if __name__ == '__main__':
    try:
        audit_attendance()
    except (OSError, InvalidHeaderError, csv.Error, UnicodeError) as error:
        print(error)
