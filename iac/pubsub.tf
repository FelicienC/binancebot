resource "google_pubsub_topic" "load_data" {
  name = "load_data"
}

resource "google_pubsub_topic" "binance-tradingbot-trigger" {
  name = "binance-tradingbot-trigger"
}