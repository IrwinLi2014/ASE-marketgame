# ASE-marketgame

[![Build Status](https://travis-ci.org/wanlinxie/ASE-marketgame.svg?branch=master)](https://travis-ci.org/wanlinxie/ASE-marketgame)

## Deployment
For deployment, first install the requirements through pip3 after creating and entering an isolated Python environment using `virtualenv`
```
$ virtualenv -p python3.5 env
$ source env /bin/activate
$ pip3 install -t lib -r requirements.txt
```
This will install the requirements into the `lib/` directory, which is necessary for deployment to Google Cloud.
To deploy on Google Cloud, first install the Google Cloud SDK, then run:
```
$ gcloud app deploy
```
