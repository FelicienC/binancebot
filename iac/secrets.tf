resource "google_secret_manager_secret" "default" {
  provider = google-beta
  secret_id = "secret-binance"
  replication {
    automatic = true
  }

}

resource "google_secret_manager_secret" "secret-binance-private" {
  provider = google-beta
  secret_id = "secret-binance-private"
  replication {
    automatic = true
  }

}