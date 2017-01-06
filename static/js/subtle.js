// Flip over a Bootstrap button
function toggleButton(buttonname, disable) {
    var thisButton = $("#" + buttonname);
    if (disable) {
        thisButton.toggleClass("btn-success", false);
        thisButton.prop('disabled', true);
    } else {
        thisButton.toggleClass("btn-success", true);
        thisButton.prop('disabled', false);
    }
}


// To convert minutes (ie. 90) to a human readeable time (ie. 1:30)
function minutes_as_time(minutes){
    var h = Math.floor(minutes / 60);
    var m = Math.floor(minutes) % 60;
    h = h < 10 ? '0' + h : h;
    m = m < 10 ? '0' + m : m;
    return h + ':' + m;
}

// Utility function to ask server to set a specific color on a bulb
function forcecolor(bulbnumber, color) {
    $.get("/forcecolor/" + bulbnumber + "/" + color.substring(1))
}

// Utility function to ask server to blink one specific bulb in it's current color
function forceblink(bulbnumber) {
    $.get("/forceblink/" + bulbnumber)
}

// Add a bulb block to the page for a given bulb and remove that
// from the list of available bulbs
function add_bulb_block(light_number, light_name, initial_color) {
    // We do not want to see this bulb in the light list any more
    $("#bulbs_available").find("option[value='"+ light_number +"']").remove();

    // Add a large panel with some sub panels and buttons
    var block = '<div class="panel panel-default" data-name="bulbscene" data-bulb="'+light_number+'">' +
        '<div class="panel-heading">' +
        '<h3 class="panel-title">'+light_name+ ' scene ' +
        '<span data-name="sceneremove" data-bulb="'+light_number+'" class="glyphicon glyphicon-remove-circle" aria-hidden="true"></spandata-></h3>'+
        '</div><div class="panel-body" data-name="scenelist" data-bulb="'+light_number+'"> ' +
        '<button name="color_add" class="btn btn-success btn-sm" data-bulb="'+light_number+'" data-color="'+ initial_color+'">Add</button>' +
        '</div></div>';
    $("#bulbs_active").append(block);

    // Bind an event to the little remove button next to the panel name
    $("span[data-name='sceneremove']").click(function() {
        light_number=$(this).data("bulb");
        $( document ).trigger( "subtle:change");
        $("div[data-name='bulbscene'][data-bulb='"+light_number+"']").remove();
        // Refresh to get our bulb list completed again
        refresh_buttons()
    });

    $("button[name='color_add'][data-bulb='"+light_number+"']").click(function(){
        add_color_picker($(this).data('bulb'), $(this).data('color'))
    })
}

// Given a bulb number, add another color picker to that bulb block
function add_color_picker(bulbnumber, defaultcolor) {
    sceneblock = $("div[data-name='scenelist'][data-bulb='"+bulbnumber+"']");
    current_palette = $("input[data-bulb='"+bulbnumber+"']");
    if(current_palette.length < 12) {
        newcolor = $('<input/>', {
            'type': 'color',
            'name': 'colorpicker',
            'data-bulb':bulbnumber,
            'value': defaultcolor
        }).prependTo(sceneblock);
        newcolor.spectrum({
            showPalette: true,
            showSelectionPalette: true,
            palette: [],
            cancelText: "Remove",
            localStorageKey: "spectrum.homepage",
            maxSelectionSize: 12
        })
        .on("dragstop.spectrum", function (e, color) {
            forcecolor(bulbnumber,color.toHexString());
            $( document ).trigger( "subtle:change")
        })
        .on("change.spectrum", function (e, color) {
            forcecolor(bulbnumber,color.toHexString());
            $( document ).trigger( "subtle:change")
        })
    }
}

// Adds a new row to the bulb scheme list and inserts one empty colorpicker
$("#bulbs_add").click(function() {
    // Figure out the ID and name of the selected bulb
    var light_number = $('#bulbs_available').val();
    if(light_number) {
        selected = $("#bulbs_available:selected");
        initial_color = selected.attr("color");
        light_name = selected.text();

        // Have the server blink said light
        forceblink(light_number);

        add_bulb_block(light_number, light_name, initial_color);
        add_color_picker(light_number, initial_color);
        $( document ).trigger( "subtle:change")
    }
});

$("#bulbs_force").click(function() {
    bootstrap_alert("Forced a color change on saved lights", "success");
    toggleButton("bulbs_force", true);
    $.get("/forcerun").done(function() {
       toggleButton("bulbs_force", false)
  }).fail(function() {
        toggleButton("bulbs_force", false);
        bootstrap_alert("Tried to do a light change, but failed for unknown reasons", "danger")
  })
});

$("#savechanges").click(function() {
    var scheme  = {};
    $("input[data-bulb][name='colorpicker']").each(function (){
        bulbnumber = $(this).data('bulb');
         if(!scheme [bulbnumber]) {
            scheme [bulbnumber] = []
         }
        scheme [bulbnumber].push($(this).spectrum('get').toHexString())
    });

    state = {
        "run_from": document.getElementById('timeslider').noUiSlider.get()[0],
        "run_until": document.getElementById('timeslider').noUiSlider.get()[1],
        "switch_from" :document.getElementById('cycleslider').noUiSlider.get()[0],
        "switch_until":document.getElementById('cycleslider').noUiSlider.get()[1],
        "duration": document.getElementById('durationslider').noUiSlider.get(),
        "lights": scheme
    };
    $.ajax("/addschedules", {
        data: JSON.stringify(state),
        contentType: 'application/json',
        type: 'POST'
    }).fail(function(jqXHR, textStatus, errorThrown) {
        bootstrap_alert("Could not save light configuration to server. Is the server instance up and running? Error message: " + errorThrown)
    }).done(function() {
        bootstrap_alert("Changes saved succesfully", "success");
        toggleButton("savechanges", true)
    })
});

function bootstrap_alert(message, alertclass) {
    alertclass = alertclass || "danger";
     $('#alert_placeholder').html('<div class="alert alert-' + alertclass + ' alert-dismissible" role="alert">' +
         '<button type="button" class="close" data-dismiss="alert" aria-label="Close">' +
         '<span aria-hidden="true">&times;</span>' +
         '</button><span>'+message+'</span>' +
         '</div>')
}

// Fetch the HUE configuration so we know what bulbs are there, what their
// current colors are and if we already schemed them
function refresh_buttons() {
    toggleButton("bulbs_add", true);
    $.getJSON("getlights", function (data) {
        if(!data.error) {
            // Fetch the first row of JSON keys
            lights_available = Object.keys(data.lights);
            bulbs = $('#bulbs_available').empty();
            if (lights_available.length > 0) {
                for (number in lights_available) {
                    lightid = lights_available[number];
                    if ($("div[data-bulb='" + lightid + "']").length == 0) {
                        bulbs.append($('<option>').val(lightid).text(data.lights[lightid].name).attr("color", "#" + data.lights[lightid].hexcolor))
                    }
                }
                toggleButton("bulbs_add")
            }
        } else {
            bootstrap_alert("Could not connect to a HUE bridge instance")
        }
    }).fail(function(jqXHR, textStatus, errorThrown) { bootstrap_alert("Could not get light configuration from server. Is the server instance up and running? Error message: " + errorThrown) })
}

function init_sliders() {
    var timeslider = document.getElementById('timeslider');
    noUiSlider.create(timeslider, {
        start: [60, 1380],
        step: 15,
        connect: true,
        range: {
            'min': 0,
            'max': 1440
        }
    });
	timeslider.noUiSlider.on('update', function( values ) {
	    if(values[0] == 0 && values[1] == 96) {
            $("#timeslidertimes").text("Schedules run permanently")
        } else {
	        $("#timeslidertimes").text("Subtle changer runs from " + minutes_as_time(values[0])  + " until " +  minutes_as_time(values[1]) )
        }
        $( document ).trigger( "subtle:change");
    });

    var cycleslider = document.getElementById('cycleslider');
    noUiSlider.create(cycleslider, {
        start: [5,10],
        connect: true,
        range: {
            'min': 1,
            'max': 30
        }
    });
	cycleslider.noUiSlider.on('update', function( values ) {
        if(values[0] == values[1]) {
	        $("#cycleslidertimes").text("Selected lights will change every " + Math.floor(values[0]) + " minutes.")
        } else {
            $("#cycleslidertimes").text("Selected lights will change every " + Math.floor(values[0]) + " to " + Math.floor(values[1]) + " minutes.")
        }
        I_edited_something()
    });

    var durationslider = document.getElementById('durationslider');
    noUiSlider.create(durationslider, {
        start: [5],
        step: 1,
        connect: true,
        range: {
            'min': 0,
            'max': 60
        }
    });
	durationslider.noUiSlider.on('update', function( values ) {
        $("#durationslidertimes").text("Color changes take "+ Math.floor(values) + " seconds");
        
    });
}

function restore_settings() {
    $.getJSON("/getschedules",function(data) {
        document.getElementById("durationslider").noUiSlider.set(data.schedules.duration);
        document.getElementById("cycleslider").noUiSlider.set([data.schedules.randomstart, data.schedules.randomend]);
        document.getElementById("timeslider").noUiSlider.set([data.schedules.startat, data.schedules.endat]);
        for(light in data.schedules.lights) {
            light_name = data.schedules.lightnames[light];
            add_bulb_block(light,light_name, data.schedules.lights[light][0]);
            for(color in data.schedules.lights[light]) {
                add_color_picker(light, data.schedules.lights[light][color])
            }
        }
        toggleButton("savechanges", true)
    })
}

 $(document).ready(function ($) {
    refresh_buttons();
    init_sliders();

     // I do not understand why this button disables. Sorry.
     toggleButton("bulbs_force", false);

     $( document ).on( "subtle::change", function(){
          toggleButton("savechanges")
    });


    restore_settings();
});