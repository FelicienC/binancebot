terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "3.5.0"
    }
  }
}

provider "google" {
  project = var.project
  region  = "eu-west1"
  zone    = "eu-west1-a"
}

provider "google-beta" {
  project = var.project
  region  = "eu-west1"
  zone    = "eu-west1-a"
}

resource "google_app_engine_application" "app" {
  project     = var.project
  location_id = "europe-west"
}


variable "project" {
  type = string
  default = "trading-dv"
}