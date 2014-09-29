#!/usr/bin/env python

# Author: Bryan J. Brown
# Email:  bryjbrown@gmail.com
# Date:   Spring semester, 2014
# 
# Script for pulling historical metadata from Google spreadsheets and parsing into Leaflet JS
# Created for the 'Globalization of the US, 1775-1861' project w/ Konstantin Dierks


import sys
sys.dont_write_bytecode = True
import urllib2
import csv
import os
import time
import subprocess

# ./settings.py, controls various script options
import settings


# Save old data.js into /backups/ with timestamp
cwd = os.getcwd()
t = time.localtime()
tf = '%d-%02d-%02d@%02d:%02d:%02d' % (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
if not os.path.exists(cwd + "/backups/"):
  print "Backups dir missing."
  print "Creating " + cwd + "/backups/"
  os.mkdir(cwd + "/backups/")
if os.path.exists(cwd + "/data.js"):
  os.rename(cwd + "/data.js", cwd + "/backups/data_" + tf + ".js")

# Grab remote CSV data from Google Docs spreadsheet and save to local file 'data.csv'
csv_local = open("data.csv", 'w')
csv_link = "https://docs.google.com/feeds/download/spreadsheets/Export?key={0}&exportFormat=csv&gid=0".format(settings.gdoc_id)
csv_data = urllib2.urlopen(csv_link).read()
csv_local.write(csv_data)
csv_local.close()

# Read CSV file and save relevant data to memory
csv_input = open("data.csv", "r")
reader = csv.DictReader(csv_input, delimiter=',')

# Initialize empty arrays to hold each metadata record according to record type
# (each individual record will be stored as its own hash inside these arrays)
map_list = []
marker_list = []
shape_list = []

# Sort records by type
for line in reader:

  if line["Type"] == "Map":
    map_obj = {}
    map_obj["url"] = line["URL"]
    map_obj["title"] = line["Title"]
    map_obj["syear"] = line["Start Year"]
    map_obj["eyear"] = line["End Year"]
    if line["URL"] != "" and line["Title"] != "" and line["Start Year"] != "" and line["End Year"] != "":
      map_list.append(map_obj)

  elif line["Type"] == "Marker":
    marker_obj = {}
    if line["Historic Lat"] != "" and line["Historic Lon"] != "":
      marker_obj["lat"], marker_obj["lon"] = line["Historic Lat"], line["Historic Lon"]
    else:
      marker_obj["lat"], marker_obj["lon"] = line["Present Lat"], line["Present Lon"]
    marker_obj["cat"] = line["Category"]
    marker_obj["subcat"] = line["Sub Category"]
    marker_obj["syear"] = line["Start Year"]
    marker_obj["eyear"] = line["End Year"]
    marker_obj["drange"] = line["Date Range"]
    marker_obj["title"] = line["Title"]
    marker_obj["desc"] = line["Description"]
    marker_obj["hist-loc"] = line["Historic Location"]
    marker_obj["pres-loc"] = line["Present Location"]
    marker_obj["src"] = line["Source"]
    marker_obj["url"] = line["URL"]
    if line["Category"] != "" and line["Sub Category"] != "" and line["Start Year"] != "" and line["Title"] != "" and line["Present Lat"] != "" and line["Present Lon"] != "":
      marker_list.append(marker_obj)

  elif line["Type"] == "Shape":
    shape_obj = {}
    shape_obj["cat"] = line["Category"]
    shape_obj["subcat"] = line["Sub Category"]
    shape_obj["title"] = line["Title"]
    shape_obj["desc"] = line["Description"]
    shape_obj["syear"] = line["Start Year"]
    shape_obj["eyear"] = line["End Year"]
    shape_obj["drange"] = line["Date Range"]
    shape_obj["hist-loc"] = line["Historic Location"]
    shape_obj["pres-loc"] = line["Present Location"]
    shape_obj["json"] = line["GeoJSON"]
    shape_obj["src"] = line["Source"]
    shape_obj["url"] = line["URL"]
    if line["Category"] != "" and line["Sub Category"] != "" and line["Start Year"] != "" and line["Title"] != "" and line["GeoJSON"] != "":
      shape_list.append(shape_obj)

csv_input.close()

removals = range(len(map_list))

# Format captured data into JS vars
js_output = open("data.js", "w")
js_output.write("// Leaflet data, compiled on " + tf + "\n")

# Initialize empty hashes to store array of records by key
# This is to generate the list of everything that should turn on/off by layer
# such as categories (cat_dict), records with only a start date (start_dict),
# records that only exist for one year in time (iso_dict) and records that only
# exist between a start year and end year (range_dict)
cat_dict = {}
start_dict = {}
iso_dict = {}
range_dict = {}

# Generate all js map vars, write to 'data.js' and store a copy in base_layer array
js_output.write("\n")
base_layer = []
for index, map in enumerate(map_list):
  map_var = "var map{0} = L.tileLayer('{1}', {{maxZoom: {2}, minZoom: {3}, tms: true}});\n"
  js_output.write(map_var.format(index, map['url'], settings.max_zoom, settings.min_zoom))

  base = "'{0}': map{1},".format(map['title'], index) 
  base_layer.append(base)

# Generate marker GeoJSON
for index, marker in enumerate(marker_list):
  if not marker["cat"] in cat_dict:
    cat_dict[marker["cat"]] = {}
  if not marker["subcat"] in cat_dict[marker["cat"]]:
    cat_dict[marker["cat"]][marker["subcat"]] = []
  
OverseasMarineLandings = "\nvar OverseasMarineLandings={type:\"FeatureCollection\",features:["
OverseasNavyPersonnel = "\nvar OverseasNavyPersonnel={type:\"FeatureCollection\",features:["
ForeignMilitaryActions = "\nvar ForeignMilitaryActions={type:\"FeatureCollection\",features:["
ForeignImports = "\nvar ForeignImports={type:\"FeatureCollection\",features:["
ForeignExports = "\nvar ForeignExports={type:\"FeatureCollection\",features:["
MinorForeignOrigins = "\nvar MinorForeignOrigins={type:\"FeatureCollection\",features:["
MajorForeignOrigins = "\nvar MajorForeignOrigins={type:\"FeatureCollection\",features:["
MissionStations = "\nvar MissionStations={type:\"FeatureCollection\",features:["
DiplomaticMissions = "\nvar DiplomaticMissions={type:\"FeatureCollection\",features:["
ForeignTreaties = "\nvar ForeignTreaties={type:\"FeatureCollection\",features:["

for index, marker in enumerate(marker_list):
  subcat = marker["subcat"].replace(" ", "")
  
  title = "<p><b><u>{0}</u></b>".format(marker["title"])
  if marker["drange"] != "":
    year_range = "<br/><b>Years:</b> {0}".format(marker["drange"])
  elif marker["eyear"] != "":
    year_range = "<br/><b>Years:</b> {0} - {1}".format(marker["syear"], marker["eyear"])
  else:
    year_range = "<br /><b>Year:</b> {0}".format(marker["syear"])

  if marker["desc"] != "":
    desc = "<br/><b>Description:</b> {0}".format(marker["desc"])
  else:
    desc = "<br/><b>Description:</b> "

  if marker["hist-loc"] != "":
    hist_loc = "<br/><b>Historic Location:</b> {0}".format(marker["hist-loc"])
  else:
    hist_loc = "<br/><b>Historic Location:</b> "

  if marker["pres-loc"] != "":
    pres_loc = "<br/><b>Present Location:</b> {0}".format(marker["pres-loc"])
  else:
    pres_loc = "<br/><b>Present Location:</b> "

  if marker["src"] != "" and marker["url"] != "":
    src = "<br/><b>Source:</b> <a href='{0}'>{1}</a>".format(marker["url"], marker["src"])
  elif marker["src"] != "" and marker["url"] == "":
    src = "<br/><b>Source:</b> {1}".format(marker["url"], marker["src"])
  else:
    src = "<br/><Source:</b> "

  pop_text = "\"" + title + year_range + desc + hist_loc + pres_loc + src + "</p>\""
  
  if marker["eyear"] == "":
    date_type = "start"
    date = "[{0}]".format(marker["syear"])
  else:
    if marker["eyear"] == marker["syear"]:
      date_type = "iso"
      date = "[{0}]".format(marker["syear"])
    else:
      date_type = "range"
      date = "[{0},{1}]".format(marker["syear"], marker["eyear"])
  
  marker_json = "{{type:\"Feature\",id:\"{0}\",date_type:\"{1}\",date:{2},geometry:{{type:\"Point\",coordinates:[{3},{4}]}},pop_text:{5}}},".format(index, date_type, date, marker["lon"], marker["lat"], pop_text)
  
  if subcat == "OverseasMarineLandings":
    OverseasMarineLandings += marker_json
  elif subcat == "OverseasNavyPersonnel":
    OverseasNavyPersonnel += marker_json
  elif subcat == "ForeignMilitaryActions":
    ForeignMilitaryActions += marker_json
  elif subcat == "ForeignImports":
    ForeignImports += marker_json
  elif subcat == "ForeignExports":
    ForeignExports += marker_json
  elif subcat == "MinorForeignOrigins":
    MinorForeignOrigins += marker_json
  elif subcat == "MajorForeignOrigins":
    MajorForeignOrigins += marker_json
  elif subcat == "MissionStations":
    MissionStations += marker_json
  elif subcat == "DiplomaticMissions":
    DiplomaticMissions += marker_json
  elif subcat == "ForeignTreaties":
    ForeignTreaties += marker_json

OverseasMarineLandings += "]}"
OverseasNavyPersonnel += "]}"
ForeignMilitaryActions += "]}"
ForeignImports += "]}"
ForeignExports += "]}"
MinorForeignOrigins += "]}"
MajorForeignOrigins += "]}"
MissionStations += "]}"
DiplomaticMissions += "]}"
ForeignTreaties += "]}"

js_output.write(OverseasMarineLandings)
js_output.write(OverseasNavyPersonnel)
js_output.write(ForeignMilitaryActions)
js_output.write(ForeignImports)
js_output.write(ForeignExports)
js_output.write(MinorForeignOrigins)
js_output.write(MajorForeignOrigins)
js_output.write(MissionStations)
js_output.write(DiplomaticMissions)
js_output.write(ForeignTreaties)

# Generate all js shape vars and write to 'data.js'
# Also generate pop-up to display relevant metadata and bind to shape var
# Finally, store record data in relevant hash depending on category and year metadata
js_output.write("\n")
for index, shape in enumerate(shape_list):
  js_output.write("var json{0} = {1}; ".format(index, shape["json"]))
  js_output.write("var shape{0} = L.geoJson(json{1}, {{ style: {2}ShapeStyle }}); ".format(index, index, shape["subcat"].replace(" ", "")))

  title = "<p><b><u>{0}</u></b>".format(shape["title"])
  if shape["drange"] != "":
    year_range = "<br/><b>Years:</b> {0}".format(shape["drange"])
  elif shape["eyear"] != "":
    year_range = "<br/><b>Years:</b> {0} - {1}".format(shape["syear"], shape["eyear"])
  else:
    year_range = "<br /><b>Year:</b> {0}".format(shape["syear"])

  if shape["desc"] != "":
    desc = "<br/><b>Description:</b> {0}".format(shape["desc"])
  else:
    desc = "<br/><b>Description:</b> "

  if shape["hist-loc"] != "":
    hist_loc = "<br/><b>Historic Location:</b> {0}".format(shape["hist-loc"])
  else:
    hist_loc = "<br/><b>Historic Location:</b> "

  if shape["pres-loc"] != "":
    pres_loc = "<br/><b>Present Location:</b> {0}".format(shape["pres-loc"])
  else:
    pres_loc = "<br/><b>Present Location:</b> "

  if shape["src"] != "" and shape["url"] != "":
    src = "<br/><b>Source:</b> <a href='{0}'>{1}</a>".format(shape["url"], shape["src"])
  elif shape["src"] != "" and shape["url"] == "":
    src = "<br/><b>Source:</b> {1}".format(shape["url"], shape["src"])
  else:
    src = "<br/><Source:</b> "

  pop_text = "\"" + title + year_range + desc + hist_loc + pres_loc + src + "</p>\""
  js_output.write("shape{0}.bindPopup({1});\n".format(index, pop_text))

  if not shape["cat"] in cat_dict:
    cat_dict[shape["cat"]] = {}
  if not shape["subcat"] in cat_dict[shape["cat"]]:
    cat_dict[shape["cat"]][shape["subcat"]] = []
  cat_dict[shape["cat"]][shape["subcat"]].append("shape{0}".format(index))

  if shape["eyear"] == "":
    if not shape["syear"] in start_dict:
      start_dict[shape["syear"]] = []
    start_dict[shape["syear"]].append("shape{0}".format(index))
  else:
    if shape["eyear"] == shape["syear"]:
      if not shape["syear"] in iso_dict:
        iso_dict[shape["syear"]] = []
      iso_dict[shape["syear"]].append("shape{0}".format(index))
    else:
      key = "{0}_{1}".format(shape["syear"], shape["eyear"])
      if not key in range_dict:
        range_dict[key] = []
      range_dict[key].append("shape{0}".format(index))

js_output.write("\n")

js_output.write("var currentYear = null;\n\n")

# Custom GeoJSON filter functions and popup bindings
js_output.write("function filter(feature, layer) {\n")
js_output.write("\tswitch(feature.date_type) {\n")
js_output.write("\t\tcase \"start\":\n")
js_output.write("\t\t\tif (currentYear >= feature.date[0]) {\n")
js_output.write("\t\t\t\treturn true;\n")
js_output.write("\t\t\t} else {\n")
js_output.write("\t\t\t\treturn false;\n")
js_output.write("\t\t\t};\n")
js_output.write("\t\tcase \"iso\":\n")
js_output.write("\t\t\tif (currentYear == feature.date[0]) {\n")
js_output.write("\t\t\t\treturn true;\n")
js_output.write("\t\t\t} else {\n")
js_output.write("\t\t\t\treturn false;\n")
js_output.write("\t\t\t};\n")
js_output.write("\t\tcase \"range\":\n")
js_output.write("\t\t\tif (currentYear >= feature.date[0] && currentYear <= feature.date[1]) {\n")
js_output.write("\t\t\t\treturn true;\n")
js_output.write("\t\t\t} else {\n")
js_output.write("\t\t\t\treturn false;\n")
js_output.write("\t\t\t};\n")
js_output.write("\t}\n")
js_output.write("};\n")
js_output.write("\n")
js_output.write("function onEachFeature(feature, layer) {\n")
js_output.write("\tvar popup = feature.pop_text;\n")
js_output.write("\tlayer.bindPopup(popup);\n")
js_output.write("};\n\n")

# Create subcategorical marker clusters
overlayer = []

for category in cat_dict:

  for subcategory in cat_dict[category]:
    cluster_name = "{0}Markers".format(subcategory.replace(" ", ""))
    class_name = "{0}".format(subcategory.replace(" ", "-").lower())
    cluster = "' -- {0}': {1},".format(subcategory, cluster_name) 
    js_output.write("var {0} = new L.MarkerClusterGroup({{ clusterClass: \"{1}".format(cluster_name, class_name)) 
    js_output.write("\" });\n")
    
    sublayer = "\"<img src='images/{0}.png' class='overlay-icon' height=13 width=10><span>&nbsp;{1}</span>\": {2},".format(subcategory.replace(" ", ""), subcategory, cluster_name)
    overlayer.append(sublayer)

js_output.write("\n")

# Create (sub)categorical layers
for category in cat_dict:

  for subcategory in cat_dict[category]:
    sublayer_name = "{0}Layer".format(subcategory.replace(" ", ""))
    js_output.write("var {0} = L.geoJson({1},{{filter: filter, onEachFeature: onEachFeature, pointToLayer: function (feature, latlng) {{return L.marker(latlng, {{icon:{2}Icon}})}}}}".format(sublayer_name, subcategory.replace(" ", ""), subcategory.replace(" ", ""))) 
    js_output.write(");\n")

js_output.write("\n")

# Add subcategorical layers to marker clusters
for category in cat_dict:

  for subcategory in cat_dict[category]:
    cluster_name = "{0}Markers".format(subcategory.replace(" ", ""))
    sublayer_name = "{0}Layer".format(subcategory.replace(" ", ""))
    js_output.write("{0}.addLayer({1});\n".format(cluster_name, sublayer_name))

js_output.write("\n")

# Set styling options for category/subcategory icons and shapes, and search the images folder
# for filenames that match category/subcategory names
if settings.style_refresh == True:
  style_file = open("style.js", "w")
  images = os.listdir("../images")
  image_list = []
  for image in images:
    image_list.append(image.replace(".png", ""))

  for category in cat_dict:
    for subcategory in cat_dict[category]:
      shortsubcat = subcategory.replace(" ", "")
      style_file.write("// {0} marker icon and shape styling".format(subcategory))
      style_file.write("\nvar {0}Icon = L.icon({{\n".format(shortsubcat))

      if shortsubcat in image_list:
        style_file.write("\ticonUrl: '{0}images/{1}.png',\n".format(settings.app_path, shortsubcat))
        style_file.write("\ticonSize: [{0}], // icon height/width in pixels\n".format(settings.icon_size))
        style_file.write("\ticonAnchor: [{0}], // point where icon corresponds to marker's location\n".format(settings.icon_anchor))
      else:
        style_file.write("\ticonUrl: '{0}images/default-icon.png',\n".format(settings.app_path))
        style_file.write("\t//iconSize: [0, 0], // icon height/width in pixels\n")
        style_file.write("\t//iconAnchor: [0, 0], // point of the icon which will correspond to marker's location\n")

      style_file.write("\t//popupAnchor: [0, 0] // point from which the popup should open relative to the iconAnchor\n")
      style_file.write("});\n")
      style_file.write("\nvar {0}ShapeStyle = {{\n".format(subcategory.replace(" ", "")))
      style_file.write("\t'color': '#0000ff',\n") 
      style_file.write("\t'weight': 1,\n") 
      style_file.write("\t'opacity': 1\n") 
      style_file.write("};\n\n\n")
  style_file.close()


# Set all category/subcategory layers to be toggleable from control panel
js_output.write("var overlays = {")
for overlay in overlayer:
  js_output.write(overlay)
js_output.write("};\n")

js_output.write("\n")

# Set all basemaps to be selectable from control panel
js_output.write("var baseLayers = {")
for base in base_layer:
  js_output.write(base)
js_output.write("};\n")

# Set boundaries for map
js_output.write("var southWest = L.latLng(-68.13885, -178.59385)\n")
js_output.write("var northEast = L.latLng(79.68718, 189.14063)\n")
js_output.write("var bounds = L.latLngBounds(southWest, northEast);\n")

# Initialize map and append cluster layer group
js_output.write("\n")
js_output.write("var map = L.map('map', {{ center: {0}, zoom: {1}, maxBounds: bounds }});\n".format(settings.init_center, settings.init_zoom))
js_output.write("L.control.layers(baseLayers, overlays).addTo(map);\n\n")

# create 'setBasemap' function which switches basemaps on trigger years
js_output.write("function setBasemap(time) {\n")
for index, map in enumerate(map_list):
  removed = removals[:]
  removed.remove(index)
  js_output.write("\tif (time >= {0} && time <= {1}) {{\n".format(map["syear"], map["eyear"]))
  for item in removed:
    js_output.write("\t\tmap.removeLayer(map{0});\n".format(item))
  js_output.write("\t\tmap.addLayer(map{0});\n".format(index))
  js_output.write("\t}\n")
js_output.write("};\n\n")

# create 'setOverlays' function which refreshes data layers on timeline change
js_output.write("function setOverlays(time) {\n")
for category in cat_dict:
  for subcategory in cat_dict[category]:
    subcat = subcategory.replace(" ", "")
    js_output.write("\t{0}Markers.removeLayer({0}Layer);\n".format(subcat))
  for subcategory in cat_dict[category]:
    subcat = subcategory.replace(" ", "")
    js_output.write("\t{0}Layer = L.geoJson({0},{{filter: filter, onEachFeature: onEachFeature, pointToLayer: function (feature, latlng) {{return L.marker(latlng, {{icon: {0}Icon}})}}}});\n".format(subcat))
  for subcategory in cat_dict[category]:
    subcat = subcategory.replace(" ", "")
    js_output.write("\t{0}Markers.addLayer({0}Layer);\n".format(subcat))
js_output.write("};\n\n")

# create 'setData' function which triggers all other functions at once
js_output.write("function setData(time) {\n")
js_output.write("\tsetBasemap(time);\n")
js_output.write("\tsetOverlays(time);\n")
js_output.write("\tcurrentYear = time;\n")
js_output.write("};\n")
js_output.close()

print "\033[92mDone!\033[0m"
print "New data.js created, old data.js has been moved to:"
print cwd + "/backups/\033[91mdata_" + tf + ".js\033[0m"
