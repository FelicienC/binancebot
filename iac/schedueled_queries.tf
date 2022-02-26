locals {
  tpl_queries         = fileset("./${path.module}", "schedueled_queries/build/*.yaml")
  confs_queries     = { for file in local.tpl_queries : file => yamldecode(templatefile("./${path.module}/${file}", { location = "eu", project = var.project })) }

}

resource "google_bigquery_data_transfer_config" "query_config" {

  for_each = local.confs_queries
  
  provider                    = google-beta

  display_name           = each.value.display_name
  location               = "europe-west1"
  data_source_id         = "scheduled_query"
  schedule               = each.value.schedule

  params = {
    query                           = each.value.query
  }
}
