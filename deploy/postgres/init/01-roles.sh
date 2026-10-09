#!/bin/sh
# Runs once, on first start of an empty data directory (docker-entrypoint-initdb.d).
#
# Roles (threat model T1):
#   referral_owner  owns the schema; used only by migrations (MIGRATION_DATABASE_URL)
#   referral_app    DML only; used by API and workers (DATABASE_URL). Cannot ALTER tables or
#                   DISABLE TRIGGER, so insert-only triggers (I2) cannot be bypassed by the app.
# Databases: referral (application), referral_test (integration tests).
set -eu

: "${REFERRAL_OWNER_PASSWORD:?set REFERRAL_OWNER_PASSWORD}"
: "${REFERRAL_APP_PASSWORD:?set REFERRAL_APP_PASSWORD}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
  -v owner_pw="$REFERRAL_OWNER_PASSWORD" -v app_pw="$REFERRAL_APP_PASSWORD" <<'SQL'
CREATE ROLE referral_owner LOGIN PASSWORD :'owner_pw';
CREATE ROLE referral_app LOGIN PASSWORD :'app_pw';
CREATE DATABASE referral OWNER referral_owner;
CREATE DATABASE referral_test OWNER referral_owner;
SQL

for db in referral referral_test; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" -v db="$db" <<'SQL'
REVOKE ALL ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO referral_owner;
GRANT USAGE ON SCHEMA public TO referral_app;
REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE :"db" TO referral_app;
SQL
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" <<'SQL'
ALTER DEFAULT PRIVILEGES FOR ROLE referral_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO referral_app;
ALTER DEFAULT PRIVILEGES FOR ROLE referral_owner IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO referral_app;
ALTER DEFAULT PRIVILEGES FOR ROLE referral_owner IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO referral_app;
SQL
done
