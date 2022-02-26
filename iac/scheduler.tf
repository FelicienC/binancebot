resource "google_cloud_scheduler_job" "load_data_job" {
  name        = "load_data"
  description = "Load binance data in bigquery"
  schedule    = "0 12 * * *"
  region      = "europe-west1"

  pubsub_target {
    topic_name = google_pubsub_topic.load_data.id
    data       = base64encode("{}")
  }
}

resource "google_cloud_scheduler_job" "trigger_trading_bot" {
  name        = "trading-bot"
  description = "trigger bot to make predictions"
  schedule    = "* * * * *"
  region      = "europe-west1"

  pubsub_target {
    topic_name = google_pubsub_topic.binance-tradingbot-trigger.id
    data       = base64encode("{}")
  }
}