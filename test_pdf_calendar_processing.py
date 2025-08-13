#!/usr/bin/env python3
"""
Test script for PDF calendar processing functionality.
This script tests the PDF text extraction and date parsing capabilities.
"""

import os
import sys
from datetime import datetime, date

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_date_parsing():
    """Test the date parsing functionality."""
    print("🧪 Testing date parsing functionality...")
    
    # Test various date formats
    test_dates = [
        "January 15 2024",
        "Jan 15, 2024", 
        "01/15/2024",
        "01-15-2024",
        "2024-01-15",
        "January 15",  # No year (should use current year)
        "Jan 15",      # No year (should use current year)
        "01/15",       # No year (should use current year)
        "01-15"        # No year (should use current year)
    ]
    
    current_year = datetime.now().year
    
    for date_str in test_dates:
        try:
            parsed_date = parse_date_string(date_str)
            if parsed_date:
                print(f"✅ '{date_str}' -> {parsed_date}")
            else:
                print(f"❌ '{date_str}' -> Failed to parse")
        except Exception as e:
            print(f"❌ '{date_str}' -> Error: {str(e)}")
    
    print()

def test_pattern_matching():
    """Test the regex pattern matching for calendar events."""
    print("🧪 Testing pattern matching...")
    
    # Test text content
    test_text = """
    School Year 2024-2025 Calendar
    
    Quarter 1: August 26, 2024 - October 25, 2024
    Quarter 2: October 28, 2024 - January 17, 2025
    Quarter 3: January 20, 2025 - March 28, 2025
    Quarter 4: March 31, 2025 - June 6, 2025
    
    Semester 1: August 26, 2024 - January 17, 2025
    Semester 2: January 20, 2025 - June 6, 2025
    
    Holidays:
    September 2, 2024: Labor Day
    October 14, 2024: Columbus Day
    November 11, 2024: Veterans Day
    November 28, 2024: Thanksgiving
    December 25, 2024: Christmas
    January 1, 2025: New Year
    January 20, 2025: Martin Luther King Jr. Day
    February 17, 2025: Presidents Day
    May 26, 2025: Memorial Day
    July 4, 2025: Independence Day
    
    Breaks:
    December 23, 2024 - January 3, 2025: Winter Break
    March 17, 2025 - March 21, 2025: Spring Break
    June 9, 2025 - August 25, 2025: Summer Break
    
    Professional Development:
    August 23, 2024: Professional Development
    January 17, 2025: PD Day
    June 6, 2025: Staff Development
    
    Parent-Teacher Conferences:
    October 10, 2024: Parent-Teacher Conference
    March 13, 2025: PTC
    
    Early Dismissal:
    December 20, 2024: Early Dismissal
    June 5, 2025: Early Dismissal
    
    No School:
    September 2, 2024: No School
    December 25, 2024: School Closed
    """
    
    print("📝 Test text content:")
    print(test_text)
    print()
    
    # Test the extraction functions
    print("🔍 Testing extraction functions...")
    
    # Test school year extraction
    school_year_dates = extract_school_year_dates(test_text, test_text.lower())
    print(f"✅ School Year: {school_year_dates}")
    
    # Test academic periods extraction
    academic_periods = extract_academic_periods(test_text, test_text.lower())
    print(f"✅ Quarters: {len(academic_periods['quarters'])} found")
    print(f"✅ Semesters: {len(academic_periods['semesters'])} found")
    
    # Test holidays and events extraction
    events = extract_holidays_and_events(test_text, test_text.lower())
    print(f"✅ Holidays: {len(events['holidays'])} found")
    print(f"✅ Parent-Teacher Conferences: {len(events['parent_teacher_conferences'])} found")
    print(f"✅ Early Dismissal: {len(events['early_dismissal'])} found")
    print(f"✅ No School: {len(events['no_school'])} found")
    
    # Test breaks extraction
    breaks = extract_breaks_and_vacations(test_text, test_text.lower())
    print(f"✅ Breaks: {len(breaks['breaks'])} found")
    
    # Test professional development extraction
    pd_dates = extract_professional_dates(test_text, test_text.lower())
    print(f"✅ Professional Development: {len(pd_dates['professional_development'])} found")
    
    print()

def parse_date_string(date_str):
    """Parse various date string formats into a date object."""
    if not date_str:
        return None
    
    import re
    
    # Remove extra whitespace and common punctuation
    date_str = re.sub(r'[,\s]+', ' ', date_str.strip())
    
    # Common date formats
    date_formats = [
        '%B %d %Y',      # January 15 2024
        '%b %d %Y',      # Jan 15 2024
        '%B %d, %Y',     # January 15, 2024
        '%b %d, %Y',     # Jan 15, 2024
        '%m/%d/%Y',      # 01/15/2024
        '%m-%d-%Y',      # 01-15-2024
        '%Y-%m-%d',      # 2024-01-15
        '%B %d',         # January 15 (assume current year)
        '%b %d',         # Jan 15 (assume current year)
        '%m/%d',         # 01/15 (assume current year)
        '%m-%d'          # 01-15 (assume current year)
    ]
    
    current_year = datetime.now().year
    
    for fmt in date_formats:
        try:
            if fmt in ['%B %d', '%b %d', '%m/%d', '%m-%d']:
                # For formats without year, assume current year
                parsed_date = datetime.strptime(date_str, fmt)
                return date(current_year, parsed_date.month, parsed_date.day)
            else:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.date()
        except ValueError:
            continue
    
    return None

def extract_school_year_dates(text_content, text_lower):
    """Extract school year start and end dates."""
    import re
    
    dates = {
        'school_year_start': None,
        'school_year_end': None
    }
    
    # Common patterns for school year dates
    patterns = [
        r'school\s+year\s+(\d{4})[-\s]+(\d{4})',
        r'(\d{4})[-\s]+(\d{4})\s+school\s+year',
        r'(\d{4})[-\s]+(\d{4})\s+academic\s+year',
        r'(\d{4})[-\s]+(\d{4})\s+calendar'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            year1, year2 = int(match.group(1)), int(match.group(2))
            # Assume school year starts in August/September and ends in May/June
            dates['school_year_start'] = date(year1, 8, 1)  # August 1st
            dates['school_year_end'] = date(year2, 6, 30)   # June 30th
            break
    
    return dates

def extract_academic_periods(text_content, text_lower):
    """Extract quarter and semester dates."""
    import re
    
    periods = {
        'quarters': [],
        'semesters': []
    }
    
    # Quarter patterns
    quarter_patterns = [
        r'quarter\s+(\d)[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})',
        r'q(\d)[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})[:\s]*quarter\s+(\d)'
    ]
    
    # Semester patterns
    semester_patterns = [
        r'semester\s+(\d)[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})',
        r's(\d)[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    
    # Extract quarters
    for pattern in quarter_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                if len(match.groups()) == 3:
                    if 'quarter' in pattern or 'q' in pattern:
                        quarter_num = int(match.group(1))
                        start_date = parse_date_string(match.group(2))
                        end_date = parse_date_string(match.group(3))
                    else:
                        start_date = parse_date_string(match.group(1))
                        end_date = parse_date_string(match.group(2))
                        quarter_num = int(match.group(3))
                    
                    if start_date and end_date:
                        periods['quarters'].append({
                            'name': f'Q{quarter_num}',
                            'start_date': start_date,
                            'end_date': end_date
                        })
            except:
                continue
    
    # Extract semesters
    for pattern in semester_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                semester_num = int(match.group(1))
                start_date = parse_date_string(match.group(2))
                end_date = parse_date_string(match.group(3))
                
                if start_date and end_date:
                    periods['semesters'].append({
                        'name': f'S{semester_num}',
                        'start_date': start_date,
                        'end_date': end_date
                    })
            except:
                continue
    
    return periods

def extract_holidays_and_events(text_content, text_lower):
    """Extract holidays and special event dates."""
    import re
    
    events = {
        'holidays': [],
        'parent_teacher_conferences': [],
        'early_dismissal': [],
        'no_school': []
    }
    
    # Common holiday patterns
    holiday_patterns = [
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*labor\s+day', 'Labor Day'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*columbus\s+day', 'Columbus Day'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*veterans\s+day', 'Veterans Day'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*thanksgiving', 'Thanksgiving'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*christmas', 'Christmas'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*new\s+year', 'New Year'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*martin\s+luther\s+king', 'Martin Luther King Jr. Day'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*presidents\s+day', 'Presidents Day'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*memorial\s+day', 'Memorial Day'),
        (r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*independence\s+day', 'Independence Day')
    ]
    
    for pattern, holiday_name in holiday_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                date_str = match.group(1)
                parsed_date = parse_date_string(date_str)
                if parsed_date:
                    events['holidays'].append({
                        'name': holiday_name,
                        'date': parsed_date
                    })
            except:
                continue
    
    # Parent-teacher conference patterns
    ptc_patterns = [
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*parent[-\s]*teacher\s+conference',
        r'parent[-\s]*teacher\s+conference[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
        r'ptc[:\s]*(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    
    for pattern in ptc_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                date_str = match.group(1)
                parsed_date = parse_date_string(date_str)
                if parsed_date:
                    events['parent_teacher_conferences'].append({
                        'name': 'Parent-Teacher Conference',
                        'date': parsed_date
                    })
            except:
                continue
    
    # Early dismissal patterns
    early_patterns = [
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*early\s+dismissal',
        r'early\s+dismissal[:\s]*(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    
    for pattern in early_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                date_str = match.group(1)
                parsed_date = parse_date_string(date_str)
                if parsed_date:
                    events['early_dismissal'].append({
                        'name': 'Early Dismissal',
                        'date': parsed_date
                    })
            except:
                continue
    
    # No school patterns
    no_school_patterns = [
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*no\s+school',
        r'no\s+school[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*school\s+closed',
        r'school\s+closed[:\s]*(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    
    for pattern in no_school_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                date_str = match.group(1)
                parsed_date = parse_date_string(date_str)
                if parsed_date:
                    events['no_school'].append({
                        'name': 'No School',
                        'date': parsed_date
                    })
            except:
                continue
    
    return events

def extract_breaks_and_vacations(text_content, text_lower):
    """Extract vacation and break dates."""
    import re
    
    breaks = {
        'breaks': []
    }
    
    # Break patterns
    break_patterns = [
        r'(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})[:\s]*winter\s+break',
        r'winter\s+break[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})[:\s]*spring\s+break',
        r'spring\s+break[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})[:\s]*summer\s+break',
        r'summer\s+break[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})[:\s]*fall\s+break',
        r'fall\s+break[:\s]*(\w+\s+\d{1,2},?\s+\d{4})[-\s]+(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    
    for pattern in break_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                start_date = parse_date_string(match.group(1))
                end_date = parse_date_string(match.group(2))
                
                if start_date and end_date:
                    # Determine break type from the pattern
                    if 'winter' in pattern:
                        break_name = 'Winter Break'
                    elif 'spring' in pattern:
                        break_name = 'Spring Break'
                    elif 'summer' in pattern:
                        break_name = 'Summer Break'
                    elif 'fall' in pattern:
                        break_name = 'Fall Break'
                    else:
                        break_name = 'School Break'
                    
                    breaks['breaks'].append({
                        'name': break_name,
                        'start_date': start_date,
                        'end_date': end_date
                    })
            except:
                continue
    
    return breaks

def extract_professional_dates(text_content, text_lower):
    """Extract professional development and staff dates."""
    import re
    
    prof_dates = {
        'professional_development': []
    }
    
    # Professional development patterns
    pd_patterns = [
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*professional\s+development',
        r'professional\s+development[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*pd\s+day',
        r'pd\s+day[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*staff\s+development',
        r'staff\s+development[:\s]*(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})[:\s]*teacher\s+workday',
        r'teacher\s+workday[:\s]*(\w+\s+\d{1,2},?\s+\d{4})'
    ]
    
    for pattern in pd_patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                date_str = match.group(1)
                parsed_date = parse_date_string(date_str)
                if parsed_date:
                    prof_dates['professional_development'].append({
                        'name': 'Professional Development',
                        'date': parsed_date
                    })
            except:
                continue
    
    return prof_dates

if __name__ == "__main__":
    print("🚀 Testing PDF Calendar Processing Functionality")
    print("=" * 60)
    
    test_date_parsing()
    test_pattern_matching()
    
    print("🎉 Testing completed!")
