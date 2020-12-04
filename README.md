# Image Caption Geolocalization Tool
Source code repository for our vision, language tool.

# Project Notebooks:
These are found in the Project Notebooks Folder. There are notebooks to show the training and testing of the image model, and the set up of geoparsepy, the python library that is being used to parse text. The content provides a more thorough understanding of our technical process. 


## Overview
This webpage is implemented using Flask, and is configured in the app.yaml file to run using Google App Engine.

main.py: The app includes the code for text parsing, and for predicting the location of the image. It also includes subroutines to calculate the scores described in the research paper. 

## Requirements
- Setup a conda environment and install some prerequisite packages like this
```bash
conda create -n vislang python=3.7    # Create a virtual environment
source activate vislang         	    # Activate virtual environment
conda install whoosh flask  # Install dependencies
# Download pickledObjects.zip from https://drive.google.com/file/d/1JklZyNSSON5sndl8SufbSA_kpjr7DIsF/view?usp=sharing and put in folder
unzip pickledObjects.zip # Unzip pickled variables to reduce latency

```


## Data 
This code depens on data from the SBU dataset which is provided as a JSON file here http://www.cs.virginia.edu/~vicente/sbucaptions/ 
and the caption JSON file for the COCO dataset which is provded here http://cocodataset.org/#download

## Running the website
In order to test the website only the following commands need to be run.
```bash
source activate vislang
export FLASK_ENV=development
export FLASK_APP=main.py
flask run
```
The server is now run on port 5000, not 8080

## Deploying the website on Google App Engine.
Create a Google App Engine account on Google Cloud and start a a project. You can see how to setup and configure a basic Flask app on Google App Engine here https://codelabs.developers.google.com/codelabs/cloud-app-engine-python3/#0

Once everything is installed you should be able to just deploy using the following command:

```bash
gcloud app deploy
```
