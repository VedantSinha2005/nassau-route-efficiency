"""Geographic lookup for US state choropleths and illustrative state-center flows.

Coordinates are approximate geographic state centroids, NOT customer addresses,
travel paths, route distances, or real factory-to-customer network geometry.
"""

US_STATES = {
    'Alabama':('AL',32.8067,-86.7911),'Alaska':('AK',61.3707,-152.4044),
    'Arizona':('AZ',33.7298,-111.4312),'Arkansas':('AR',34.9697,-92.3731),
    'California':('CA',36.1162,-119.6816),'Colorado':('CO',39.0598,-105.3111),
    'Connecticut':('CT',41.5978,-72.7554),'Delaware':('DE',39.3185,-75.5071),
    'District of Columbia':('DC',38.9072,-77.0369),'Florida':('FL',27.7663,-81.6868),
    'Georgia':('GA',33.0406,-83.6431),'Hawaii':('HI',21.0943,-157.4983),
    'Idaho':('ID',44.2405,-114.4788),'Illinois':('IL',40.3495,-88.9861),
    'Indiana':('IN',39.8494,-86.2583),'Iowa':('IA',42.0115,-93.2105),
    'Kansas':('KS',38.5266,-96.7265),'Kentucky':('KY',37.6681,-84.6701),
    'Louisiana':('LA',31.1695,-91.8678),'Maine':('ME',44.6939,-69.3819),
    'Maryland':('MD',39.0639,-76.8021),'Massachusetts':('MA',42.2302,-71.5301),
    'Michigan':('MI',43.3266,-84.5361),'Minnesota':('MN',45.6945,-93.9002),
    'Mississippi':('MS',32.7416,-89.6787),'Missouri':('MO',38.4561,-92.2884),
    'Montana':('MT',46.9219,-110.4544),'Nebraska':('NE',41.1254,-98.2681),
    'Nevada':('NV',38.3135,-117.0554),'New Hampshire':('NH',43.4525,-71.5639),
    'New Jersey':('NJ',40.2989,-74.5210),'New Mexico':('NM',34.8405,-106.2485),
    'New York':('NY',42.1657,-74.9481),'North Carolina':('NC',35.6301,-79.8064),
    'North Dakota':('ND',47.5289,-99.7840),'Ohio':('OH',40.3888,-82.7649),
    'Oklahoma':('OK',35.5653,-96.9289),'Oregon':('OR',44.5720,-122.0709),
    'Pennsylvania':('PA',40.5908,-77.2098),'Rhode Island':('RI',41.6809,-71.5118),
    'South Carolina':('SC',33.8569,-80.9450),'South Dakota':('SD',44.2998,-99.4388),
    'Tennessee':('TN',35.7478,-86.6923),'Texas':('TX',31.0545,-97.5635),
    'Utah':('UT',40.1500,-111.8624),'Vermont':('VT',44.0459,-72.7107),
    'Virginia':('VA',37.7693,-78.1700),'Washington':('WA',47.4009,-121.4905),
    'West Virginia':('WV',38.4912,-80.9545),'Wisconsin':('WI',44.2685,-89.6165),
    'Wyoming':('WY',42.7560,-107.3025),
}
CANADA_PROVINCES = {'Alberta':'AB','British Columbia':'BC','Manitoba':'MB',
    'New Brunswick':'NB','Newfoundland and Labrador':'NL','Nova Scotia':'NS',
    'Ontario':'ON','Prince Edward Island':'PE','Quebec':'QC','Saskatchewan':'SK',
    'Northwest Territories':'NT','Nunavut':'NU','Yukon':'YT'}
STATE_BY_CODE = {value[0]:name for name,value in US_STATES.items()}
PROVINCE_BY_CODE = {value:name for name,value in CANADA_PROVINCES.items()}


def standardize_state(name, country):
    value = str(name).strip()
    if country == 'United States':
        return STATE_BY_CODE.get(value.upper(), value)
    if country == 'Canada':
        return PROVINCE_BY_CODE.get(value.upper(), value)
    return value


def get_us_code(name):
    return US_STATES.get(name, (None,None,None))[0]
