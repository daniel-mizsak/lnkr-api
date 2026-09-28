#!/usr/bin/env bash

set -euo pipefail

# Downloads the latest GeoLite2 Country database from MaxMind and atomically places it
# into the "geoip" directory relative to the current working directory.

GEOIP_DATABASE_EDITION="GeoLite2-Country"
GEOIP_DATABASE_DIRECTORY="geoip"
GEOIP_DATABASE_FILE="${GEOIP_DATABASE_DIRECTORY}/${GEOIP_DATABASE_EDITION}.mmdb"
temporary_directory=""

cleanup() {
    local exit_code=$?
    if [[ -n "${temporary_directory}" ]]; then
        rm -rf "${temporary_directory}"
    fi
    echo "GeoIP database update finished with exit code ${exit_code} at $(date -u +%Y-%m-%dT%H:%M:%S) UTC"
}
trap cleanup EXIT

echo "GeoIP database update started at $(date -u +%Y-%m-%dT%H:%M:%S) UTC"
if [[ -n "${GEOIP_CREDENTIALS:-}" ]]; then
    if [[ ! -f "${GEOIP_CREDENTIALS}" ]]; then
        echo "Error: GEOIP_CREDENTIALS is set to '${GEOIP_CREDENTIALS}', but that file does not exist." >&2
        exit 1
    fi

    echo "Loading GeoIP credentials from '${GEOIP_CREDENTIALS}'."
    # shellcheck disable=SC1090 # can't follow non-constant
    source "${GEOIP_CREDENTIALS}"
fi

if [[ -z "${GEOIP_ACCOUNT_ID:-}" ]]; then
    echo "Error: GEOIP_ACCOUNT_ID is not set." >&2
    exit 1
fi
if [[ -z "${GEOIP_LICENSE_KEY:-}" ]]; then
    echo "Error: GEOIP_LICENSE_KEY is not set." >&2
    exit 1
fi

mkdir -p "${GEOIP_DATABASE_DIRECTORY}"
temporary_directory="$(mktemp --directory "${GEOIP_DATABASE_DIRECTORY}/.update.XXXXXX")"

curl --fail --silent --show-error --location \
    --connect-timeout 10 --max-time 300 \
    --retry 3 --retry-delay 5 --retry-connrefused --retry-max-time 60 \
    --user "${GEOIP_ACCOUNT_ID}:${GEOIP_LICENSE_KEY}" \
    "https://download.maxmind.com/geoip/databases/${GEOIP_DATABASE_EDITION}/download?suffix=tar.gz" |
    tar --extract --gzip --strip-components=1 --directory "${temporary_directory}"

mv "${temporary_directory}/${GEOIP_DATABASE_EDITION}.mmdb" "${GEOIP_DATABASE_FILE}"
echo "Updated ${GEOIP_DATABASE_FILE}"
