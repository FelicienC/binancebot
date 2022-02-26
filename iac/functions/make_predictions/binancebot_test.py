import unittest
from unittest import mock

import json
import hmac
import hashlib
import time
import datetime
import requests

from binancebot import BinanceBot


class MockBiqueryQuery:
    def __init__(self, rows) -> None:
        self.rows = rows

    def result(self):
        return self.rows

class MockResponse:
    def __init__(self, file_name, status_code):
        with open(file_name, "r") as file:
            self.json_data = json.load(file)
        self.status_code = status_code
        self.content = self.json_data

    def json(self):
        return self.json_data


def mocked_binance_public(*args, **kwargs):
    if args[0][:38] == "https://api.binance.com/api/v3/ticker/":
        return MockResponse("test_data/ticker.json", 200)
    if args[0][:37] == "https://api.binance.com/api/v3/klines":
        return MockResponse("test_data/full_history.json", 200)
    if args[0][:43] == "https://api.binance.com/api/v3/exchangeInfo":
        return MockResponse("test_data/exchangeInfo.json", 200)


def mocked_binance_signed(*args, **kwargs):
    if args[0] in ("https://api.binance.com/api/v3/order", "https://api.binance.com/api/v3/account"):
        if "X-MBX-APIKEY" in kwargs["headers"].keys():
            if kwargs["headers"]["X-MBX-APIKEY"] == "trululu":
                params = kwargs["params"]
                query_string = "&".join(
                    f"{key}={value}"
                    for key, value in params.items()
                    if key != "signature"
                )
                signature = hmac.new(
                    "tralala".encode("utf-8"),
                    query_string.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                if signature == params["signature"]:
                    if args[0] == "https://api.binance.com/api/v3/order":
                        return MockResponse("test_data/success_order.json", 200)
                    if args[0] == "https://api.binance.com/api/v3/account":
                        return MockResponse("test_data/account_balances.json", 200)
                return MockResponse("test_data/signature_error.json", 401)
            return MockResponse("test_data/wrong_api_key.json", 401)


class TestCases(unittest.TestCase):
    def __init__(self, methodName: str = ...) -> None:
        super().__init__(methodName)
        self.reset_bot()

    @mock.patch("requests.get", side_effect=mocked_binance_public)
    def reset_bot(self, mock_get):
        self.bot = BinanceBot("parameters.json")

    @mock.patch("requests.get", side_effect=mocked_binance_public)
    def test_get_asset_settings(self, mock_get):
        self.bot.get_asset_settings()
        self.assertEqual(
            self.bot.asset_params["BTCUSDT"],
            {"minQty": 1e-5, "maxQty": 9e3, "stepSize": 1e-5},
        )

    def test_load_parameters(self):
        self.reset_bot()
        with open("parameters.json", "r") as file:
            data = json.load(file)
        self.assertEqual(self.bot.project, data["project"])
        self.assertEqual(self.bot.coin_list, data["coin_list"])
        self.assertEqual(self.bot.indexes, data["indexes"])
        self.assertEqual(self.bot.take_profit, data["take_profit"])
        self.assertEqual(self.bot.stop_loss, data["stop_loss"])
        self.assertEqual(
            self.bot.max_trade_duration_seconds, data["max_trade_duration_seconds"]
        )
        self.assertEqual(
            self.bot.thresholds_validity_seconds, data["thresholds_validity_seconds"]
        )
        self.assertEqual(
            self.bot.secrets_validity_seconds, data["secrets_validity_seconds"]
        )

    @mock.patch("requests.post", side_effect=mocked_binance_signed)
    def test_create_buy_order(self, mock_post):
        self.bot.secret = {
            "api_private_key": "tralala",
            "api_key": "trululu",
        }
        response = self.bot.create_buy_order("BTCUSDT", 10)
        self.assertEqual(response.status_code, 200)
        self.bot.secret = {
            "api_private_key": "oupsi",
            "api_key": "trululu",
        }
        response = self.bot.create_buy_order("BTCUSDT", 10)
        self.assertEqual(response.status_code, 401)
        self.bot.secret = {
            "api_private_key": "oupsi",
            "api_key": "wrong_api_key",
        }
        response = self.bot.create_buy_order("BTCUSDT", 10)
        self.assertEqual(response.status_code, 401)

    @mock.patch("requests.post", side_effect=mocked_binance_signed)
    def test_create_sell_order(self, mock_post):
        self.bot.secret = {
            "api_private_key": "tralala",
            "api_key": "trululu",
        }
        response = self.bot.create_sell_order("BTCUSDT", 10)
        self.assertEqual(response.status_code, 200)

    @mock.patch("requests.get", side_effect=mocked_binance_signed)
    def test_update_asset_quantities(self, mock_get):
        self.bot.secret = {
            "api_private_key": "tralala",
            "api_key": "trululu",
        }
        self.bot.update_asset_quantities()
        self.assertEqual(200, 200)

    def test_update_open_trade(self):
        self.bot.bq_client.query = mock.Mock(return_value=MockBiqueryQuery([]))
        self.bot.update_open_trade()
        self.assertEqual(self.bot.current_open_trade, None)
        open_trade_dict =  {
            "pair": "BTCUSDT",
            "target_price": 1010,
            "stop_loss_price": 980,
            "ingestion_time": datetime.datetime.now(),
            "purchase_price": 1000,
            "quantity": 1
            }
        self.bot.bq_client.query = mock.Mock(return_value=MockBiqueryQuery([
            open_trade_dict
        ]))
        self.bot.update_open_trade()
        self.assertEqual(self.bot.current_open_trade, open_trade_dict)

    def test_open_trade(self):
        self.bot.asset_quantities["USDT"] = 100
        self.bot.create_buy_order = mock.Mock(
            return_value=MockResponse("test_data/success_order.json", 200)
        )
        self.bot.bq_client.query = mock.Mock(return_value=MockBiqueryQuery([]))
        self.bot.open_trade("BTCUSDT", 10, 11, 9)

        self.bot.bq_client.query.assert_called_once()

        self.bot.create_buy_order = mock.Mock(
            return_value=MockResponse("test_data/signature_error.json", 401)
        )
        self.bot.bq_client.query = mock.Mock()
        self.bot.open_trade("BTCUSDT", 10, 11, 9)
        self.bot.bq_client.query.assert_not_called()


    def test_close_trade(self):
        self.bot.asset_quantities["BTC"] = 1
        self.bot.create_sell_order = mock.Mock(
            return_value=MockResponse("test_data/success_order.json", 200)
        )
        self.bot.bq_client.query = mock.Mock(return_value=MockBiqueryQuery([]))
        self.bot.close_trade("BTC", 123, 12, 1)
        self.bot.bq_client.query.assert_called_once()

        self.bot.create_sell_order = mock.Mock(
            return_value=MockResponse("test_data/signature_error.json", 401)
        )
        self.bot.bq_client.query = mock.Mock()
        self.bot.close_trade("BTC", 123, 12, 1)
        self.bot.bq_client.query.assert_not_called()

    @mock.patch("requests.get", side_effect=mocked_binance_public)
    def test_update_full_history(self, mock_get):
        coin = "BTC"
        self.bot.update_estimation = mock.Mock()
        self.bot.update_full_history(coin)
        self.assertEqual(self.bot.data_hist[coin][-1], 44057.45)

    @mock.patch("requests.get", side_effect=mocked_binance_public)
    def test_update_latest_price(self, mock_get):
        coin = "BTC"
        self.bot.update_estimation = mock.Mock()
        self.bot.update_latest_price(coin)
        self.assertEqual(self.bot.data_hist[coin][-1], 42069)

    @mock.patch("requests.get", side_effect=requests.exceptions.ConnectionError())
    def test_update_latest_price_error(self, mock_get):
        self.bot.update_estimation = mock.Mock()
        with self.assertRaises(SystemExit):
            self.bot.update_latest_price("BTC")

    def test_update_estimation(self):
        self.reset_bot()
        self.bot.bq_client.query = mock.Mock(
            return_value=MockBiqueryQuery([{"prob": 0.8}])
        )
        self.bot.data_hist["BTC"] = range(1441)
        self.bot.update_estimation("BTC")
        self.assertEqual(self.bot.estimations["BTC"], 0.8)

    def test_update_thresholds(self):
        self.reset_bot()
        self.bot.bq_client.query = mock.Mock(
            return_value=MockBiqueryQuery(
                [
                    {"coin": "BTC", "threshold": "0.9"},
                    {"coin": "ETH", "threshold": "0.8"},
                ]
            )
        )
        self.bot.update_thresholds()
        self.assertEqual(self.bot.thresholds["BTC"], 0.9)
        self.assertEqual(self.bot.thresholds["ETH"], 0.8)

    def test_update_secrets(self):
        self.reset_bot()
        returner = mock.MagicMock()
        returner.payload.data.decode = mock.Mock(return_value="ha")
        self.bot.sm_client.access_secret_version = mock.Mock(return_value=returner)
        self.bot.update_secrets()
        self.assertEqual(self.bot.secret["api_private_key"], "ha")
        self.assertEqual(self.bot.secret["api_key"], "ha")

    def test_update_information(self):
        # Without history
        self.reset_bot()

        self.bot.update_open_trade = mock.Mock()
        self.bot.update_thresholds = mock.Mock()
        self.bot.update_secrets = mock.Mock()
        self.bot.update_asset_quantities = mock.Mock()
        self.bot.update_full_history = mock.Mock()

        self.bot.update_information()

        self.bot.update_open_trade.assert_called_once()
        self.bot.update_thresholds.assert_called_once()
        self.bot.update_secrets.assert_called_once()
        self.bot.update_asset_quantities.assert_called_once()
        self.bot.update_full_history.assert_any_call("BTC")
        self.bot.update_full_history.assert_any_call("ETH")
        self.bot.update_full_history.assert_any_call("SOL")

        # With existing history, secrets and thresholds
        self.reset_bot()

        self.bot.update_open_trade = mock.Mock()
        self.bot.update_asset_quantities = mock.Mock()
        self.bot.update_latest_price = mock.Mock()
        self.bot.secret = {"timestamp": time.time()}
        self.bot.thresholds = {"timestamp": time.time()}
        for coin in ["BTC", "ETH", "SOL"]:
            self.bot.data_hist[coin] = range(1441)

        self.bot.update_information()

        self.bot.update_open_trade.assert_called_once()
        self.bot.update_asset_quantities.assert_called_once()
        self.bot.update_latest_price.assert_any_call("BTC")
        self.bot.update_latest_price.assert_any_call("ETH")
        self.bot.update_latest_price.assert_any_call("SOL")

    def test_decision_function(self):
        # No open trade, no signal
        self.reset_bot()
        self.bot.current_open_trade = None
        for coin in ["BTC", "ETH", "SOL"]:
            self.bot.estimations[coin] = 0.5
            self.bot.thresholds[coin] = 0.6
        self.bot.open_trade = mock.Mock()

        self.bot.decide()

        self.bot.open_trade.assert_not_called()

        # No open trade, one signal
        self.reset_bot()
        self.bot.current_open_trade = None
        for coin in ["BTC", "ETH"]:
            self.bot.estimations[coin] = 0.5
            self.bot.thresholds[coin] = 0.6
        self.bot.estimations["SOL"] = 0.8
        self.bot.thresholds["SOL"] = 0.6
        self.bot.data_hist["SOL"] = [100]
        self.bot.open_trade = mock.Mock()

        self.bot.decide()

        self.bot.open_trade.assert_called_once_with(
            symbol="SOLUSDT", current_price=100, target=101.0, stop_loss=98.0
        )

        # No open trade, two signals
        self.reset_bot()
        self.bot.current_open_trade = None
        for coin in ["BTC"]:
            self.bot.estimations[coin] = 0.5
            self.bot.thresholds[coin] = 0.6
        self.bot.estimations["SOL"] = 0.8
        self.bot.thresholds["SOL"] = 0.6
        self.bot.data_hist["SOL"] = [100]
        self.bot.estimations["ETH"] = 0.7
        self.bot.thresholds["ETH"] = 0.6
        self.bot.open_trade = mock.Mock()

        self.bot.decide()

        self.bot.open_trade.assert_called_once_with(
            symbol="SOLUSDT", current_price=100, target=101.0, stop_loss=98.0
        )

        # An open trade, nothing to do
        self.reset_bot()
        self.bot.current_open_trade = {
            "pair": "BTCUSDT",
            "target_price": 1010,
            "stop_loss_price": 980,
            "ingestion_time": datetime.datetime.now(),
            "purchase_price": 1000,
            "quantity": 1,
        }
        self.bot.data_hist["BTC"] = [1000]
        self.bot.close_trade = mock.Mock()

        self.bot.decide()

        self.bot.close_trade.assert_not_called()

        # An open trade, reaching target
        self.reset_bot()
        self.bot.current_open_trade = {
            "pair": "BTCUSDT",
            "target_price": 1010,
            "stop_loss_price": 980,
            "ingestion_time": datetime.datetime.now(),
            "purchase_price": 1000,
            "quantity": 1,
        }
        self.bot.data_hist["BTC"] = [1020]
        self.bot.close_trade = mock.Mock()

        self.bot.decide()

        self.bot.close_trade.assert_called_once_with(
            "BTC", self.bot.current_open_trade["ingestion_time"], 1020, 20.0
        )

        # An open trade, reaching stop loss
        self.reset_bot()
        self.bot.current_open_trade = {
            "pair": "BTCUSDT",
            "target_price": 1010,
            "stop_loss_price": 980,
            "ingestion_time": datetime.datetime.now(),
            "purchase_price": 1000,
            "quantity": 1,
        }
        self.bot.data_hist["BTC"] = [970]
        self.bot.close_trade = mock.Mock()

        self.bot.decide()

        self.bot.close_trade.assert_called_once_with(
            "BTC", self.bot.current_open_trade["ingestion_time"], 970, -30.0
        )

        # An open trade, reaching the time limit
        self.reset_bot()
        self.bot.current_open_trade = {
            "pair": "BTCUSDT",
            "target_price": 1010,
            "stop_loss_price": 980,
            "ingestion_time": datetime.datetime.now() - datetime.timedelta(hours=1),
            "purchase_price": 1000,
            "quantity": 1,
        }
        self.bot.data_hist["BTC"] = [1000]
        self.bot.close_trade = mock.Mock()

        self.bot.decide()

        self.bot.close_trade.assert_called_once_with(
            "BTC", self.bot.current_open_trade["ingestion_time"], 1000, 0.0
        )


if __name__ == "__main__":
    unittest.main()
