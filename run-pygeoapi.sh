#!/usr/bin/env bash
pygeoapi openapi generate pygeoapi.yml --output-file openapi.yml
export PYGEOAPI_CONFIG=$(pwd)/pygeoapi.yml
export PYGEOAPI_OPENAPI=$(pwd)/openapi.yml
pygeoapi serve
