FROM postgres:12.5
FROM python:3.7-buster


RUN \
      apt-get update && apt-get install -y --no-install-recommends \
              postgis \
      && rm -rf /var/lib/apt/lists/*
# Python 3.7 install and update 
# install geoparsepy requirements
# install postgris


# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN python3 -m pip install -r requirements.txt
#RUN wget https://drive.google.com/file/d/1JklZyNSSON5sndl8SufbSA_kpjr7DIsF/view?usp=sharing
#RUN unzip pickledObjects.zip
RUN python3 -m pip install gdown
#RUN gdown https://drive.google.com/uc?id=1JklZyNSSON5sndl8SufbSA_kpjr7DIsF
RUN gdown https://drive.google.com/uc?id=1xUdBJukg620tgJdPYae8S_oazsYXGO28
#RUN unzip pickledObjects.zip
EXPOSE 5000
COPY . /app

ENV FLASK_APP main.py
ENV FLASK_ENV development
CMD ["flask", "run", "--host", "0.0.0.0"]