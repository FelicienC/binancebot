# Binance-Bot

This projects aims at creating a simple crypto-currency trading bot running on Google Cloud Platform. It uses the Binance API to trade on the spot market, and Google Cloud's BigQuery integrated machine learning models to detect favorable opportunities. 


## How does it work ? 

Every minute, a Cloud Function is triggered, calling Binance's API to get the latest price information for a set of coins.
With that price, and the stored prices of these coins of the preceding 1440 minutes, the function calls an ML model running in BigQuery. The model produces an estimation of the probability that each considered coin will undergo a 1% growth in the comming hour. This estimation is compared to a preset threshold to determine if the coin should be purchased or not. If whithin that hour, the coin does not reach the stop loss or the take profit limits, it is sold.

Every month, the models are re-trained using the latest available data. The thresholds defining the 

## Disclaimer

This project is just meant as an experiment of BigQuery's ML capabilities, so if you whish to use this project with your own funds, make sure you understand what you are doing ! There are also simpler ways to run a machine learning model on Google Cloud, if you are interested in the 


## What is in this repository ?

### IAC (infrastructure as code) 
The infrastructure used in this project is defined with terraform, and contained in the iac folder. This code allows the automatic deployement of resources of the following Google Cloud services:
- Functions 
- BigQuery Datasets
- BigQuery Stored Procedures 
- BigQuery Schedueled Queries
- BigQuery Tables
- BigQuery Views 
- Secrets 
- Scheduler 
- PubSub

These resources are arranged as described in the folowing diagram :
![infrastructure-schema](docs/schema.svg)

### Tools
The tools folders contains:
- A parameter file used to define the number of coins which are to be used by the bot to make the predictions, coin.lst.
- A python script that can be used to fill the tables with Binance data 
- A script generating the terraform infrastructure for the coins listed in the parameter file


# Useful commands

The makefile at the root of this repository can be used to easily deploy the infrastructure.

To make sure that the infrastructure change you would deploy are coherent with your expectations, you can look at Terraforms output provided by this command:

```
make plan
```

To deploy it, simply run
```
make deploy
```
(Please see the Setup section for the first deployment)

# Project Setup 

1. Installation of the required software
2. Google Cloud project setup
3. Creation of the infrastructure
4. Training of the ML models
5. Connection to the Binance API


## 1 - Installation of required tools

If you wish to setup this bot, you need to use:

 - [The gcloud CLI](https://cloud.google.com/sdk/docs/install)
 - [Terrafom](https://learn.hashicorp.com/tutorials/terraform/install-cli)
 - [Tfsec](https://github.com/aquasecurity/tfsec)


## 2 - Setup of the Google Cloud Project

Create a google cloud project using the Google Cloud CLI
```
 gcloud projects create PROJECT_ID
```
Make sure this is now set as your default project
```
 gcloud config set project PROJECT_IT
```
Link the project to a billing account in GCP (even if we can stay in the free tier, this is needed for certain APIs)

Enable the cloud function, cloud data transfer, scheduler and build APIs :
```
gcloud services enable bigquerydatatransfer.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

## 3 - Creation of the infrastructure

List the coins you want your bot to use in the coin.lst parameter file of the tools folder
```
ETH
BTC
BNB
```

:warning: **Google Cloud's free Tier**: If you want to stay in  the free tier, do not use more than 3 coins (pricing of January 2022)

```
export TF_VAR_project=PROJECT_ID
```

Initialize terraform 
```
make init
```

Deploy the infrastructure :
```
make deploy
```

At that point, terraform should yield errors, because some views being created need the construction of the ml models first, which we can build in the folowing step :

## 4 - Training of the ML models

Use the tool script to load the Binance data in your BigQuery infrastructure :
```
cd tools
python complete_historical_data.py    
```

Create the model using the stored procedure to train them : 
```
bq query --nouse_legacy_sql "CALL `PROJECT_ID.models.update_model_COIN`();"
bq query --nouse_legacy_sql "CALL `PROJECT_ID.models.update_model_COIN`();"
```

Deploy the infrastructure again
```
make deploy
```

## 5 - Connection to the Binance API

Once the secrets' IAC has been created, you can [generate an API key](https://www.binance.com/en/support/faq/360002502072) with your Binance Account and insert it in Google Cloud's secret manager :

```
printf "your private secret" | gcloud secrets versions add secret-binance-private 
printf "your api key"| gcloud secrets versions add secret-binance 
```

That's it, now your bot is running, you should be able to see the result in the trades table. 

# TODO :
- [ ] set up a production environnement
- [ ] implement daily status emails
- [ ] keep old models and only change to a new one if it increases the performance