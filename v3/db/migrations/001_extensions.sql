-- Derived from docs/v3/SCHEMA.sql. Idempotent.
-- CREATE ... IF NOT EXISTS does not change an object that already exists.
-- A later schema change is a new numbered file, not an edit to this one.

create extension if not exists postgis;

create extension if not exists pg_trgm;      -- fuzzy name search (institution + geo filters)

create extension if not exists unaccent;

create schema if not exists usd;

set search_path = usd, public;
