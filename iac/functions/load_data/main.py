"""
This google cloud function imports binance minute data of the previous day
into BigQuery using the public Binance API
"""
import json
import calendar
import concurrent.futures
from datetime import datetime
import requests
from google.cloud import bigquery

parameters = json.load(open("parameters.json"))
project = parameters["project"]
coin_list = parameters["coin_list"]
bq_client = bigquery.Client()


def get_previous_day(coin: str):
    """Get the close price of the last 1440 minutes for the specified coin"""
    today = datetime.utcnow().date()
    end_time = calendar.timegm(today.timetuple()) * 1000
    symbol = coin + "USDT"
    url = (
        "https://api.binance.com/api/v3/klines?interval=1m&limit=500"
        f"&symbol={symbol}"
        f"&endTime={end_time}"
    )
    response = requests.get(url, headers={}, data={})
    first_batch = json.loads(response.content)
    insert_data(coin, first_batch)
    url = (
        "https://api.binance.com/api/v3/klines?interval=1m&limit=500"
        f"&symbol={symbol}"
        f"&endTime={min(x[0] for x in first_batch)-60000}"
    )
    response = requests.get(url, headers={}, data={})
    second_batch = json.loads(response.content)
    insert_data(coin, second_batch)
    url = (
        "https://api.binance.com/api/v3/klines?interval=1m&limit=440"
        f"&symbol={symbol}"
        f"&endTime={min(x[0] for x in second_batch)-60000}"
    )
    response = requests.get(url, headers={}, data={})
    insert_data(coin, json.loads(response.content))


def insert_data(coin, data):
    """Insert the provided data lines in bigquery"""
    insertion = [
        "(TIMESTAMP_MILLIS("
        + str(element[0])
        + "),"
        + ", ".join(map(str, element[:-1]))
        + ")"
        for element in data
    ]

    bq_client.query(
        f"INSERT INTO `{project}.binance_data.minute_" + coin.lower() + "`"
        "(minute_timestamp,"
        " open_time,"
        " open,"
        " high,"
        " low,"
        " close,"
        " volume,"
        " close_time,"
        " quote_asset_volume,"
        " number_of_trades,"
        " taker_buy_base_asset_volume,"
        " taker_buy_quote_asset_volume)"
        "VALUES" + ",".join(insertion) + ";"
    )


def main(event, context):
    """
    Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    del event, context
    with concurrent.futures.ThreadPoolExecutor() as executor:
        res = [executor.submit(get_previous_day, coin) for coin in coin_list]
        concurrent.futures.wait(res)
