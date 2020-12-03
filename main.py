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
from simple_hierarchy.hierarchal_model import HierarchalModel 
import torchvision.transforms as transforms
import torchvision
import torch
import numpy as np
from qwikidata.entity import WikidataItem, WikidataLexeme, WikidataProperty
from qwikidata.linked_data_interface import get_entity_dict_from_api

# If `entrypoint` is not defined in app.yaml, App Engine will look for an app
# called `app` in `main.py`.
base_model = torchvision.models.resnext101_32x8d(pretrained = True)
class DemoModel(torch.nn.Module):
	def __init__(self):
		super(DemoModel, self).__init__()
		hierarchy = {
			('A', 3) : [('B', 30)]
		}
		self.model = HierarchalModel(base_model=base_model, 
						hierarchy=hierarchy, size=(1000,256,256), 
						output_order=[('A', 3), ('B',30)])
	def forward(self, x):
		return self.model(x)
	def only_district_out(self, x):
		return self.model(x)[1]
	def load_state_dict(self, weights):
		self.model.load_state_dict(weights)
model = DemoModel()
model.load_state_dict(torch.load('best_model_so_far.pth', map_location='cpu'))
model.to(device='cpu')
model.eval()

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
	geolink, max_confidence = text_parser(listText)

	tags['Text Privacy Score'] = 1

	if geolink != "":
		tags, area = get_tags(geolink)
		tags['geolink'] = geolink
		tags['confidence'] = max_confidence
		tags['Text Privacy Score'] = get_text_score(tags['confidence'], area)


	transform = transforms.Compose([
		transforms.Resize(256),
		transforms.CenterCrop(224),
		transforms.ToTensor()
	])
	transform_normalize = transforms.Normalize(
		mean=[0.485, 0.456, 0.406],
		std=[0.229, 0.224, 0.225]
	)
	transformed_img = transform(image)
	input = transform_normalize(transformed_img)
	out_c, out_d = model(input.unsqueeze(0))		
	probs_c = torch.softmax(out_c, dim=1)		
	probs_d = torch.softmax(out_d, dim=1)
	prob_d, district = torch.max(probs_d, dim=1)	
	city_names = ["Pittsburg", "Orlando","Manhattan"]

	prob_c, city = torch.max(probs_c, dim=1)
	image_score = get_image_score(prob_c.item(), prob_d.item())
	pred_city = city_names[city.item()]
	if image_score == 1:
		pred_city = ""

	comp_listText = [
		pred_city + " " + image_caption,
	]
	print(comp_listText)
	comp_geolink, comp_max_confidence = text_parser(comp_listText)

	comp_tags = {}
	comp_tags['Text Privacy Score'] = 1
	if comp_geolink != "":
		comp_tags, comp_area = get_tags(comp_geolink)
		comp_tags['geolink'] = comp_geolink
		comp_tags['confidence'] = comp_max_confidence
		comp_tags['Composite Privacy Score'] = get_text_score(comp_tags['confidence'], comp_area)

	print('text scores', tags)
	print('composite scores', comp_tags)

	return {'geolink': tags, 'composite scores': comp_tags, 'image_results' : {'Image Privacy Score': image_score, 'District':district.item() % 10, 'City':pred_city}}

def get_image_score(city_conf, district_conf, c=0.8):
	if city_conf >= c:
		return 1-district_conf
	return 1


def get_text_score(confidence, area, area_const=16.79*2): #16.79 is average size in pittsburgh
	if area == 0:
		return confidence

	return confidence*min(1, area/area_const)

def text_parser(listText):
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
	max_confidence=0
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
		confidences= geoparsepy.geo_parse_lib.calc_location_confidence( listLocMatches, dictGeospatialConfig, geom_context = strGeom, geom_cache = dictGeomResultsCache)

		size, max_confidence = len(confidences), 0 if len(confidences) == 0 else max(confidences)

		if max_confidence == 1:
			max_confidence = .5
		elif max_confidence > 1 and max_confidence < 100:
			max_confidence = .5 + .25*max_confidence / 99
		else:
			max_confidence = .75 + .25*max_confidence / 300

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

	return geolink, max_confidence

@app.route('/feature-occlusion', methods = ["POST"])
def feature_occlusion():
	from captum.attr import IntegratedGradients
	from captum.attr import GradientShap
	from captum.attr import Occlusion
	from captum.attr import NoiseTunnel
	from captum.attr import visualization as viz
	import torch.nn.functional as F
	import time 
	print(np.array([1]))
	image = request.files.get('image')
	image = retrieve_image_from_file(image)
	st = time.time()
	transform = transforms.Compose([
		transforms.Resize(256),
		transforms.CenterCrop(224),
		transforms.ToTensor()
	])


	transform_normalize = transforms.Normalize(
			mean=[0.485, 0.456, 0.406],
			std=[0.229, 0.224, 0.225]
		)


	transformed_img = transform(image)

	input = transform_normalize(transformed_img)
	input = input.unsqueeze(0)
	occlusion = Occlusion(model.only_district_out)
	cit, dis = model(input)
	probs = torch.softmax(dis, dim=1)
	probability, pred_label_idx = probs.max(dim=1)
	pred_label_idx.squeeze_()
	
	attributions_occ = occlusion.attribute(input,
											strides = (3, 8, 8),
											target=pred_label_idx,
											sliding_window_shapes=(3,15, 15),
											baselines=0)

	fig, ax = viz.visualize_image_attr_multiple(np.transpose(attributions_occ.squeeze().cpu().detach().numpy(), (1,2,0)),
											np.transpose(transformed_img.squeeze().cpu().detach().numpy(), (1,2,0)),
											["original_image", "heat_map"],
											["all", "positive"],
											show_colorbar=True,
											outlier_perc=2,
											)

	logger.info(('Seconds it took to run : ' + str(time.time() - st)))
	fig.savefig('./static/images/occlusion.svg')
	return {'location': '/static/images/occlusion.svg'}


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

	wikidata_key = tags['wikidata']


	area = get_wikidata_area(wikidata_key)

	return tags, area


def get_wikidata_area(entity):
	try:
		entity_dict = get_entity_dict_from_api(entity)
		return float(entity_dict['claims']['P2046'][0]['mainsnak']['datavalue']['value']['amount'])
	except:
		return 0


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
	app.run(host='0.0.0.0', debug=True, use_reloader=False)
