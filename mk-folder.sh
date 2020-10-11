#!/bin/sh

[ $# -ne 1 ] && { echo "Usage: $0 notebookname" >&2; exit 2; }

foldername="$1"

# try to obtain token from jopleet.config

token="$(awk -F ' = '  '/^token/ { print $2 }' jopleet.config)"

curl -sf http://localhost:41184/folders?token=${token} \
	--data "{ \"title\": \"${foldername}\" }" |
	python -mjson.tool
