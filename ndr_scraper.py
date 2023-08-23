#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
This script fetches race results of dutch horse races from ndr.nl within a
user-defined time interval.

The user specifies the beginning and the end of the interval by entering the
respective year and month of the first and last month. For example '2022-01' 
for January 2022.   

The script creates two csv-files in the working directory which contain
IDs from the ndr.nl website for the events and the results of the races. If 
errors occur a third csv-file will be generated to log the errors.

One can find the csv-files by name. If for example the user inputs a time 
intervall starting with January 2022 and ending with May 2022 the three files
would have the following names:
    events_202201to202205.csv
    results_202201to202205.csv
    errors_202201to202205.csv
'''

import csv
import re
import time
from datetime import datetime


import pandas as pd
import requests
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select



def get_events(months_list, events_filename):
    '''
    Fetch numbers which identify horse racing events in the Netherlands from 
    ndr.nl for a given list of months and write those numbers with additional 
    information (date etc.) to a csv-file.    

    Parameters
    ----------
    months_list : list of str
        A list of strings with year and month (e.g. '2022-1' for January of
        2022)
    events_filename : str
        Name for file to put ndr.nl IDs in.

    Returns
    -------
    None.

    '''
    months_list = [month.split('-') for month in months_list]
    options = Options()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    service = Service("chromedriver.exe")
    driver = webdriver.Chrome(service = service, options = options)
    driver.get('https://ndr.nl/selectieproeven/')
    driver.maximize_window()
    #events_list = []
    for month in months_list:
        my_year, my_month = month[0], month[1]
        # selecting month and year in the two dropdown menus
        select = Select(
            driver.find_element(by = By.NAME, value = 'ndr-koersen-jaar')
        )
        select.select_by_value(my_year)
        select = Select(
          driver.find_element(by = By.NAME, value = 'ndr-koersen-maand')
        )
        select.select_by_value(my_month)
        time.sleep(10)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        course_results = soup.find('div', {'id':'ndr-course-results'})
        course_results = course_results.find_all(
          'li', {'class':re.compile('^ndr-agenda-item.*')}
        )
        events = [
          [
            dag['data-koersdag'],
            dag.find('div', {'class':'ndr-agenda-datum'}).get_text(),
            my_month,
            my_year
          ] for dag in course_results
        ]
        with open(
            events_filename, 'a', newline = '', encoding = 'utf-8'
        ) as fout:
            csvout = csv.writer(fout)
            csvout.writerows(events)
    driver.quit()


def get_event_tables(event_id, col_names):
    '''
    Fetches all result tables for one horse racing event and returns them as
    a list of data frames.

    Parameters
    ----------
    event : str
        ID of an event used at ndr.nl.

    Returns
    -------
    list
        A list of data frames containing race result of one event.
    '''
    url = (
        'https://ndr.nl/wp-content/plugins/ndr/' + 
        'ndr-print.php?action=do_search&koersdag=' + event_id +
        '&koersnr=1&isAgenda=0&paard=false'
    )
      # reading tables and error handling if no tables are present on url:
      # return list with empty data frame if no tables are present
    try:
        tables = pd.read_html(
            url, thousands = None, converters = {'COTE':str, 'na 1e':str}
        )
    except ValueError as err:
        with open(
          errors_csv, mode = 'a', encoding = 'utf-8', newline = ''
        ) as fout:
            csvout = csv.writer(fout)
            csvout.writerow([err, event, url])
        return [pd.DataFrame()]
    # initialize a list to which the resulting dataframes
    # (one per race) will be appended
    df_list = []
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'lxml')
    for idx, table in enumerate(tables):
        result_df = table
        # get race infos which are not integrated into table but above
        result_df['race_number'] = soup.find_all(
          'div', {'class':'ndr-koers-naam'}
        )[idx].get_text()
        result_df['race_time'] = soup.find_all(
          'div', {'class':'ndr-koers-tijd'}
        )[idx].get_text()
        koers_titel = soup.find_all('div', {'class':'ndr-koers-titel'})[idx]
        result_df['race_title'] = koers_titel.find('h2').get_text()
        race_description = koers_titel.find_all(
          'span', {'class':'ndr-koers-omschrijving'}
        )
        if len(race_description) == 1:
            result_df['description1'] = race_description[0].get_text()
        elif len(race_description) == 2:
            result_df['description1'] = race_description[0].get_text()
            result_df['description2'] = race_description[1].get_text()
        elif len(race_description) == 3:
            result_df['description1'] = race_description[0].get_text()
            result_df['description2'] = race_description[1].get_text()
            result_df['description3'] = race_description[2].get_text()
        koers_datum_baan = koers_titel.find_all(
          'span', {'class':'ndr-koers-datum-baan'}
        )
        result_df['date_track'] = koers_datum_baan[0].get_text()
        result_df['race_infos'] = koers_datum_baan[1].get_text()
        result_df['event'] = event
        # all possible columns in result tables from ndr.nl
        #    result_df_cols = list(result_df.columns.values)
        missing_cols = [
            col for col in col_names if col not in result_df.columns
        ]
        result_df.loc[:, missing_cols] = ''
        # reorder columns
        result_df = result_df[all_cols]
        # append df to df_list
        df_list.append(result_df)
    return df_list



# Start of the script with user input:
# scraper fetches dutch horse racing results between two months which the user
# has to declare
print(__doc__)
first_month = input(
    "Please enter the start of the interval by typing year and month " +
    "(e.g. '2013-02' for February 2013): "
)
last_month = input(
    "Please enter the end of the interval by typing year and month " +
    "(e.g. '2013-02' for February 2013): "
)
start_date = first_month + '-01'
end_date = datetime.strptime(last_month + '-01', '%Y-%m-%d').date()
end_date += relativedelta(months = 1)
my_months = pd.date_range(
    start_date, end_date, freq = 'M'
).strftime('%Y-%#m').to_list()
# build names for the three csv files, which are the main output of this script
events_csv = (
    'events_' + first_month.replace('-', '') + 'to' + 
    last_month.replace('-', '') + '.csv'
)
results_csv = (
    'results_' + first_month.replace('-', '') + 'to' + 
    last_month.replace('-', '') + '.csv'
)
errors_csv = (
    'errors_' + first_month.replace('-', '') + 'to' + 
    last_month.replace('-', '') + '.csv'
)
# get all the event or "koersdagen" ids and write to csv file
get_events(my_months, events_csv)
# read all event ids
with open(events_csv, 'rt', encoding = 'utf-8') as fin:
    cin = csv.reader(fin)
    my_events = [row[0] for row in cin]
# get the race result for all events in list and write to a second csv file
all_cols = [
    'event', 'date_track', 'race_time', 'race_number', 'race_title', 
    'description1', 'description2', 'description3', 'race_infos',
    'nr.', 'paard', 'rijder', 'afstand', 'startnummer', 'startnr', 
    'box', 'tijd', 'na 1e', 'Hcap', 'prijs', 'COTE' 
]
with open(results_csv, 'a', newline = '', encoding = 'utf-8') as fout:
    csvout = csv.writer(fout)
    csvout.writerow(all_cols)    
for event in my_events:
    event_dfs = get_event_tables(event, all_cols)
    for df in event_dfs:
        df.to_csv(results_csv, header = False, index = False, mode = 'a')
