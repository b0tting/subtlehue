import json
import logging
import random
from threading import Thread
import time
import datetime

logger = logging.getLogger()

## weeny subclass because..
class ScheduledLight():
    def __init__(self, light_number, colorlist):
        self.light_number = light_number
        self.colorlist = colorlist
        self.nextcycletime = 0
        self.lastcycle = 0
        self.lastindex = 0

    def set_next_cycle(self, randomstart, randomend):
        self.nextcycletime = random.randint(randomstart, randomend)


class BackgroundTimer(Thread):
    def __init__(self, scheduler):
        super(BackgroundTimer, self).__init__()
        self.scheduler = scheduler

    def run(self):
        while True:
            x = int(time.time())
            logger.debug("Ping from timer thread..")
            self.scheduler.run_scheduler()
            duration = max(60 - (int(time.time()) - x), 0)
            time.sleep(duration)


class LightScheduler():
    def __init__(self, hue, settingsfile):
        self.hue = hue
        self.scheduledlights = {}
        self.settingsfile = settingsfile
        self.schedules = {}
        self.pause = False

        try:
            self.load_scheduler_config()
        except Exception as e:
            logger.warning("Could not find, read or convert settingsfile. using defaults")
            logger.debug("Error was " + str(e))
            self.schedules["randomstart"] = 5
            self.schedules["randomend"]= 7
            self.schedules["startat"]= 0
            self.schedules["endat"]= 1440
            self.schedules["duration"]= 0
            self.schedules["lights"] = {}

        ## Start timer after settings
        self.timer = BackgroundTimer(self)
        self.timer.setDaemon(True)
        self.timer.start()

    def set_paused(self, state):
        logger.warn("Pausing state" if state else "Unpausing state")
        self.pause = state

    def add_rawjson_schedules(self, raw_json):
        unmapped_content = json.loads(raw_json)
        self.schedules["randomstart"] = int(float(unmapped_content["switch_from"]))
        self.schedules["randomend"] = int(float(unmapped_content["switch_until"]))
        self.schedules["startat"] = int(float(unmapped_content["run_from"]))
        self.schedules["endat"] = int(float(unmapped_content["run_until"]))
        self.schedules["duration"] = int(float(unmapped_content["duration"]))
        self.schedules["lights"] = unmapped_content["lights"]
        self.refresh_schedules()

    def refresh_schedules(self):
        self.scheduledlights = {}
        for light, colors in self.schedules["lights"].iteritems():
            self.schedules["lights"][light] = colors
            self.add_schedule(light, colors)

    def load_scheduler_config(self):
        try:
            f = open(self.settingsfile,'r')
            self.schedules = json.load(f)
            self.refresh_schedules()
        except Exception as e:
            raise e

    def save_scheduler_config(self):
        logger.debug("Now saving settings file")
        f = open(self.settingsfile, 'w')
        f.write(json.dumps(self.schedules))
        f.close()

    def add_schedule(self, light_number, colorlist):
        logger.debug("Adding a new schedule for " + light_number + " with color list " + ', '.join(colorlist))
        colorlist = [color[1:] for color in colorlist]
        light = ScheduledLight(light_number, colorlist)
        if light_number in self.scheduledlights:
            self.scheduledlights.pop(light_number)
        self.scheduledlights[light_number]= light
        light.set_next_cycle(self.schedules["randomstart"], self.schedules["randomend"])

    def run_scheduler(self, force=False):
        if force:
            logger.warn("Doing a forced run through the light scheduler, even skipping a pause")
        currentmins = int(time.time() / 60)
        ## Check if we are not outside of the subtle window
        today = datetime.date.today()
        minutes_of_day = int((time.time() - time.mktime(today.timetuple())) / 60)
        logger.debug(
            "Schedule checking for applicable lights in " + str(len(self.scheduledlights)) + " lights at time " + str(minutes_of_day))
        if(self.hue):
            if (not self.pause and self.schedules["startat"] < minutes_of_day < self.schedules["endat"]) or force:
                for light in self.scheduledlights.values():
                    logger.debug("..light " + str(light.light_number) + " is due at " + str(light.lastcycle + light.nextcycletime))
                    if (light.lastcycle + int(light.nextcycletime)) <= currentmins or force:
                        logger.debug("..so I am triggering light " + str(light.light_number))
                        newhex, index = self.get_random_newcolor_from_list(light.colorlist, light.lastindex)
                        light.lastindex = index
                        logger.debug("Setting hex color " + newhex)
                        try:
                            self.hue.set_hex_color(light.light_number, newhex, self.schedules["duration"])
                        except Exception as e:
                            logger.warn("Could not set color: "+ str(e))
                        light.lastcycle = currentmins
                        light.set_next_cycle(self.schedules["randomstart"], self.schedules["randomend"])
            else:
                logger.debug("Sorry. " + str(minutes_of_day) + " is outside of the " + str(self.schedules["startat"]) + " and " + str(self.schedules["endat"]) + " timewindow")
        else:
            logger.warn("Could not connect to HUE.. Trying again in the next run..")


    def get_random_newcolor_from_list(self, colorlist, lastindex):
        size = len(colorlist)
        if(size > 1 and lastindex < size):
            options = range(0, len(colorlist))
            options.pop(lastindex)
            randomindex = random.choice(options)
        else:
            randomindex = 0
        return colorlist[randomindex], randomindex