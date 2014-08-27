#!/usr/bin/env python

import sys
sys.dont_write_bytecode = True
import urllib2
import csv
import os
import time
import subprocess

# ./settings.py, controls automation options
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

# Grab CSV data from Google Docs spreadsheet and save to data.csv 
csv_local = open("data.csv", 'w')
csv_link = "https://docs.google.com/feeds/download/spreadsheets/Export?key={0}&exportFormat=csv&gid=0".format(settings.gdoc_id)
csv_data = urllib2.urlopen(csv_link).read()
csv_local.write(csv_data)
csv_local.close()

# Read CSV file and save relevant data to memory
csv_input = open("data.csv", "r")
reader = csv.DictReader(csv_input, delimiter=',')

map_list = []
marker_list = []
shape_list = []

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

js_output.write("\nvar cluster = new L.MarkerClusterGroup();\n")

cat_dict = {}
start_dict = {}
iso_dict = {}
range_dict = {}

js_output.write("\n")
base_layer = []
for index, map in enumerate(map_list):
  map_var = "var map{0} = L.tileLayer('{1}', {{maxZoom: {2}, minZoom: {3}, tms: true}});\n"
  js_output.write(map_var.format(index, map['url'], settings.max_zoom, settings.min_zoom))

  base = "'{0}': map{1},".format(map['title'], index) 
  base_layer.append(base)

js_output.write("\n")
for index, marker in enumerate(marker_list):
  marker_name = "marker{0}".format(index)
  marker_var = "var {0} = L.marker([{1}, {2}], {{icon: {3}Icon}}); "
  js_output.write(marker_var.format(marker_name, marker["lat"], marker["lon"], marker["subcat"].replace(" ", "")))

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
  js_output.write("marker{0}.bindPopup({1}); ".format(index, pop_text))
  js_output.write("cluster.addLayer(marker{0});\n".format(index))

  if marker["eyear"] == "":
    if not marker["syear"] in start_dict:
      start_dict[marker["syear"]] = []
    start_dict[marker["syear"]].append("marker{0}".format(index))
  else:
    if marker["eyear"] == marker["syear"]:
      if not marker["syear"] in iso_dict:
        iso_dict[marker["syear"]] = []
      iso_dict[marker["syear"]].append("marker{0}".format(index))
    else:
      key = "{0}_{1}".format(marker["syear"], marker["eyear"])
      if not key in range_dict:
        range_dict[key] = []
      range_dict[key].append("marker{0}".format(index))

  if not marker["cat"] in cat_dict:
    cat_dict[marker["cat"]] = {}
  if not marker["subcat"] in cat_dict[marker["cat"]]:
    cat_dict[marker["cat"]][marker["subcat"]] = []
  cat_dict[marker["cat"]][marker["subcat"]].append(marker_name)

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


# Create chronological layers
js_output.write("\n")
for year in start_dict:
  js_output.write("var start{0}Layer = L.layerGroup([".format(year))
  for object in start_dict[year]:
    js_output.write("{0},".format(object))
  js_output.write("]);\n")

js_output.write("\n")
for year in iso_dict:
  js_output.write("var iso{0}Layer = L.layerGroup([".format(year))
  for object in iso_dict[year]:
    js_output.write("{0},".format(object))
  js_output.write("]);\n")

js_output.write("\n")
for range in range_dict:
  js_output.write("var range{0}Layer = L.layerGroup([".format(range))
  for object in range_dict[range]:
    js_output.write("{0},".format(object))
  js_output.write("]);\n")

js_output.write("\n")

# Create (sub)categorical layers
overlayer = []

for category in cat_dict:
  layer_name = "{0}Layer".format(category.replace(" ", ""))
  layer = "'{0}': {1},".format(category, layer_name) 
  overlayer.append(layer)
  cat_markers = []

  for subcategory in cat_dict[category]:
    sublayer_name = "{0}Layer".format(subcategory.replace(" ", ""))
    sublayer = "' -- {0}': {1},".format(subcategory, sublayer_name) 
    overlayer.append(sublayer)

    js_output.write("var {0} = L.layerGroup([".format(sublayer_name)) 
    for marker in cat_dict[category][subcategory]:
      marker_fmt = "{0},".format(marker)
      cat_markers.append(marker_fmt)
      js_output.write(marker_fmt)
    js_output.write("]);\n") 

  js_output.write("var {0} = L.layerGroup([".format(layer_name)) 
  for marker in cat_markers:
    js_output.write(marker)
  js_output.write("]);\n")


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


js_output.write("var overlays = {")
for overlay in overlayer:
  js_output.write(overlay)
js_output.write("};\n")

js_output.write("\n")

# Create basemap layer, map and control panel
js_output.write("var baseLayers = {")
for base in base_layer:
  js_output.write(base)
js_output.write("};\n")


js_output.write("var southWest = L.latLng(-68.13885, -178.59385)\n")
js_output.write("var northEast = L.latLng(79.68718, 189.14063)\n")
js_output.write("var bounds = L.latLngBounds(southWest, northEast);\n")

js_output.write("\n")
js_output.write("var map = L.map('map', {{ center: {0}, zoom: {1}, maxBounds: bounds }});\n".format(settings.init_center, settings.init_zoom))
js_output.write("L.control.layers(baseLayers, overlays).addTo(map);\n\n")
js_output.write("\nmap.addLayer(cluster);\n\n")


# setBasemap funtion
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

# setStarts function
js_output.write("function setStarts(time) {\n")
for year in start_dict:
  js_output.write("\tif (time >= {0}) {{\n".format(year))
  js_output.write("\t\tmap.addLayer(start{0}Layer);\n".format(year))
  js_output.write("\t} else {\n")
  js_output.write("\t\tmap.removeLayer(start{0}Layer);\n".format(year))
  js_output.write("\t}\n")
js_output.write("};\n\n")

# setIsos function
js_output.write("function setIsos(time) {\n")
for year in iso_dict:
  js_output.write("\tif (time === {0}) {{\n".format(year))
  js_output.write("\t\tmap.addLayer(iso{0}Layer);\n".format(year))
  js_output.write("\t} else {\n")
  js_output.write("\t\tmap.removeLayer(iso{0}Layer);\n".format(year))
  js_output.write("\t}\n")
js_output.write("};\n\n")

# setRanges function
js_output.write("function setRanges(time) {\n")
for year in range_dict:
  s = year.split("_")
  js_output.write("\tif (time >= {0} && time <= {1}) {{\n".format(s[0], s[1]))
  js_output.write("\t\tmap.addLayer(range{0}Layer);\n".format(year))
  js_output.write("\t} else {\n")
  js_output.write("\t\tmap.removeLayer(range{0}Layer);\n".format(year))
  js_output.write("\t}\n")
js_output.write("};\n\n")

# setData function
js_output.write("function setData(time) {\n")
js_output.write("\tsetBasemap(time);\n")
js_output.write("\tsetStarts(time);\n")
js_output.write("\tsetIsos(time);\n")
js_output.write("\tsetRanges(time);\n")
js_output.write("};\n")
js_output.close()

print "\033[92mDone!\033[0m"
print "New data.js created, old data.js has been moved to:"
print cwd + "/backups/\033[91mdata_" + tf + ".js\033[0m"
