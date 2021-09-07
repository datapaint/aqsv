import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import aqi
import decimal
from decimal import Decimal
import flask
from flask import Flask, render_template
from dash.dependencies import Input, Output

# app-specific packages
from waqi_python import client as aq

server = flask.Flask(__name__)
app = dash.Dash(__name__, server=server)
app.title = 'Silicon Valley Air Quality Dashboard'

#instantiate from the APIs
token = os.environ['AQIPY_TOKEN']
client = aq.WaqiClient()
sjaq = client.get_local_station()
city = sjaq.city.name
score = sjaq.aqi

# 3d geographic box for Silicon Valley
sv = [37.835, -121.743, 37.199, -122.557]

# Instantiate air quality rubric dataframe from http://aqicn.org/api/
aqdf = pd.DataFrame({
  'Min': [0,51,101,151,201,301],
  'Max': [50,100,150,200,300,2000],
  'Level': ['Good', 'Moderate', 'High', 'Unhealthy', 'Extreme', 'Hazardous'],
  'Health': [
             'Air quality is considered satisfactory, and air pollution poses little or no risk',
             'Air quality is acceptable; however, for some pollutants there may be a moderate health concern for a very small number of people who are unusually sensitive to air pollution.',
             'Members of sensitive groups may experience health effects. The general public is not likely to be affected.',
             'Everyone may begin to experience health effects; members of sensitive groups may experience more serious health effects',
             'Health warnings of emergency conditions. The entire population is more likely to be affected.',
             'Health alert: everyone may experience more serious health effects'
  ],
  'Caution': [
              'None',
              'Active children and adults, and people with respiratory disease, such as asthma, should limit prolonged outdoor exertion.',
              'Active children and adults, and people with respiratory disease, such as asthma, should limit prolonged outdoor exertion.',
              'Active children and adults, and people with respiratory disease, such as asthma, should avoid prolonged outdoor exertion; everyone else, especially children, should limit prolonged outdoor exertion',
              'Active children and adults, and people with respiratory disease, such as asthma, should avoid all outdoor exertion; everyone else, especially children, should limit outdoor exertion.',
              'Everyone should avoid all outdoor exertion'
  ],
  'Color': ['#A1C42C', '#FDFD96', '#FFB347', '#FF6961', '#663399', '#8b0000']
})

# Get the list of stations within the Silicon Valley geographic region
def get_sv_stations():
    lat1, lng1, lat2, lng2 = tuple(sv)
    c = client.list_stations_by_bbox(lat1, lng1, lat2, lng2, detailed=True)

    cldf = pd.DataFrame(
    [p.city.name, p.aqi] for p in c)
    cldf.columns = ['Location', 'AQI']

    return cldf

# Compare the air quality score with caution and health labels
def aqi_compare(cdf):

    cdf['Health'] = ''
    cdf['Caution'] = ''
    cdf['Color'] = ''

    for a, row in cdf.iterrows():
        for c, row in aqdf.iterrows():
            if (aqdf['Min'].iloc[c] <= cdf['AQI'].iloc[a]) and (cdf['AQI'].iloc[a] <= aqdf['Max'].iloc[c]):
                cdf['Health'].iloc[a] = aqdf['Health'].iloc[c]
                cdf['Caution'].iloc[a] = aqdf['Caution'].iloc[c]
                cdf['Color'].iloc[a] = aqdf['Color'].iloc[c]

    return cdf

# Create the gui for the individual aqi cards
def create_cards(sdf):

    output = []

    for z, row in sdf.iterrows():
        output.append(html.Li([html.Div(sdf['Location'].iloc[z], className='card-loc'),
                              html.Div(sdf['AQI'].iloc[z], className='card-aqi'),
                              html.Div('24hr exposure to ' + str(round(sdf['Cigarettes'].iloc[z], 2)) + ' Cigarettes', className='card-cigs'),
                              html.Div('Health Advisory', className='card-health-title'),
                              html.Div(sdf['Health'].iloc[z], className='card-health'),
                              html.Div('Caution: ' + sdf['Caution'].iloc[z], className='card-caution')],
                              className='card', style={'background-color': sdf['Color'].iloc[z]}))

    return output

def calc_cigs(gdf):

    cigarette = 1/22 # Taken from http://berkeleyearth.org/air-pollution-and-cigarette-equivalence/
    cigdf = gdf
    cigdf['Cigarettes'] = ''

    for d, row in gdf.iterrows():
        cigdf['Cigarettes'].iloc[d] = decimal.Decimal(aqi.to_cc(aqi.POLLUTANT_PM25, gdf['AQI'].iloc[d], algo=aqi.ALGO_EPA)) * decimal.Decimal(cigarette)

    return cigdf

cities_df = get_sv_stations()
compare_df = aqi_compare(cities_df)
scored_df = calc_cigs(compare_df)
cards = create_cards(scored_df)
app.layout = html.Div(children=[
    html.H1('Silicon Valley Air Quality', className='navigation'),
    html.Ul(children=cards, className='card-layout')
])

if __name__ == '__main__':
    app.run_server(debug=True)
