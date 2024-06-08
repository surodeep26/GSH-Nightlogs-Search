import os
from collections import defaultdict
from astropy.table import Table, Column, vstack
from openpyxl import Workbook
from fuzzywuzzy import process

# Define the base directory
base_dir = './DataTree'

# Function to process data for a specific year
def process_year(year, printing=True):
    '''
    you give func a year and get all objects that have been observed and the number of observation and instruments of obervation
    '''
    year_dir = os.path.join(base_dir, str(year))
    if not os.path.exists(year_dir):
        print(f"No data found for the year {year}.")
        return None

    # Initialize a dictionary to store observation counts and dates
    observations = defaultdict(lambda: {'count': 0, 'dates': defaultdict(list), 'instruments': defaultdict(int)})
    observation_dates = set()

    # Traverse through the directory structure
    for date_dir in os.listdir(year_dir):
        date_path = os.path.join(year_dir, date_dir)
        if os.path.isdir(date_path):
            observation_dates.add(date_dir)
            for instrument in os.listdir(date_path):
                instrument_path = os.path.join(date_path, instrument)
                if os.path.isdir(instrument_path):
                    for target in os.listdir(instrument_path):
                        target_path = os.path.join(instrument_path, target)
                        if os.path.isdir(target_path):
                            observations[target]['count'] += 1
                            observations[target]['dates'][instrument].append(date_dir)
                            observations[target]['instruments'][instrument] += 1

    # Print the total number of observation dates in the year
    total_observation_dates = len(observation_dates)
    if printing:
        print(f"Year {year} - Total number of observation dates: {total_observation_dates}")

    # Prepare data for the Astropy table
    object_names = []
    observation_counts = []
    observation_dates_list = []
    instrument_counts = defaultdict(list)

    # Collect unique instruments
    all_instruments = set()
    for data in observations.values():
        all_instruments.update(data['instruments'].keys())

    # Prepare the table columns
    for target, data in observations.items():
        object_names.append(target)
        observation_counts.append(data['count'])
        observation_dates_list.append(', '.join(f"{instr}: {', '.join(dates)}" for instr, dates in data['dates'].items()))
        for instrument in all_instruments:
            instrument_counts[instrument].append(data['instruments'].get(instrument, 0))

    # Create columns for instrument counts
    instrument_columns = [Column(name=instr, data=counts) for instr, counts in instrument_counts.items()]

    # Create an Astropy table
    t = Table([object_names, observation_counts, observation_dates_list] + instrument_columns, 
              names=['Celestial Object', 'Observations', 'Dates'] + list(all_instruments))
    t.sort(keys='Observations', reverse=True)

    return t

# Function to find observation dates for a specific object across all years
def find_object_observation_dates(object_name, start_year=2006, end_year=2024):
    '''
    give name of object and returns the dates where the object where observed
    '''
    observation_dates = []

    for year in range(start_year, end_year + 1):
        year_table = process_year(year, printing=False)
        if year_table is not None:
            # Check if the object is in the table
            for row in year_table:
                if row['Celestial Object'] == object_name:
                    # Extract dates from the 'Dates' column
                    dates = row['Dates']
                    for date in dates.split(', '):
                        if ':' in date:  # Check if the date contains instrument information
                            instrument, date_list = date.split(': ')
                            observation_dates.extend(date_list.split(', '))
                        else:
                            observation_dates.extend(date.split(', '))
    # print(len(set(observation_dates)))

    return sorted(set(observation_dates))


def findObject(object_name: str, years: list):
    """
    # Example usage:
    object_name = "wasp14"
    years = [2011, 2012, 2013]
    matched_rows = findObject(object_name, years)
    matched_rows

    you give the name and you get the best matched name like internet search
    """
    def fuzzy_search(term, lst):
        # Get all matches using fuzzywuzzy's process.extract
        matches = process.extract(term, lst)
        return matches

    # Initialize an empty list to store tables from different years
    table_list = []

    for year in years:
        # Process the table for the given year
        table = process_year(year)
        
        # Sample list
        my_list = table['Celestial Object']  # No need to convert to list

        # Perform fuzzy search
        search_term = object_name  # Object name provided
        matches = fuzzy_search(search_term, my_list)

        # Filter the table to get rows where the object appears with a good score
        matched_rows = table[[any(x == match[0] for match in matches if match[1] >= 50) for x in table['Celestial Object']]]

        # Add a new column for match scores
        match_scores = [next((match[1] for match in matches if match[0] == x), None) for x in matched_rows['Celestial Object']]
        matched_rows['Match Score'] = match_scores

        # Append matched rows to the table list
        table_list.append(matched_rows)

    # Combine tables from all years
    combined = vstack(table_list)

    # Sort the combined table by match score
    combined.sort('Match Score', reverse=True)
    
    # Return the combined table
    return combined
