"""
BinanceBot Class module
"""
import json
import hashlib
import time
import hmac
import concurrent.futures
from collections import deque

import requests
from google.cloud import bigquery
from google.cloud import secretmanager


class BinanceBot:
    """
    Class containing the bot making the calls to the Binance and GCP APIs to
    send purchase or sale orders on the different coins specified in the
    parameter file.
    """

    def __init__(self, parameter_file):
        self.load_parameters(parameter_file)
        self.get_asset_settings()
        self.bq_client = bigquery.Client(project=self.project)
        self.sm_client = secretmanager.SecretManagerServiceClient()
        self.data_hist = {coin: deque(maxlen=1441) for coin in self.coin_list}
        self.thresholds = {}
        self.secret = {}
        self.estimations = {}
        self.asset_quantities = {}
        self.current_open_trade = None

    def get_asset_settings(self):
        """Load the settings of the binance API for the traded assets"""
        self.asset_params = {}
        for coin in self.coin_list:
            symbol = coin + "USDT"
            response = requests.get(
                f"https://api.binance.com/api/v3/exchangeInfo?symbol={symbol}"
            )
            for binance_filter in response.json()["symbols"][0]["filters"]:
                if binance_filter["filterType"] == "LOT_SIZE":
                    self.asset_params[symbol] = {
                        "minQty": float(binance_filter["minQty"]),
                        "maxQty": float(binance_filter["maxQty"]),
                        "stepSize": float(binance_filter["stepSize"]),
                    }
                    break

    def load_parameters(self, parameter_file):
        """Load the parameter file"""
        with open(parameter_file, "r") as file:
            data = json.load(file)
        self.project = data["project"]
        self.coin_list = data["coin_list"]
        self.indexes = data["indexes"]
        self.take_profit = data["take_profit"]
        self.stop_loss = data["stop_loss"]
        self.max_trade_duration_seconds = data["max_trade_duration_seconds"]
        self.thresholds_validity_seconds = data["thresholds_validity_seconds"]
        self.secrets_validity_seconds = data["secrets_validity_seconds"]

    def create_buy_order(self, symbol, usd_amount):
        """Create a Binance buy order at the current market price"""
        usd_amount = int(usd_amount)
        print(usd_amount, symbol)
        params = {
            "symbol": symbol,
            "quoteOrderQty": usd_amount,
            "type": "MARKET",
            "side": "BUY",
            "timestamp": round(time.time() * 1000),
        }
        query_str = "&".join(f"{key}={value}" for key, value in params.items())
        signature = hmac.new(
            self.secret["api_private_key"].encode("utf-8"),
            query_str.encode("utf-8"),
            hashlib.sha256,
        )
        params["signature"] = signature.hexdigest()
        response = requests.post(
            "https://api.binance.com/api/v3/order",
            headers={"X-MBX-APIKEY": self.secret["api_key"]},
            params=params,
        )
        return response

    def create_sell_order(self, symbol, coin_amount):
        """Create a Binance sell order at the current market price"""
        coin_amount = (
            float(coin_amount) // self.asset_params[symbol]["stepSize"]
        ) * self.asset_params[symbol]["stepSize"]
        coin_amount = max(self.asset_params[symbol]["minQty"], coin_amount)
        coin_amount = min(self.asset_params[symbol]["maxQty"], coin_amount)
        params = {
            "symbol": symbol,
            "quantity": format(coin_amount, "f"),
            "type": "MARKET",
            "side": "SELL",
            "timestamp": round(time.time() * 1000),
        }
        query_str = "&".join(f"{key}={value}" for key, value in params.items())
        signature = hmac.new(
            self.secret["api_private_key"].encode("utf-8"),
            query_str.encode("utf-8"),
            hashlib.sha256,
        )
        params["signature"] = signature.hexdigest()
        response = requests.post(
            "https://api.binance.com/api/v3/order",
            headers={"X-MBX-APIKEY": self.secret["api_key"]},
            params=params,
        )
        return response

    def update_asset_quantities(self):
        """Get current available liquidity in the Binance account"""
        timestamp = round(time.time() * 1000)
        query_str = f"timestamp={timestamp}"
        signature = hmac.new(
            self.secret["api_private_key"].encode("utf-8"),
            query_str.encode("utf-8"),
            hashlib.sha256,
        )
        response = requests.get(
            "https://api.binance.com/api/v3/account",
            headers={"X-MBX-APIKEY": self.secret["api_key"]},
            params={"timestamp": timestamp, "signature": signature.hexdigest()},
        )
        if response.status_code == 200:
            for bal in response.json()["balances"]:
                self.asset_quantities[bal["asset"]] = float(bal["free"])

    def update_open_trade(self):
        """Get the open trade if it exists"""
        query_job = self.bq_client.query(
            "SELECT"
            "  * "
            "FROM"
            f"  `{self.project}.trades.trades` "
            "WHERE"
            "  still_open "
            "LIMIT 1"
        )
        rows = query_job.result()
        for row in rows:
            self.current_open_trade = row
            return
        self.current_open_trade = None

    def open_trade(self, symbol, current_price, target, stop_loss):
        """Open a trade and log the information in BigQuery"""
        response = self.create_buy_order(symbol, self.asset_quantities["USDT"])
        quantity = self.asset_quantities["USDT"] / current_price
        if response.status_code == 200:
            self.bq_client.query(
                f"INSERT INTO `{self.project}.trades.trades` VALUES "
                "(CURRENT_TIMESTAMP(),"
                f" '{symbol}',"
                f" {current_price},"
                f" {target},"
                f" {stop_loss},"
                " NULL,"
                f" {quantity},"
                " TRUE,"
                " NULL,"
                " NULL,"
                " NULL)"
            )
        else:
            raise Exception(f"Error while opening a trade in Binance {response.content}")

    def close_trade(self, coin, trade_timestamp, sale_price, profit):
        """Close a trade and log the information in BigQuery"""
        response = self.create_sell_order(coin + "USDT", self.asset_quantities[coin])
        if response.status_code == 200:
            self.bq_client.query(
                f"UPDATE `{self.project}.trades.trades` "
                " SET "
                "  still_open = false,"
                f"  sale_price = {sale_price},"
                "  close_time = CURRENT_TIMESTAMP(),"
                f"  profit = {profit} "
                "WHERE"
                f"  ingestion_time = '{trade_timestamp}'"
            )
        else:
            raise Exception(f"Error while closing a trade in Binance {response.content}")

    def update_full_history(self, coin: str):
        """
        Get the close price of the last 1440 minutes (one day) for the
        specified coin
        """
        symbol = coin + "USDT"
        url = (
            "https://api.binance.com/api/v3/klines?interval=1m&limit=720"
            f"&symbol={symbol}"
        )
        first_batch = requests.get(url, headers={}, data={}).json()
        url = (
            "https://api.binance.com/api/v3/klines?interval=1m&limit=721"
            f"&endTime={min(x[0] for x in first_batch)}"
            f"&symbol={symbol}"
        )
        second_batch = requests.get(url, headers={}, data={}).json()
        self.data_hist[coin] = [float(x[4]) for x in second_batch + first_batch]
        self.update_estimation(coin)

    def update_latest_price(self, coin: str):
        """
        Get the latest price from the Binance ticker and updates the history
        """
        try:
            symbol = coin + "USDT"
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            data = requests.get(url, headers={}, data={}).json()
            self.data_hist[coin].append(float(data["price"]))
            self.update_estimation(coin)
        except Exception as exception:
            raise SystemExit(exception) from exception

    def update_estimation(self, coin: str):
        """
        Update the prediction for the specified coin using the model managed
        on BiqQuery
        """
        lc_coin = coin.lower()
        averaged = [x * 1441 / sum(self.data_hist[coin]) for x in self.data_hist[coin]]
        query = (
            "SELECT predicted_win_in_hour_probs[OFFSET(0)].prob AS prob "
            "FROM "
            "ML.PREDICT("
            f"MODEL `{self.project}.models.bt_{lc_coin}`,"
            "(SELECT "
            + ",".join(
                [
                    f"{averaged[index]} AS value_{lc_coin}_{index}"
                    for index in self.indexes
                ]
            )
            + ")"
            ")"
        )
        query_job = self.bq_client.query(query)
        for row in query_job.result():
            self.estimations[coin] = float(row["prob"])
            print(f'{coin} , {float(row["prob"])}')

    def update_thresholds(self):
        """Update the thresholds used by the bot"""
        print("Updating thresholds")
        query_job = self.bq_client.query(
            f"SELECT * FROM `{self.project}.models.thresholds` "
            f"ORDER BY ingestion_timestamp DESC LIMIT {len(self.coin_list)}"
        )
        rows = query_job.result()
        self.thresholds["timestamp"] = time.time()
        for row in rows:
            self.thresholds[row["coin"].upper()] = float(row["threshold"])
        print(self.thresholds)

    def update_secrets(self):
        """Update the secrets used by the bot"""
        print("Updating secrets")
        response = self.sm_client.access_secret_version(
            {"name": f"projects/{self.project}/secrets/secret-binance/versions/latest"}
        )
        self.secret["api_key"] = response.payload.data.decode("UTF-8")
        response = self.sm_client.access_secret_version(
            {
                "name": f"projects/{self.project}/secrets/secret-binance-private/versions/latest"
            }
        )
        self.secret["api_private_key"] = response.payload.data.decode("UTF-8")
        self.secret["timestamp"] = time.time()

    def update_information(self):
        """
        Parallelize the requests to the different APIs providing information
        needed to make a decision.
        """
        res = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            res.append(executor.submit(self.update_open_trade))
            if (
                not self.thresholds
                or time.time() - self.thresholds["timestamp"]
                > self.thresholds_validity_seconds
            ):
                res.append(executor.submit(self.update_thresholds))
            if (
                not self.secret
                or time.time() - self.secret["timestamp"]
                > self.secrets_validity_seconds
            ):
                res.append(executor.submit(self.update_secrets))
            res.append(executor.submit(self.update_asset_quantities))
            for coin in self.coin_list:
                if len(self.data_hist[coin]) < 1441:
                    res.append(executor.submit(self.update_full_history, coin))
                else:
                    res.append(executor.submit(self.update_latest_price, coin))
            concurrent.futures.wait(res)

    def decide(self):
        """
        Once all information is loaded, choose wether to sell the current
        position, keep it, or open one if none already is.
        """
        if self.current_open_trade:
            print("Trade already open", self.current_open_trade)
            coin = self.current_open_trade["pair"][:-4]
            if (
                self.data_hist[coin][-1]
                >= float(self.current_open_trade["target_price"])
                or self.data_hist[coin][-1]
                <= float(self.current_open_trade["stop_loss_price"])
                or self.current_open_trade["ingestion_time"].timestamp()
                < time.time() - self.max_trade_duration_seconds
            ):
                trade_result = (
                    self.data_hist[coin][-1]
                    - float(self.current_open_trade["purchase_price"])
                ) * float(self.current_open_trade["quantity"])
                print("Closing trade; restult: ", trade_result)
                self.close_trade(
                    coin,
                    self.current_open_trade["ingestion_time"],
                    self.data_hist[coin][-1],
                    trade_result,
                )
                self.update_asset_quantities()
        else:
            coin_signals = [
                (coin, self.estimations[coin] - self.thresholds[coin])
                for coin in self.coin_list
                if self.estimations[coin] >= self.thresholds[coin]
            ]
            if coin_signals:
                coin = max(coin_signals, key=lambda x: x[1])[0]
                print(f"Coin Signal for  {coin}")
                if self.asset_quantities["USDT"] > 10:
                    self.open_trade(
                        symbol=coin+"USDT",
                        current_price=self.data_hist[coin][-1],
                        target=self.data_hist[coin][-1] * self.take_profit,
                        stop_loss=self.data_hist[coin][-1] * self.stop_loss,
                    )
                    self.update_asset_quantities()
                else:
                    print("Not enought funds in the Binance account")

