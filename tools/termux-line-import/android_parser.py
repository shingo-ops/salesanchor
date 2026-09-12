"""Parse Android LINE's date headings and tab-separated message headers.

Keep the original export separately. Blank lines and continuation lines are not
discarded. Newlines are normalized to LF; do not claim byte-exact body recovery.
"""
import re
from datetime import datetime

DATE = re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})\s*\([^\r\n)]*\)$")
TIME = re.compile(r"^(\d{1,2}):(\d{2})\t(.*)$")


class AndroidExportError(ValueError):
    pass


def parse_android_export(text):
    day = None
    current = None
    messages = []
    for number, line in enumerate(text.lstrip('\ufeff').splitlines(), 1):
        date_match = DATE.fullmatch(line)
        if date_match:
            try:
                day = datetime(*map(int, date_match.groups())).strftime('%Y-%m-%d')
            except ValueError as error:
                raise AndroidExportError(f'Invalid date at line {number}') from error
            current = None
            continue
        time_match = TIME.fullmatch(line)
        if time_match and day:
            hour, minute = map(int, time_match.groups()[:2])
            if hour > 23 or minute > 59:
                raise AndroidExportError(f'Invalid time at line {number}')
            fields = time_match[3].split('\t', 1)
            if len(fields) == 2:
                sender, body = fields
                if not sender:
                    raise AndroidExportError(f'Missing sender at line {number}')
                system = False
            else:
                sender, body, system = '', fields[0], True
            current = dict(timestamp=f'{day} {hour:02d}:{minute:02d}:00',
                           display_name=sender, body=body, is_system_event=system)
            messages.append(current)
        elif current is not None:
            current['body'] += '\n' + line
        elif day and line:
            raise AndroidExportError(f'Unrecognized record at line {number}')
    if not any(not message['is_system_event'] for message in messages):
        raise AndroidExportError('No Android LINE messages found')
    return messages
