import time
import json
import requests
import threading
from   datetime                  import datetime
from   icalendar                 import Calendar, Event
from   pytz                      import timezone
from   flask                     import Flask
from   googleapiclient.discovery import build
from   httplib2                  import Http
from   oauth2client              import file, client, tools

WUNDERGROUND_API = "XXXX"
CALENDAR_ID      = "XXXX@group.calendar.google.com"
SCOPES           = 'https://www.googleapis.com/auth/calendar'
DESC             = "Powered by https://ansi.23-5.eu, weather data from https://www.wunderground.com based on the https://motionlab.berlin weatherstation. Live conditions: https://www.wunderground.com/personal-weather-station/dashboard?ID=IBERLIN1705. Forecast: https://www.wunderground.com/forecast/de/berlin-treptow/IBERLIN1705" 
EVENT            = {
                    'summary'    : '',
                    'description': DESC,
                    'start': {
                              'dateTime' : '',
                              'timeZone' : 'Europe/Berlin',
                             },
                    'end':   {
                              'dateTime' : '',
                              'timeZone' : 'Europe/Berlin',
                             },
                   }


class w2ical(threading.Thread):

    def __init__(self):
        super(w2ical, self).__init__()
        self.setDaemon(True)
        self._cal = Calendar()
        self.start()

    def run(self):
        while True:
            self._newcal = Calendar()
            self.deleteAllCalendarEntries()
            fw = self.updateForecast()
            hw = self.updateHourly()
         
            if fw and hw:
                self._cal = self._newcal
                time.sleep(3 * 60 * 60)
            else:
                print("problem with wunderground")
                time.sleep(30)

    def getICal(self):
        return self._cal.to_ical()

    def getService(self):
        store = file.Storage('token.json')
        creds = store.get()

        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
            creds = tools.run_flow(flow, store)
        
        return build('calendar', 'v3', http=creds.authorize(Http()))

    def deleteAllCalendarEntries(self):
        service       = self.getService()
        events_result = service.events().list(calendarId=CALENDAR_ID, maxResults=100, singleEvents=True, orderBy='startTime').execute()
        events        = events_result.get('items', [])
        
        for e in events:
            service.events().delete(calendarId=CALENDAR_ID, eventId=e['id']).execute()

    def addCalendarEnties(self, event):
        service = self.getService()
        service.events().insert(calendarId=CALENDAR_ID, body=event).execute()

    def updateForecast(self):
        try:
            data   = json.loads(requests.get("http://api.wunderground.com/api/" + WUNDERGROUND_API + "/forecast10day/q/pws:IBERLIN1705.json").content)
        except:
            print("Error in Forecast")
            return False

        for e in data['forecast']['simpleforecast']['forecastday']:
            day        = e['date']['day']
            month      = e['date']['month']
            year       = e['date']['year'] 
            conditions = e['conditions']
            humidity   = e['avehumidity']
            high       = e['high']['celsius']
            low        = e['low']['celsius']
            snow       = e['snow_allday']['cm']
            rain       = e['qpf_allday']['mm']
            
            # ical
            event = Event()    
            event.add('summary', "%s-%sC %s%% Rain:%s Snow:%s %s" % (low, high, humidity, rain, snow, conditions))
            event.add('dtstart', datetime(year,month,day,6, 0,0,0,timezone('Europe/Berlin')))
            event.add('dtend',   datetime(year,month,day,6,15,0,0,timezone("Europe/Berlin")))
            event.add('description', DESC)
            self._newcal.add_component(event)

            #google
            ge = EVENT
            ge['summary']           = "%s-%sC %s%% Rain:%s Snow:%s %s" % (low, high, humidity, rain, snow, conditions)
            ge['start']['dateTime'] = '%s-%s-%sT06:00:00' % (year, month, day)
            ge['end'  ]['dateTime'] = '%s-%s-%sT06:15:00' % (year, month, day)
            self.addCalendarEnties(ge)

        return True

    def updateHourly(self):

        try:
            data = json.loads(requests.get("http://api.wunderground.com/api/" + WUNDERGROUND_API + "/hourly10day/q/pws:IBERLIN1705.json").content)
        except:
            print("Error in hourly update")
            return False

        for e in data['hourly_forecast']:
            hour     = int(e['FCTTIME']['hour'])
            day      = int(e['FCTTIME']['mday'])
            month    = int(e['FCTTIME']['mon'])
            year     = int(e['FCTTIME']['year'])
            rain     = float(e['qpf']['metric'])
            snow     = float(e['snow']['metric'])
            temp     = float(e['temp']['metric'])
            wind     = float(e['wspd']['metric'])
            dewpoint = float(e['dewpoint']['metric'])
            uvi      = float(e['uvi'])
            humidity = float(e['humidity'])

            if rain > 0.0:
                #ical
                event = Event()    
                event.add('summary', "Rain: %.0f mm" % (rain))
                event.add('dtstart', datetime(year, month, day, hour,  0, 0, 0, timezone('Europe/Berlin')))
                event.add('dtend',   datetime(year, month, day, hour, 59, 0, 0, timezone("Europe/Berlin")))
                event.add('description', DESC)
                self._newcal.add_component(event)
                #google
                ge = EVENT
                ge['summary']           = "Rain: %.0f mm" % (rain)
                ge['start']['dateTime'] = '%02d-%02d-%02dT%02d:00:00' % (year, month, day, hour)
                ge['end'  ]['dateTime'] = '%02d-%02d-%02dT%02d:59:00' % (year, month, day, hour)
                self.addCalendarEnties(ge)

            if snow > 0.0:
                #ical
                event = Event()    
                event.add('summary', "Snow: %.0f cm" % (snow))
                event.add('dtstart', datetime(year, month, day, hour,  0, 0, 0, timezone('Europe/Berlin')))
                event.add('dtend',   datetime(year, month, day, hour, 59, 0, 0, timezone("Europe/Berlin")))
                event.add('description', DESC)
                self._newcal.add_component(event)
                #google
                ge = EVENT
                ge['summary']           = "Snow: %.0f cm" % (snow)
                ge['start']['dateTime'] = '%02d-%02d-%02dT%02d:00:00' % (year, month, day, hour)
                ge['end'  ]['dateTime'] = '%02d-%02d-%02dT%02d:59:00' % (year, month, day, hour)
                self.addCalendarEnties(ge)

            if uvi > 4.0:
                #ical
                event = Event()    
                event.add('summary', "UV-Index: %.0f" % (uvi))
                event.add('dtstart', datetime(year, month, day, hour,  0, 0, 0, timezone('Europe/Berlin')))
                event.add('dtend',   datetime(year, month, day, hour, 59, 0, 0, timezone("Europe/Berlin")))
                event.add('description', DESC)
                self._newcal.add_component(event)
                #google
                ge = EVENT
                ge['summary']           = "UV-Index: %.0f" % (uvi)
                ge['start']['dateTime'] = '%02d-%02d-%02dT%02d:00:00' % (year, month, day, hour)
                ge['end'  ]['dateTime'] = '%02d-%02d-%02dT%02d:59:00' % (year, month, day, hour)
                self.addCalendarEnties(ge)

            if temp > 30.0 or temp < -10.0:
                #ical
                event = Event()    
                event.add('summary', "Temp: %.0f C" % (temp))
                event.add('dtstart', datetime(year, month, day, hour,  0, 0, 0, timezone('Europe/Berlin')))
                event.add('dtend',   datetime(year, month, day, hour, 59, 0, 0, timezone("Europe/Berlin")))
                event.add('description', DESC)
                self._newcal.add_component(event)
                #google
                ge = EVENT
                ge['summary']           = "Temp: %.0f C" % (temp)
                ge['start']['dateTime'] = '%02d-%02d-%02dT%02d:00:00' % (year, month, day, hour)
                ge['end'  ]['dateTime'] = '%02d-%02d-%02dT%02d:59:00' % (year, month, day, hour)
                self.addCalendarEnties(ge)

            if (temp - dewpoint) < 3:
                #ical
                event = Event()    
                event.add('summary', "Muggy: %.0f %%" % (humidity))
                event.add('dtstart', datetime(year, month, day, hour,  0, 0, 0, timezone('Europe/Berlin')))
                event.add('dtend',   datetime(year, month, day, hour, 59, 0, 0, timezone("Europe/Berlin")))
                event.add('description', DESC)
                self._newcal.add_component(event)
                #google
                ge = EVENT
                ge['summary']           = "Muggy: %.0f %%" % (humidity)
                ge['start']['dateTime'] = '%02d-%02d-%02dT%02d:00:00' % (year, month, day, hour)
                ge['end'  ]['dateTime'] = '%02d-%02d-%02dT%02d:59:00' % (year, month, day, hour)
                self.addCalendarEnties(ge)

            if wind > 23.0:
                #ical
                event = Event()    
                event.add('summary', "Wind: %.1f km/h" % (wind))
                event.add('dtstart', datetime(year, month, day, hour,  0, 0, 0,timezone('Europe/Berlin')))
                event.add('dtend',   datetime(year, month, day, hour, 59, 0, 0,timezone("Europe/Berlin")))
                event.add('description', DESC)
                self._newcal.add_component(event)
                #google
                ge = EVENT
                ge['summary']           = "Wind: %.1f km/h" % (wind)
                ge['start']['dateTime'] = '%02d-%02d-%02dT%02d:00:00' % (year, month, day, hour)
                ge['end'  ]['dateTime'] = '%02d-%02d-%02dT%02d:59:00' % (year, month, day, hour)
                self.addCalendarEnties(ge)

        return True

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False # UTF-8

w = w2ical()

@app.route('/', methods=['GET'])
def getIcal():
    return(w.getICal())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
