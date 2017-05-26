import logging
import os
import traceback
from flask import Flask, jsonify
from flask import render_template
from flask import request

from hue.LightScheduler import LightScheduler
from hue.converter_decorator import HUE

app = Flask(__name__)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)

## Disable werkzeug logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)


## Get working dir for WSGI situations:
here = os.path.dirname(__file__)
SCHEDULE_FILE = os.path.join(here, './subtlehue.json')
SETTINGS_FILE = os.path.join(here, './subtlehuesettings.json')

## Accepts a JSON set of bulbs, their suggested colors and some additional parameters
@app.route('/addschedules', methods=["POST"])
def flask_add_schedules():
    ### Example of expected JSON:
    #{
    #    "run_from": "60.00",
    #    "run_until": "1380.00",
    #    "switch_from": "5.00",
    #    "switch_until": "10.00",
    #    "duration": "10.00",
    #    "lights": {
    #        "2": [
    #            "#ff4600","#ffffff"
    #        ]
    #    }
    #}
    ###

    ## We parse this message in the scheduler
    ## Note that we overwrite any existing schedules
    scheduler.add_rawjson_schedules(request.get_data())
    scheduler.save_scheduler_config()
    return jsonify({"state": "ok"})


## Shortcut version to add a single schedule, not in use any more
@app.route('/addschedule/<light_number>/<cycletime>/<colors_comma_seperated>')
def flask_add_schedule(light_number, cycletime, colors_comma_seperated):
    colorlist = colors_comma_seperated.lower().split(',')
    scheduler.add_schedule(light_number, colorlist)
    return jsonify({"state":"ok"})


## Hard set one bulb to a color
@app.route('/forcecolor/<light_number>/<hex_color>')
def flask_force_color(light_number, hex_color):
    try:
        hue.set_hex_color(light_number, str(hex_color),0)
    except Exception as e:
        traceback.print_exc()
        logger.error("Got an exception setting color " + str(hex_color) + " for light " + str(light_number)+ ":",e)
    return jsonify({"state":"ok"})


## Shortcut to quickly debug the scheduler
@app.route('/forcerun')
def flask_force_run():
    scheduler.run_scheduler(True)
    return jsonify({"state": "ok"})


## Shortcut to pause the scheduler
@app.route('/pause/<pause_scheduler>')
def flask_pause_scheduler(pause_scheduler):
    to_pause = pause_scheduler == "1"
    scheduler.set_paused(to_pause)
    return jsonify({"state": "ok"})

## Method for blinking, this is run whenever a new scheme is added
@app.route('/forceblink/<light_number>')
def flask_force_blink(light_number):
    hue.turn_on_and_blink(light_number)
    return jsonify({"state": "ok"})

## Retrieves the current schedules to restore the web page to last time use
@app.route('/getschedules')
def flask_get_schedules():
    if(scheduler.hue):
        schedules = scheduler.schedules
        lightnames = {}
        for schedule in schedules["lights"]:
            lightnames[schedule] = hue.get_light(schedule)["name"]
        schedules["lightnames"] = lightnames
        return jsonify({"schedules":scheduler.schedules})
    else:
        return jsonify({"error":"Could not connect to HUE bridge"})


## List all bulbs on this bridge
@app.route("/getlights")
def flask_get_lights():
    if hue:
        hue.refresh_lights_config()
        return jsonify({"lights":hue.lights})
    else:
        return jsonify({"lights":{}, "error":"Could not connect to a HUE bridge"})


@app.route("/createuser")
def flask_create_hue_user():
    global hue, scheduler
    try:
        ip, user = HUE.create_user()
        hue = HUE.get_hue_instance(SETTINGS_FILE,ip,user)
        scheduler = LightScheduler(hue, SCHEDULE_FILE)
    except Exception as e:
        return jsonify({"state": "nok", "error":str(e)})
    return jsonify({"state": "ok"})


@app.route('/')
def hello_world():
    if scheduler == None:
        return render_template('adduser.html')
    else:
        return render_template('index.html', pause="true" if scheduler.pause else "false")


def init_subtle():
    scheduler = None
    hue = HUE.get_hue_instance(SETTINGS_FILE)
    if hue:
        scheduler = LightScheduler(hue, SCHEDULE_FILE)
    return hue, scheduler

hue, scheduler = init_subtle()
if __name__ == '__main__':
    app.run(debug=False,threaded=True,host='0.0.0.0', port=86)

