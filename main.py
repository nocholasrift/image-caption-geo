'''
	Main app for vislang.ai
'''
import random, io, time
import requests as http_requests
import xml.etree.ElementTree as ET 

from collections import defaultdict

from flask import Flask, request, redirect, flash, url_for
from flask import render_template
import validators

from whoosh import index
from whoosh.qparser import QueryParser

from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

from pagination import Pagination
from utils import resize_image, center_crop_image, image2string, rotate_image_if_needed
import pickle

# If `entrypoint` is not defined in app.yaml, App Engine will look for an app
# called `app` in `main.py`.
app = Flask(__name__)

@app.route('/', methods=['GET'])
def main():
	return render_template('index.html')

# def initialize_parameters():
# 	LOG_FORMAT = ('%(message)s')
# 	logger = logging.getLogger( __name__ )
# 	logging.basicConfig( level=logging.INFO, format=LOG_FORMAT )
# 	logger.info('logging started')

# 	with open('pickledObjects/dictGeospatialConfig.pkl', 'rb') as f:
# 	    dictGeospatialConfig = pickle.load(f)
# 	print('loaded dictGeospatialConfig')   

# 	with open('pickledObjects/dictLocationIDs.pkl', 'rb') as f:
# 	    dictLocationIDs = pickle.load(f)
# 	print('loaded dictLocationIDs')    

# 	with open('pickledObjects/listFocusArea.pkl', 'rb') as f:
# 	    listFocusArea = pickle.load(f)
# 	print('loaded listFocusArea')    

# 	with open('pickledObjects/cached_locations.pkl', 'rb') as f:
# 	    cached_locations = pickle.load(f)
# 	print('loaded cached_locations')    

# 	with open('pickledObjects/indexed_locations.pkl', 'rb') as f:
# 	    indexed_locations = pickle.load(f)
# 	print('loaded indexed_locations')  

# 	with open('pickledObjects/osmid_lookup.pkl', 'rb') as f:
# 	    osmid_lookup = pickle.load(f)
# 	print('loaded osmid_lookup')    

# 	with open('pickledObjects/dictGeomResultsCache.pkl', 'rb') as f:
# 	    dictGeomResultsCache = pickle.load(f)
# 	print('loaded dictGeomResultsCache')   
	    
# 	indexed_geoms = geoparsepy.geo_parse_lib.calc_geom_index( cached_locations )
# 	print('initialized indexed_geoms') 

# 	return logger, dictGeospatialConfig, dictLocationIDs, listFocusArea, cached_locations, indexed_locations, indexed_geoms, osmid_lookup, dictGeomResultsCache

# Simple Demo demo.
import imghdr, json
from PIL import Image

# Restrict filetypes allowed.  
# Important: This doesn't just check for file extensions.
ALLOWED_IMAGE_TYPES = ['jpeg' , 'png']

# Configure app to allow maximum  of 32 MB image file sizes.
# Note: This will send a 403 HTTP error page. 
# So we will need to validate file size on the client side.
# Client side could have a stricter requirement size.
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024


####################################################

# *****************************
# Load model stuff here
# *****************************

####################################################

import soton_corenlppy, geoparsepy, nltk
import os, sys, logging, traceback, codecs, datetime, copy, time, ast, math, re, random, shutil, json


#global variables:
LOG_FORMAT = ('%(message)s')
logger = logging.getLogger( __name__ )
logging.basicConfig( level=logging.INFO, format=LOG_FORMAT )
logger.info('logging started')

with open('pickledObjects/dictGeospatialConfig.pkl', 'rb') as f:
    dictGeospatialConfig = pickle.load(f)
print('loaded dictGeospatialConfig')   

with open('pickledObjects/dictLocationIDs.pkl', 'rb') as f:
    dictLocationIDs = pickle.load(f)
print('loaded dictLocationIDs')    

with open('pickledObjects/listFocusArea.pkl', 'rb') as f:
    listFocusArea = pickle.load(f)
print('loaded listFocusArea')    

with open('pickledObjects/cached_locations.pkl', 'rb') as f:
    cached_locations = pickle.load(f)
print('loaded cached_locations')    
	
with open('pickledObjects/indexed_locations.pkl', 'rb') as f:
    indexed_locations = pickle.load(f)
print('loaded indexed_locations')  

with open('pickledObjects/osmid_lookup.pkl', 'rb') as f:
    osmid_lookup = pickle.load(f)
print('loaded osmid_lookup')    

with open('pickledObjects/dictGeomResultsCache.pkl', 'rb') as f:
    dictGeomResultsCache = pickle.load(f)
print('loaded dictGeomResultsCache')   
    
indexed_geoms = geoparsepy.geo_parse_lib.calc_geom_index( cached_locations )
print('initialized indexed_geoms') 

@app.route('/simple-demo', methods = ["GET", "POST"])
def simple_demo():
	# If the request is GET then only render template.
	if request.method == "GET":
		return render_template('simple-demo.html')

	print(request.form)
	print(request.files)
	image = request.files.get('image')
	image = retrieve_image_from_file(image)
	image_caption = str(request.form.get('image_caption'))
	print("image caption is", image_caption)
	tags={}
	listText = [
		image_caption,
	]

	listTokenSets = []
	listGeotags = []
	for nIndex in range(len(listText)) :
		strUTF8Text = listText[ nIndex ]
		listToken = soton_corenlppy.common_parse_lib.unigram_tokenize_text( text = strUTF8Text, dict_common_config = dictGeospatialConfig )
		listTokenSets.append( listToken )
		listGeotags.append( None )

	listMatchSet = geoparsepy.geo_parse_lib.geoparse_token_set( listTokenSets, indexed_locations, dictGeospatialConfig )

	strGeom = 'POINT(-1.4052268 50.9369033)'
	listGeotags[0] = strGeom

	listMatchGeotag = geoparsepy.geo_parse_lib.reverse_geocode_geom( [strGeom], indexed_geoms, dictGeospatialConfig )
	if len( listMatchGeotag[0] ) > 0  :
		for tupleOSMIDs in listMatchGeotag[0] :
			setIndexLoc = osmid_lookup[ tupleOSMIDs ]
			for nIndexLoc in setIndexLoc :
				strName = cached_locations[nIndexLoc][1]
				logger.info( 'Reverse geocoded geotag location [index ' + str(nIndexLoc) + ' osmid ' + repr(tupleOSMIDs) + '] = ' + strName )

	for nIndex in range(len(listMatchSet)) :
		logger.info( 'Text = ' + listText[nIndex] )
		listMatch = listMatchSet[ nIndex ]
		strGeom = listGeotags[ nIndex ]
		setOSMID = set([])
		for tupleMatch in listMatch :
			nTokenStart = tupleMatch[0]
			nTokenEnd = tupleMatch[1]
			tuplePhrase = tupleMatch[3]
			for tupleOSMIDs in tupleMatch[2] :
				setIndexLoc = osmid_lookup[ tupleOSMIDs ]
				for nIndexLoc in setIndexLoc :
					logger.info( 'Location [index ' + str(nIndexLoc) + ' osmid ' + repr(tupleOSMIDs) + ' @ ' + str(nTokenStart) + ' : ' + str(nTokenEnd) + '] = ' + ' '.join(tuplePhrase) )
					break
		listLocMatches = geoparsepy.geo_parse_lib.create_matched_location_list( listMatch, cached_locations, osmid_lookup )
		geoparsepy.geo_parse_lib.filter_matches_by_confidence( listLocMatches, dictGeospatialConfig, geom_context = strGeom, geom_cache = dictGeomResultsCache )
		geoparsepy.geo_parse_lib.filter_matches_by_geom_area( listLocMatches, dictGeospatialConfig )
		geoparsepy.geo_parse_lib.filter_matches_by_region_of_interest( listLocMatches, [-148838, -62149], dictGeospatialConfig )
		setOSMID = set([])
		for nMatchIndex in range(len(listLocMatches)) :
			nTokenStart = listLocMatches[nMatchIndex][1]
			nTokenEnd = listLocMatches[nMatchIndex][2]
			tuplePhrase = listLocMatches[nMatchIndex][3]
			strGeom = listLocMatches[nMatchIndex][4]
			tupleOSMID = listLocMatches[nMatchIndex][5]
			dictOSMTags = listLocMatches[nMatchIndex][6]
			if not tupleOSMID in setOSMID :
				setOSMID.add( tupleOSMID )
				listNameMultilingual = geoparsepy.geo_parse_lib.calc_multilingual_osm_name_set( dictOSMTags, dictGeospatialConfig )
				strNameList = ';'.join( listNameMultilingual )
				strOSMURI = geoparsepy.geo_parse_lib.calc_OSM_uri( tupleOSMID, strGeom )
				logger.info( 'Disambiguated Location [index ' + str(nMatchIndex) + ' osmid ' + repr(tupleOSMID) + ' @ ' + str(nTokenStart) + ' : ' + str(nTokenEnd) + '] = ' + strNameList + ' : ' + strOSMURI )

	listTokenSets = []
	listGeotags = []
	for nIndex in range(len(listText)) :
		strUTF8Text = listText[ nIndex ]
		listToken = soton_corenlppy.common_parse_lib.unigram_tokenize_text( text = strUTF8Text, dict_common_config = dictGeospatialConfig )
		listTokenSets.append( listToken )
		listGeotags.append( None )

	listMatchSet = geoparsepy.geo_parse_lib.geoparse_token_set( listTokenSets, indexed_locations, dictGeospatialConfig )

	strGeom = 'POINT(-1.4052268 50.9369033)'
	listGeotags[0] = strGeom

	listMatchGeotag = geoparsepy.geo_parse_lib.reverse_geocode_geom( [strGeom], indexed_geoms, dictGeospatialConfig )
	if len( listMatchGeotag[0] ) > 0  :
		for tupleOSMIDs in listMatchGeotag[0] :
			setIndexLoc = osmid_lookup[ tupleOSMIDs ]
			for nIndexLoc in setIndexLoc :
				strName = cached_locations[nIndexLoc][1]
				logger.info( 'Reverse geocoded geotag location [index ' + str(nIndexLoc) + ' osmid ' + repr(tupleOSMIDs) + '] = ' + strName )

	geolink=""
	for nIndex in range(len(listMatchSet)) :
		logger.info( 'Text = ' + listText[nIndex] )
		listMatch = listMatchSet[ nIndex ]
		strGeom = listGeotags[ nIndex ]
		setOSMID = set([])
		for tupleMatch in listMatch :
			nTokenStart = tupleMatch[0]
			nTokenEnd = tupleMatch[1]
			tuplePhrase = tupleMatch[3]
			for tupleOSMIDs in tupleMatch[2] :
				setIndexLoc = osmid_lookup[ tupleOSMIDs ]
				for nIndexLoc in setIndexLoc :
					logger.info( 'Location [index ' + str(nIndexLoc) + ' osmid ' + repr(tupleOSMIDs) + ' @ ' + str(nTokenStart) + ' : ' + str(nTokenEnd) + '] = ' + ' '.join(tuplePhrase) )
					break
		listLocMatches = geoparsepy.geo_parse_lib.create_matched_location_list( listMatch, cached_locations, osmid_lookup )
		geoparsepy.geo_parse_lib.filter_matches_by_confidence( listLocMatches, dictGeospatialConfig, geom_context = strGeom, geom_cache = dictGeomResultsCache )
		geoparsepy.geo_parse_lib.filter_matches_by_geom_area( listLocMatches, dictGeospatialConfig )
		geoparsepy.geo_parse_lib.filter_matches_by_region_of_interest( listLocMatches, [-148838, -62149], dictGeospatialConfig )
		setOSMID = set([])
		for nMatchIndex in range(len(listLocMatches)) :
			nTokenStart = listLocMatches[nMatchIndex][1]
			nTokenEnd = listLocMatches[nMatchIndex][2]
			tuplePhrase = listLocMatches[nMatchIndex][3]
			strGeom = listLocMatches[nMatchIndex][4]
			tupleOSMID = listLocMatches[nMatchIndex][5]
			dictOSMTags = listLocMatches[nMatchIndex][6]
			if not tupleOSMID in setOSMID :
				setOSMID.add( tupleOSMID )
				listNameMultilingual = geoparsepy.geo_parse_lib.calc_multilingual_osm_name_set( dictOSMTags, dictGeospatialConfig )
				strNameList = ';'.join( listNameMultilingual )
				strOSMURI = geoparsepy.geo_parse_lib.calc_OSM_uri( tupleOSMID, strGeom )
				logger.info( 'Disambiguated Location [index ' + str(nMatchIndex) + ' osmid ' + repr(tupleOSMID) + ' @ ' + str(nTokenStart) + ' : ' + str(nTokenEnd) + '] = ' + strNameList + ' : ' + strOSMURI )
				if nMatchIndex == 0:
					geolink=strOSMURI

	if geolink != "":
		tags = get_tags(geolink)
		tags['geolink'] = geolink
		return tags

	return {'geolink': geolink}


def get_tags(url):
	tags= defaultdict(list)

	relation_id = url[url.rfind("/",0, url.rfind("/"))+1:]
	xml_url = 'https://www.openstreetmap.org/api/0.6/'+relation_id

	r = http_requests.get(xml_url)

	with open('metadata.xml', 'wb') as f:
		f.write(r.content)

	xml_tree = ET.parse('metadata.xml')
	root = xml_tree.getroot()
	parent=relation_id.split('/')[0]

	for elem in root.findall('./'+parent+'/tag'):
		# print(elem.attrib)
		tags[elem.attrib['k']]=elem.attrib['v']

	return tags


def retrieve_image_from_file(file):
	fname = file.filename
	if len(fname) > 22: fname = fname[:10] + "..." + fname[-10:]

	# Verify if this is a valid image type.
	filestream = file.read()
	image_type = imghdr.what("", h = filestream)

	# Read the image directly from the file stream.
	file.seek(0)  # Reset file stream pointer.
	img = Image.open(file).convert('RGB')

	# If the image is uploaded from a mobile device.
	# this avoids having the image rotated.
	img = rotate_image_if_needed(img)

	return img

if __name__=='__main__':
	app.run(debug=True, use_reloader=False)
