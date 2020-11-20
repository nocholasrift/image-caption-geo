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

# If `entrypoint` is not defined in app.yaml, App Engine will look for an app
# called `app` in `main.py`.
app = Flask(__name__)

@app.route('/', methods=['GET'])
def main():
	return render_template('index.html')



# Simple Demo demo.
import imghdr, json
from PIL import Image

# Restrict filetypes allowed.  
# Important: This doesn't just check for file extensions.
ALLOWED_IMAGE_TYPES = ['jpeg' , 'png']

# Configure app to allow maximum  of 15 MB image file sizes.
# Note: This will send a 403 HTTP error page. 
# So we will need to validate file size on the client side.
# Client side could have a stricter requirement size.
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024


####################################################

# *****************************
# Load model stuff here
# *****************************

####################################################

import soton_corenlppy, geoparsepy, nltk
import os, sys, logging, traceback, codecs, datetime, copy, time, ast, math, re, random, shutil, json

@app.route('/simple-demo', methods = ["GET", "POST"])
def simple_demo():

	# If the request is GET then only render template.
	if request.method == "GET":
		return render_template('simple-demo.html')

	image_caption = request.form.get('image_caption')
	print(type(image_caption), image_caption)

	logger, dictGeospatialConfig, databaseHandle, dictLocationIDs, listFocusArea = initialize_parameters()

	cached_locations = geoparsepy.geo_preprocess_lib.cache_preprocessed_locations( databaseHandle, dictLocationIDs, 'public', dictGeospatialConfig )
	logger.info( 'number of cached locations = ' + str(len(cached_locations)) )

	databaseHandle.close()

	indexed_locations = geoparsepy.geo_parse_lib.calc_inverted_index( cached_locations, dictGeospatialConfig )
	logger.info( 'number of indexed phrases = ' + str(len(indexed_locations.keys())) )

	indexed_geoms = geoparsepy.geo_parse_lib.calc_geom_index( cached_locations )
	logger.info( 'number of indexed geoms = ' + str(len(indexed_geoms.keys())) )

	osmid_lookup = geoparsepy.geo_parse_lib.calc_osmid_lookup( cached_locations )

	dictGeomResultsCache = {}

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
	
	tags = get_tags(geolink)
	tags['geolink'] = geolink
	print(tags)

	return tags


def get_tags(url):
	tags= defaultdict(list)

	relation_id = url[url.rfind("/")+1:]
	xml_url = 'https://www.openstreetmap.org/api/0.6/relation/'+relation_id
	r = http_requests.get(xml_url)

	with open('metadata.xml', 'wb') as f:
		f.write(r.content)

	xml_tree = ET.parse('metadata.xml')
	root = xml_tree.getroot()

	for elem in root.findall('./relation/tag'):
		# print(elem.attrib)
		tags[elem.attrib['k']]=elem.attrib['v']

	return tags

# def simple_demo():

# 	# If the request is GET then only render template.
# 	if request.method == "GET":
# 		return render_template('simple-demo.html')

# 	# If the request is POST then handle the upload.
# 	image_url = request.form.get('image_url')
# 	if image_url and validators.url(image_url):
# 		# TODO: Handle valid url and exceptions.
# 		response = http_requests.get(image_url)
# 		file = io.BytesIO(response.content)
# 		filename = image_url
# 	else:
# 		# Get file information just for display purposes.
# 		file = request.files.get('image')
# 		if not file:
# 			return {"error": "file-invalid", 
# 					"message": "The uploaded file is invalid"}
# 		filename = file.filename


# 	if len(filename) > 22: filename = filename[:10] + "..." + filename[-10:]

# 	# Verify if this is a valid image type.
# 	filestream = file.read()
# 	image_type = imghdr.what("", h = filestream)

# 	if image_type not in ALLOWED_IMAGE_TYPES:
# 		return {"error": "file-type-not-allowed",
# 				"message": "The uploaded file must be a JPG or PNG image"}

# 	# Read the image directly from the file stream.
# 	file.seek(0)  # Reset file stream pointer.
# 	img = Image.open(file).convert('RGB')

# 	# If the image is uploaded from a mobile device.
# 	# this avoids having the image rotated.
# 	img = rotate_image_if_needed(img)

# 	# Resize and crop the input image.
# 	img = resize_image(img, 256)
# 	img = center_crop_image(img, 224)

# 	# Encode the cropped  input image as a string for display.
# 	input_image_str = image2string(img)

# 	# Now process the image.
# 	from PIL import ImageFilter
# 	start_time = time.time()
# 	output_img = img.filter(ImageFilter.GaussianBlur(radius = 10))
# 	debug_str = 'process took %.2f seconds' % (time.time() - start_time)

# 	# Now let's try some pytorch.
# 	input_tensor = preprocess(img) # Convert to tensor.
# 	print(input_tensor.shape)  # Print shape.
	
# 	input_batch = input_tensor.unsqueeze(0)  # Add batch dim.
# 	print(model) # Print the model.
	
# 	outputs = model(input_batch)
# 	# print(outputs.shape)

# 	# Apply softmax and sort the values.
# 	probs, indices = (-outputs.softmax(dim = 1).data).sort()
# 	# Pick the top-5 scoring ones.
# 	probs = (-probs).numpy()[0][:5]; indices = indices.numpy()[0][:10]
# 	# Concat the top-5 scoring indices with the class names.
# 	preds = ['P[\"' + imagenetClasses[idx] + '\"] = ' + ('%.6f' % prob) \
#          for (prob, idx) in zip(probs, indices)]

# 	# Print top classes predicted.
# 	print('\n'.join(preds))
# 	debug_str = '\n'.join(preds)

# 	# Encode the output image as a string for display.
# 	output_image_str = image2string(output_img)

# 	return {'filename': filename, 
# 			'input_image': input_image_str, 
# 			'output_image': output_image_str,
# 			'debug_str': debug_str}

def initialize_parameters():
	LOG_FORMAT = ('%(message)s')
	logger = logging.getLogger( __name__ )
	logging.basicConfig( level=logging.INFO, format=LOG_FORMAT )
	logger.info('logging started')

	try:
		dictGeospatialConfig = geoparsepy.geo_parse_lib.get_geoparse_config( 
			lang_codes = ['en'],
			logger = logger,
			whitespace = u'"\u201a\u201b\u201c\u201d()',
			sent_token_seps = ['\n','\r\n', '\f', u'\u2026'],
			punctuation = """,;\/:+-#~&*=!?""",
			)
	except LookupError:
		nltk.download('stopwords')
		nltk.download('names')
		nltk.download('wordnet')
		nltk.download('omw')
		dictGeospatialConfig = geoparsepy.geo_parse_lib.get_geoparse_config( 
			lang_codes = ['en'],
			logger = logger,
			whitespace = u'"\u201a\u201b\u201c\u201d()',
			sent_token_seps = ['\n','\r\n', '\f', u'\u2026'],
			punctuation = """,;\/:+-#~&*=!?""",
			)

	databaseHandle = soton_corenlppy.PostgresqlHandler.PostgresqlHandler( 'postgres', 'geoparse', 'localhost', 5432, 'openstreetmap', 600 )

	dictLocationIDs = {}
	listFocusArea=[ 'global_cities', 'europe_places', 'north_america_places', 'uk_places' ]
	for strFocusArea in listFocusArea :
		dictLocationIDs[strFocusArea + '_admin'] = [-1,-1]
		dictLocationIDs[strFocusArea + '_poly'] = [-1,-1]
		dictLocationIDs[strFocusArea + '_line'] = [-1,-1]
		dictLocationIDs[strFocusArea + '_point'] = [-1,-1]

	return logger, dictGeospatialConfig, databaseHandle, dictLocationIDs, listFocusArea

# COCO Captions Explorer.
@app.route('/coco-explorer', methods = ["GET"])
def coco_search():

	# Obtain the query string.
	query_str = request.args.get("query", "dog playing with ball")
	page_num = request.args.get("page_num", 1, type = int)
	page_len = request.args.get("page_len", 20, type = int)
	split = request.args.get("split", "train")

	# Location for the whoosh index to be queried.
	coco_index_path = 'static/whoosh/cococaptions-indexdir-%s' % split
	# Pre-load whoosh index to query coco-captions.
	cococaptions_index = index.open_dir(coco_index_path)

	# Return results and do any pre-formatting before sending to view.
	with cococaptions_index.searcher() as searcher:
		query = QueryParser("caption", cococaptions_index.schema).parse(query_str)
		results = searcher.search_page(query, page_num, pagelen = page_len)

		result_set = list()
		for result in results:
			result_set.append({"image_id": result["image_url"],
							   "caption": result["caption"].split("<S>")})

	# Create pagination navigation if needed.
	pagination = Pagination(query_str, len(results), page_num, page_len, other_arguments = {'split': split})

	# Render results template.
	return render_template('coco-search.html', 
            results = result_set, query = query_str, split = split, pagination = pagination)

if __name__ == '__main__':
    # Used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    app.run(host='localhost', port=8080, debug=True)
