#!/usr/bin/env python

__author__ = "Robert Bisek"
__copyright__ = "2019 Robert Bisek"
__version__ = "19.4.27"
__status__ = "Development"

""" Script to Generate Problem DataFrame """

import datetime
import getpass
import time
import sys

import pandas as pd
import plotly
import plotly.graph_objs as go

from pyzabbix import ZabbixAPI


def generate_data(args):
    """ Generate Pandas dataframe with either <DAILY> or <WEEKLY> data """

    # Generate Today's date (MM/DD/YYYY) in Unix time (##########)
    todays_date = int(time.mktime(datetime.date.today().timetuple()))

    # Gather Zabbix Username and Password Currently
    user_name = input('Username: ')
    user_password = getpass.getpass('Password: ', stream=None)

    # Access Zabbix API
    zbx_url = input('URL for Zabbix API: ')
    zapi = ZabbixAPI(zbx_url)
    zapi.login(user_name, user_password)

    if args == 'DAILY':
        days = 86400
    elif args == 'WEEKLY':
        days = 604800
    else:
        days = 0
        print('Wrong report argument.\nUse either DAILY OR WEEKLY')

    events = zapi.event.get(time_from=todays_date-days,
                            time_till=todays_date,
                            selectHosts=['host'],
                            output='extend',
                            sortfield=['clock', 'eventid'],
                            sortorder='ASC')

    # Create Pandas DataFrame
    d_f = pd.DataFrame(events)

    # Begin Cleaning Data
    d_f['clock'] = pd.to_datetime(d_f['clock'], unit='s')
    d_f2 = pd.DataFrame(d_f['hosts'])
    d_f2['hosts'] = pd.Series(d_f['hosts']).astype(str)
    d_f2['hosts'] = pd.Series(d_f2['hosts']).str.upper()
    d_f2['hosts'] = d_f2['hosts'].str.strip('[]')
    d_f2['hosts'] = d_f2['hosts'].str.strip('{}')
    d_f2 = d_f2['hosts'].str.split(" ", n=3, expand=True)
    d_f2[3] = d_f2[3].str.strip("''")
    d_f['hosts'] = d_f2[3]
    d_f['severity'] = pd.Series(d_f['severity']).astype(str)
    d_f['severity'] = pd.Series(d_f['severity']).replace('0', 'Not Classified')
    d_f['severity'] = pd.Series(d_f['severity']).replace('1', 'Information')
    d_f['severity'] = pd.Series(d_f['severity']).replace('2', 'Warning')
    d_f['severity'] = pd.Series(d_f['severity']).replace('3', 'Average')
    d_f['severity'] = pd.Series(d_f['severity']).replace('4', 'High')
    d_f['severity'] = pd.Series(d_f['severity']).replace('5', 'Disaster')

    # Create Resolution Time DataFrame
    d_f3 = d_f[['r_eventid']].copy()
    d_f3['eventid'] = d_f3['r_eventid']
    d_f3.drop('r_eventid', axis=1, inplace=True)
    d_f4 = d_f[['eventid', 'clock']].copy()
    d_f5 = d_f3.merge(d_f4, on='eventid')

    # Rename Resolution Time DataFrame and incorporate into primary DataFrame
    d_f5['r_eventid'] = d_f5['eventid']
    d_f5['r_clock'] = d_f5['clock']
    d_f5.drop('eventid', axis=1, inplace=True)
    d_f5.drop('clock', axis=1, inplace=True)
    d_f = d_f.merge(d_f5, on='r_eventid')

    # Remove unnecessary columns
    d_f = pd.DataFrame(d_f).drop(['eventid',
                                  'source',
                                  'object',
                                  'objectid',
                                  'ns',
                                  'r_eventid',
                                  'c_eventid',
                                  'correlationid',
                                  'userid',
                                  'suppressed',
                                  'value'], axis=1)

    # Problems by Severity pie chart
    d_f6 = d_f[['severity']].copy()
    d_f6['colors'] = d_f6[['severity']]
    d_f6['colors'] = pd.Series(d_f6['colors']).replace('Not Classified', '#97AAB3')
    d_f6['colors'] = pd.Series(d_f6['colors']).replace('Information', '#7499FF')
    d_f6['colors'] = pd.Series(d_f6['colors']).replace('Warning', '#FFC859')
    d_f6['colors'] = pd.Series(d_f6['colors']).replace('Average', '#FFA059')
    d_f6['colors'] = pd.Series(d_f6['colors']).replace('High', '#E97659')
    d_f6['colors'] = pd.Series(d_f6['colors']).replace('Disaster', '#E45959')
    index = d_f6['severity'].value_counts()
    values = index.tolist()
    labels = index.keys().tolist()
    colors = d_f6['colors'].value_counts().keys().tolist()
    
    labels=labels
    values=values
    colors=colors

    trace = [go.Pie(labels=labels,
                    values=values,
                    showlegend=False,
                    hoverinfo='label+percent',
                    textinfo='value',
                    textfont=dict(size=20),
                    hole=.4,
                    marker=dict(colors=colors,
                                line=dict(color='#000000', width=1)))]
    
    layout = go.Layout(title='Percentage by Severity',
                       legend=dict(borderwidth=5))

    fig = go.Figure(data=trace, layout=layout)

    plotly.offline.plot(fig, filename='test.html')


    
if __name__ == "__main__":
    generate_data(str(sys.argv[1]))
