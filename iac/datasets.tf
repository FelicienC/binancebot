locals {
  tpl_datasets     = fileset("./${path.module}", "datasets/*.json")
  confs_dataset    = { for file in local.tpl_datasets : file => jsondecode(templatefile("./${path.module}/${file}", {location = "europe-west1" })) }
}

resource "google_bigquery_dataset" "datasets" {

  for_each                    = local.confs_dataset

  provider                    = google-beta
  project                     = var.project
  dataset_id                  = each.value.dataset_id
  friendly_name               = each.value.friendly_name
  description                 = each.value.description
  location                    = upper(each.value.location)
  default_table_expiration_ms = each.value.default_table_expiration_ms

  delete_contents_on_destroy = each.value.delete_contents_on_destroy
}
