locals {
  tpl_tables         = fileset("./${path.module}", "tables/build/*.json")
  confs_tmp_tables = { for file in local.tpl_tables : file => jsondecode(templatefile("./${path.module}/${file}", {location = "eu", "project"  = var.project})) }
  confs_tables      = { for k, v in local.confs_tmp_tables : k => merge(v, { schema = jsonencode(v["schema"]) }) }

}

# ======================================================================
# GCP BIG QUERY TABLES
# ======================================================================

resource "google_bigquery_table" "tables" {

  for_each = local.confs_tables

  project             = var.project
  dataset_id          = each.value.dataset_id
  table_id            = each.value.table_id
  schema              = each.value.schema
  clustering          = each.value.clustering
  description         = each.value.description


  dynamic "time_partitioning" {
    for_each = each.value.time_partitioning != null ? [each.value.time_partitioning] : []
    content {
      type                     = each.value.time_partitioning.type
      field                    = each.value.time_partitioning.field
      require_partition_filter = each.value.time_partitioning.require_partition_filter
    }
  }

  dynamic "external_data_configuration" {
    for_each = each.value.gsheet_data_configuration != null ? [each.value.gsheet_data_configuration] : []
    content {
      autodetect    = each.value.gsheet_data_configuration.autodetect
      ignore_unknown_values = each.value.gsheet_data_configuration.ignore_unknown_values
      source_format = "GOOGLE_SHEETS"

      google_sheets_options {
        range = each.value.gsheet_data_configuration.range
        skip_leading_rows = each.value.gsheet_data_configuration.skip_leading_rows
      }

      source_uris = [
        lookup(each.value.gsheet_data_configuration.source_uris, var.project_env, lookup(each.value.gsheet_data_configuration.source_uris, "sbx", null))
      ]
    }
  }

  depends_on = [google_bigquery_dataset.datasets]
}