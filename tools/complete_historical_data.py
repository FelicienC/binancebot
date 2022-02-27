"""
This script fills the minute tables for all coin listed in the coin.lst file
between the current timestamp and the start time provided below
"""

import json
import time
import requests
import os

from google.cloud import bigquery

bq_client = bigquery.Client()
START_TIME = round(time.time()) * 1000 - 2 * 365 * 24 * 60 * 60 * 1000
PROJECT = os.getenv('TF_VAR_project')


def insert_data(coin, data):
    """
    Insert the provided data lines in bigquery
    """
    insertion = [
        "(TIMESTAMP_MILLIS("
        + str(element[0])
        + "),"
        + ", ".join(map(str, element[:-1]))
        + ")"
        for element in data
    ]
    bq_client.query(
        f"INSERT INTO `{PROJECT}.binance_data.minute_{coin.lower()}`"
        "(minute_timestamp, "
        "open_time, "
        "open, "
        "high, "
        "low, "
        "close, "
        "volume, "
        "close_time, "
        "quote_asset_volume, "
        "number_of_trades, "
        "taker_buy_base_asset_volume, "
        "taker_buy_quote_asset_volume) "
        "VALUES " + ",".join(insertion) + ";"
    )


def get_klines(symbol: str = None, end_time: int = None, start_time: int = None):
    """
    Request the 500 last minutes from the public Binance API and return them
    """
    print(f"{start_time} {end_time}", end="\r")

    end_time_str = "" if end_time is None else f"&endTime={end_time}"
    startime_str = "" if start_time is None else f"&startTime={start_time}"

    if symbol is None:
        url = (
            "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m"
            f"{end_time_str}{startime_str}"
        )
    else:
        url = (
            "https://api.binance.com/api/v3/klines?interval=1m"
            f"&symbol={symbol}{end_time_str}{startime_str}"
        )

    response = requests.request("GET", url, headers={}, data={})
    data = {}
    if response.status_code == 200:
        data = json.loads(response.content)
    return data


def get_gaps(coin):
    """
    Runs a query to obtain the gaps in the form of a list of
    (start_time, end_time)
    """
    gaplist = []

    # Identify the "current timestamp - data start" gap
    query_job = bq_client.query(
        f"SELECT MAX(open_time) FROM `{PROJECT}.binance_data.minute_{coin.lower()}`"
    )
    for row in query_job.result():
        if row[0] is not None:
            gaplist = [(row[0], round(time.time() // 60) * 60000)]

    # Get all the gaps in the table
    query_job = bq_client.query(
        "SELECT open_time, previous_open_time FROM ("
        f"    SELECT "
        "       open_time, "
        "       LAG(open_time) OVER(ORDER BY open_time) AS previous_open_time"
        "     FROM "
        f"        `{PROJECT}.binance_data.minute_{coin.lower()}` "
        ") WHERE "
        f" open_time - previous_open_time > 60000 AND open_time > {START_TIME}"
        " ORDER BY open_time DESC"
    )
    for row in query_job.result():
        gaplist.append((row["previous_open_time"], row["open_time"]))

    # Check if the data goes back to the start date
    query_job = bq_client.query(
        f"SELECT MIN(open_time) FROM `{PROJECT}.binance_data.minute_{coin.lower()}`"
    )
    for row in query_job.result():
        if row[0] is not None and row[0] > START_TIME:
            gaplist.append((row[0], START_TIME))

    # In case the tables were empty
    if not gaplist:
        gaplist = [(START_TIME, round(time.time() // 60) * 60000)]
    return gaplist


def fill_between(coin, start, end):
    """
    Gather the information from the binance API to fill the table of the
    provided coin between the start and end timestamps.
    """
    keypoints = list(range(start, end, 500 * 60000)) + [end]
    for r_start, r_end in zip(keypoints, keypoints[1:]):
        r_end -= 60000
        data = get_klines(coin + "USDT", start_time=r_start, end_time=r_end)
        if data:
            insert_data(coin, data)


def deduplicate(coin) -> None:
    """
    Call the bigquery stored procedure to deduplicate the data for a specific
    coin
    """
    bq_client.query(f"CALL `{PROJECT}.binance_data.deduplicate_{coin.lower()}`();")


def main():
    """
    Fill each coin's table with the minute information provided by the binance
    API between now and the START_TIME defined in this script.
    """

    with open("coin.lst", "r") as file:
        coin = file.readline()
        while coin:
            coin = coin[:-1]
            print(f"\n\nLoading data for {coin}")
            gaps = get_gaps(coin)
            print(f"Found {len(gaps)} gaps")
            for start, end in gaps:
                fill_between(coin, start, end)
            coin = file.readline()


if __name__ == "__main__":
    main()
