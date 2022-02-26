resource "google_storage_bucket" "cloud_functions_bucket" {
 name                        = format("%s-%s", var.project ,"cloud-functions-bucket")
 location                    = "EU"
 uniform_bucket_level_access = true
 provider                    = google-beta
}

data "archive_file" "load_data_zip" {
 type        = "zip"
 source_dir  = "${path.root}/functions/build/load_data/"
 output_path = "${path.root}/functions/build/load_data.zip"
}

resource "google_storage_bucket_object" "function_zip" {
 name   = format("%s-%s.zip", "load_data", data.archive_file.load_data_zip.output_md5)
 bucket = "${google_storage_bucket.cloud_functions_bucket.name}"
 source = "${path.root}/functions/build/load_data.zip"
}

resource "google_cloudfunctions_function" "load_data_function" {
 name                  = "load_data"
 description           = "Scheduled load data Function"
 available_memory_mb   = 128
 source_archive_bucket = "${google_storage_bucket.cloud_functions_bucket.name}"
 source_archive_object = "${google_storage_bucket_object.function_zip.name}"
 timeout               = 60
 entry_point           = "main"
 max_instances         = 1
 runtime               = "python38"
 region                = "europe-west3"

 event_trigger  {
        event_type = "providers/cloud.pubsub/eventTypes/topic.publish"
        resource = "${google_pubsub_topic.load_data.name}"
 }
}

data "archive_file" "make_predictions_function_zip" {
 type        = "zip"
 source_dir  = "${path.root}/functions/build/make_predictions/"
 output_path = "${path.root}/functions/build/make_predictions.zip"
 excludes    = [ 
   "${path.root}/functions/build/make_predictions/test_data",
   "${path.root}/functions/build/make_predictions/*_test.py" 
  ]

}

resource "google_storage_bucket_object" "make_predictions_function_zip" {
 name   = format("%s-%s.zip", "make_predictions", data.archive_file.make_predictions_function_zip.output_md5)
 bucket = "${google_storage_bucket.cloud_functions_bucket.name}"
 source = "${path.root}/functions/build/make_predictions.zip"
}

resource "google_cloudfunctions_function" "make_predictions_function" {
 name                  = "make_predictions"
 description           = "Scheduled load data Function"
 available_memory_mb   = 256
 source_archive_bucket = "${google_storage_bucket.cloud_functions_bucket.name}"
 source_archive_object = "${google_storage_bucket_object.make_predictions_function_zip.name}"
 timeout               = 60
 entry_point           = "main"
 max_instances         = 1
 runtime               = "python38"
 region                = "europe-west3"

 event_trigger  {
        event_type = "providers/cloud.pubsub/eventTypes/topic.publish"
        resource = "${google_pubsub_topic.binance-tradingbot-trigger.name}"
 }
}

resource "google_secret_manager_secret_iam_binding" "binding" {
  provider = google-beta
  project = var.project
  secret_id = google_secret_manager_secret.default.secret_id
  role = "roles/secretmanager.secretAccessor"
  members = [
    "serviceAccount:${var.project}@appspot.gserviceaccount.com"
  ]
}

resource "google_secret_manager_secret_iam_binding" "binding-private" {
  provider = google-beta
  project = var.project
  secret_id = google_secret_manager_secret.secret-binance-private.secret_id
  role = "roles/secretmanager.secretAccessor"
  members = [
    "serviceAccount:${var.project}@appspot.gserviceaccount.com"
  ]
}