SubtleHue
-------------

Hue bulbs are awesome. Millions of colors, easy apps. But what I felt was missing was a tool that made them come alive more, in a subtle way. Like subtly shifting through a palette over time. Which is just what this app can do. 
 
You configure SubtleHue with a web based configuration page, where you set up different palettes for any Hue lights you want to include. Here you can also set different parameters: schedule the scheduler to only run at given times, the time it take to complete a color transition and the (random) amount of time to have between color cycles.
 
 ![SubtleHue screenshot](/img/screenshot.png?raw=true)

Requirements
------------

SubtleHue runs as a python daemon, on Windows or Linux. It would be a great match for a Raspberry Pi (or a zero). Once started and configured

**Installation**

First install the dependencies, as follows:

`pip install -r requirements.txt`

After that, run the program

`python subtle.py`

An example systemd configuration file for running from system start:

    [Unit]
    Description=SubtleHue python app
    
    [Service]
    PIDFile=/var/run/subtlehue.pid
    WorkingDirectory=/usr/local/subtlehue
    ExecStart=/usr/bin/python subtle.py
    
    [Install]
    WantedBy=multi-user.target


I use the QHUE shortcuts found here: https://github.com/quentinsf/qhue - and the color converters from https://github.com/benknight/hue-python-rgb-converter

**Configuration**

By default, the web interface for configuration runs at port 86. 


 
