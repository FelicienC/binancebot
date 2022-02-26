# Binance-Bot

This projects aims at creating a simple crypto-currency trading bot running on Google Cloud Platform. It uses the Binance API to trade on the spot market, and Google Cloud's BigQuery integrated machine learning models to detect favorable opportunities. 


## How does it work ? 

Every minute, a Cloud Function is triggered, calling Binance's API to get the latest price information for a set of coins.
With that price, and the stored prices of these coins of the preceding 1440 minutes, the function calls an ML model running in BigQuery, which produces an estimation of the probability that each considered coin will undergo a 1% growth in the comming hour. This estimation is compared to a preset threshold to determine if the coin should be purchased or not. If whithin that hour, the coin does not reach the stop loss or the take profit limits, it is sold.

## Disclaimer

This project is just meant as an experiment of BigQuery's ML capabilities, by no means am I an expert in trading or finance, so if you whish to use this project with your own funds, make sure you understand what you are doing ! (There are also simpler ways to run and maintain an ML model on Google Cloud)


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

Enable the cloud function, cloud data transfer, scheduler and build APIs :
```
gcloud services enable bigquerydatatransfer.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable cloudbuild.googleapis.com
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
export project="PROJECT_ID"
```

Deploy the infrastructure :
```
make deploy
```

## 4 - Training of the ML models

Use the tool script to load the data in your BigQuery infrastructure :
```
cd tools
python complete_historical_data.py    
```

Create the model using the stored procedure to train them : 
```

```


## 5 - Connection to the Binance API

Once the secrets' IAC has been created, you can [generate an API key](https://www.binance.com/en/support/faq/360002502072) with your Binance Account and insert it in Google Cloud's secret manager :

````
printf "your private secret" | gcloud secrets versions add secret-binance-private 
printf "your api key"| gcloud secrets versions add secret-binance 
```

# TODO :
- [ ] set up a production environnement
- [ ] implement daily status emails
- [ ] keep old models and only change to a new one if it increases the performance
- [ ] Test the setup procedure on a new project

# DONE :
- Add legend to the diagram
- improve complete_hist script
- fix threshold update 
- code refactoring
- add coverage in the makefile
- Finish writing tests... -> reach 100% coverage
- fix sales -> Need to be deployed
- switching to a class
- add connection to Binance
- add secret management
- set up linter for python code quality
- use tfsec
- use hash to allow the re-creation of the function on the update of the code
- create a tool script to fill the gaps in the data !!!!!
- add schema
- add functions to terraform iac
- remove cleaning jobs
- terraform for cloud scheduler and pubsub
- optimize cloud functions
- use warm start persistent memory to avoid queries
- parallelize the estimation
- evaluate models on the new data
- update cloud function to use all models to make predictions
- create scheduled query every month to retrain the model
- create models using terraform and procedures
- create an evaluation view (using only the latest month) ?
- create procedure to remove duplicates 
- update the training view to not use the last month
- script to fill tables for all coins 
- add coins to function reading the data 
- terraform resource tables for each coin  
- terraform resource schedueled query for each coin
- create view for prediction