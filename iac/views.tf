locals {
  tpl_views_1         = fileset("./${path.module}", "views/build/*.yaml")
  confs_view_1     = { for file in local.tpl_views_1 : file => yamldecode(templatefile("./${path.module}/${file}", { location = "eu", "project" = var.project })) }

}

resource "google_bigquery_table" "views_level_1" {
  for_each = local.confs_view_1

  dataset_id          = each.value.dataset_id
  table_id            = each.value.view_id

  view {
    query          = each.value.query
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.tables]

}
