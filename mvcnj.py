#! /usr/bin/env python3
 
import requests
import bs4
import re
import json
import yaml
import urllib.parse
import os
import sys
from time import sleep
from datetime import datetime

RE_JS_VAR_DECLARATION = re.compile(r' *var +([A-Za-z0-9_]+) += +(\[[^;]*)[;\n\r]')
RE_APT_DATE = re.compile(r'.*Next Available: (.*)')
ID_TAG = {
    'locationData': 'Id',
    'timeData': 'LocationId'
}

def appointment_types():
    r = requests.get('https://telegov.njportal.com/njmvc/AppointmentWizard/')
    page = bs4.BeautifulSoup(r.text, features="html.parser")
    for t in page.find_all('a', class_="text-white text-uppercase"):
        yield (t.attrs["href"].split('/')[-1], t.text.strip())

def format_date(s):
    try:
        date = datetime.strptime(s, '%m/%d/%Y %I:%M %p')
        return date.strftime('%Y-%m-%d'), date.strftime('%H%M')
    except Exception as e:
        print('Warning: Error Parsing date:', e, file=sys.stderr)
        return False

def load_config(config_path):
    config = None
    if not os.path.isfile(config_path):
        print("Config file '%s' not found." % config_path)
        return None
    with open(config_path) as configfile:
        config = yaml.load(configfile, Loader=yaml.SafeLoader)
    return config

def parse_js_apt_data(scripts):
    apts = {}
    for script in scripts:
        for s in str(script).split('\n'):
            if m := RE_JS_VAR_DECLARATION.match(s):
                if m.group(1) in ['locationData', 'timeData']:
                    for td in json.loads(m.group(2)):
                        loc_id = td[ID_TAG[m.group(1)]]
                        if loc_id in apts:
                            apts[loc_id].update(td)
                        else:
                            apts[loc_id] = td
    return apts

def get_apt_location_data(apt_type):
    r = requests.get(f'https://telegov.njportal.com/njmvc/AppointmentWizard/{apt_type}')
    if r.status_code != 200:
        return {}
    page = bs4.BeautifulSoup(r.text, features="html.parser")
    return parse_js_apt_data(page.find_all('script'))

def pretty_apt(apt_data):
    for apt in apt_data:
        appointment_type, _ = apt
        apt = apt_data[apt]
        if m := RE_APT_DATE.match(apt["FirstOpenSlot"]):
            if date := format_date(m.group(1)):
                yield apt, f'{apt["Name"]}: {apt["FirstOpenSlot"].replace("<br/>", "")}\nhttps://telegov.njportal.com/njmvc/AppointmentWizard/{appointment_type}/{apt["Id"]}/{date[0]}/{date[1]}'
                continue
        yield apt, f'{apt["Name"]}: {apt["FirstOpenSlot"].replace("<br/>", "")}\nhttps://telegov.njportal.com/njmvc/AppointmentWizard/{appointment_type}/{apt["Id"]}'

def get_available_apt(apt_data, apt_type):
    return {(apt_type, apt_data[apt]['City']): apt_data[apt] for apt in apt_data if 'No Appointments' not in apt_data[apt]['FirstOpenSlot']}

def notify(apt_data, config):
    cities = [c.lower() for c in config.get('cities', [])]
    if config.get('telegram_notify', False):
        if not config.get('telegram_bot').startswith('bot'):
            config['telegram_bot'] = 'bot' + config['telegram_bot']

    for raw, apt in pretty_apt(apt_data):
        if len(cities) == 0 or raw["City"].lower() in cities or raw["Name"].split(" - ")[0].lower() in cities:
            print(apt)
            if config.get('telegram_notify', False):
                requests.get(f'https://api.telegram.org/{config["telegram_bot"]}/sendMessage?chat_id={config.get("telegram_chat_id")}&text={urllib.parse.quote_plus(apt)}')

def filter_old_apt(new_apt, old_apt):
    return {apt: new_apt[apt] for apt in new_apt if apt not in old_apt}

def main():
    if len(sys.argv) == 2 and sys.argv[1] == '-lstypes':
        print("Appointment types:")
        for n, name in appointment_types():
            print(f"\t{n}: {name}")
        exit(0)

    config = load_config('config.yaml' if len(sys.argv) == 1 else sys.argv[1])
    if not config:
        return 1

    apt_types = config.get('appointment_types', [15])
    if not isinstance(apt_types, list):
        apt_types = [apt_types]
    delay = config.get('refresh_delay_sec', 10)

    prev_apt = {apt_type: {} for apt_type in apt_types}

    while True:
        for apt_type in apt_types:
            apts = get_apt_location_data(apt_type)
            if apts is not None:
                available_apts = get_available_apt(apts, apt_type)
                notify(filter_old_apt(available_apts, prev_apt[apt_type]), config)
                prev_apt[apt_type] = available_apts
        sleep(delay)

if __name__ == "__main__":
    sys.exit(main())
