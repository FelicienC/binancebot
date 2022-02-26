locals {
  tpl_procedures   = fileset("./${path.module}", "procedures/build/*.yaml")
  confs_procedures = { for file in local.tpl_procedures : file => yamldecode(templatefile("./${path.module}/${file}", {location = "europe-west1", project = var.project})) }

}

resource "google_bigquery_job" "procedures" {

  for_each = local.confs_procedures

  provider = google-beta
  job_id   = "${each.value.procedure_id}"
  location = "europe-west1"

  query {
    query              = each.value.body
    create_disposition = ""
    write_disposition  = ""
  }

}
