import json
import logging
import urllib
import qhue
import requests
from qhue import Bridge
from socket import getfqdn

from rgb_xy.rgb_xy import get_light_gamut, ColorHelper, Converter

logger = logging.getLogger()

converters = {}
helpers = {}
def get_color_things(modelid):
    gamut = get_light_gamut(modelid)
    if gamut not in converters:
        converters[gamut] = Converter(gamut)
        helpers[gamut] = ColorHelper(gamut)
    return converters[gamut], helpers[gamut]

def get_brightness_from_rgb(rgb):
    ## Accurate but useless
    ##bri = (0.299 * rgb[0]) + (0.587 * rgb[1])+ (0.114 * rgb[2])
    return max(rgb)

class HUE():
    PHILIPS_UPNP_PAGE = "https://www.meethue.com/api/nupnp"

    def __init__(self, IP, username):
        self.bridge = Bridge(IP, username)
        self.lights = {}
        self.refresh_lights_config()
        self.user = username
        self.ip = IP



    @staticmethod
    def create_user():
        ## Steppo uno: find the IP address used by HUE
        try:
            ip = HUE.guess_hue_ip()
        except Exception as e:
            raise e

        ## Steppo deux: generate a new API key
        fq_device_type = "subtlehue@{}".format(getfqdn())
        # POST with form-encoded data
        response = requests.post("http://" + ip + "/api", data='{"devicetype":"' + fq_device_type + '"}')
        jsonresp = json.loads(response.text)
        if("error" in jsonresp[0]):
            if jsonresp[0]["error"]["type"] == 101:
                raise Exception("Please press the link button on the HUE bridge now")
            else:
                raise Exception(jsonresp[0]["error"]["description"])
        user = jsonresp[0]["success"]["username"]
        return ip, user

    def save_scheduler_config(self, settingsfile):
        logger.debug("Now saving settings file")
        f = open(settingsfile, 'w')
        f.write(json.dumps({"hue_ip": self.ip, "hue_username":self.user}))
        f.close()

    @staticmethod
    def guess_hue_ip():
        ip = None
        response = urllib.urlopen(HUE.PHILIPS_UPNP_PAGE)
        data = json.loads(response.read())
        if len(data) > 0:
            ip = data[0]["internalipaddress"]
            if len(data) > 1:
                logger.warn("Found more then one HUE bridge. If this happens to be the case for you, drop me a message at github and I'll invest some time into handling that.")
        else:
            raise Exception("No local HUE found using the HUE website. As an alternative, you could create a settings file by hand and include the IP of your bridge - see subtlehuesettings.json.example")
        return ip

    @staticmethod
    def get_hue_instance(settings_file, ip=None, user=None):
        hue = None
        if(user):
            hue = HUE(ip,user)
            hue.save_scheduler_config(settings_file)
        else:
            try:
                f = open(settings_file,'r')
                all_settings = json.load(f)
                hue = HUE(all_settings["hue_ip"], all_settings["hue_username"])
            except IOError as ioe:
                logger.error("No setting file found, cannot connect to HUE: " + str(ioe))
            except KeyError as ke:
                logger.error("Setting file incomplete: " + str(ke))
            except ValueError as ve:
                logger.error("Setting file could not be decoded correctly: " + str(ve))
        return hue

    def get_light(self, light_number_or_name):
        if light_number_or_name.isdigit():
            light_number = light_number_or_name
        else:
            light_number = self.get_light_number_for_name(light_number_or_name)
        return self.lights[str(light_number)]

    def get_light_number_for_name(self,light_name):
        found = False
        for lightnumber in self.lights.keyset:
            light = self.lights[lightnumber]
            if light["name"] == light_name:
                found = lightnumber
                break
        return found

    def turn_on_and_blink(self, light_number):
        self.bridge.lights[light_number].state(on=True, alert="select")

    def get_hex_color_for_xy(self, lightconfig):
        ## Huidige kleur en brightness ophalen
        converter, colorhelper = get_color_things(lightconfig['modelid'])
        colors = converter.xy_to_hex(lightconfig["state"]["xy"][0], lightconfig["state"]["xy"][1])
        return colors

    def set_hex_color(self, light_number, hex_color, duration):
        if hex_color != "000000":
            light = self.get_light(light_number)
            converter, colorhelper = get_color_things(light['modelid'])
            xy = converter.hex_to_xy(hex_color)
            brightness = get_brightness_from_rgb(colorhelper.hex_to_rgb(hex_color))
            if duration > 0:
                self.bridge.lights[light_number].state(xy=xy, bri=brightness, transitiontime = (duration * 10))
            else:
                self.bridge.lights[light_number].state(xy=xy, bri=brightness)

    def refresh_lights_config(self):
        ## we halen alle LWB en kleurloze lampen eruit door te testen tegen de Gamut functie
        ## Kan niet met een dict comprehension, daar gaat mijn kans iets nieuws te leren
        newlights ={}
        for light, config in self.bridge.lights().iteritems():
            try:
                get_light_gamut(config['modelid'])
                newlights[light] = config
                newlights[light]["hexcolor"] = self.get_hex_color_for_xy(config)
            except ValueError as e:
                pass
        self.lights = newlights

