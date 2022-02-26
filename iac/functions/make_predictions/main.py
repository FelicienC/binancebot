"""
This cloud functions uses the warm start acceleration of google cloud functions
to keep in memory the price history of all coins of the last 24 hours and the
thresholds used by the models.
"""
from binancebot import BinanceBot

binance_bot = BinanceBot(parameter_file="parameters.json")


def main(event, context):
    """
    Triggered from a message on a Cloud Pub/Sub topic.
    Buy if not holding a position already, and sell when the limits are reached
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    del event, context
    binance_bot.update_information()
    binance_bot.decide()
