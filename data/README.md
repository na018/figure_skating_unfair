# Data directory

Store immutable source protocols in `raw/`, normalized datasets in `processed/`, and
supporting reference data in `external/`. These directories are ignored by Git so that
large or externally sourced files are not committed accidentally.

For each source document, record at least its competition ID, source URL, retrieval date,
original filename, and a SHA-256 checksum in a source manifest. Never overwrite the
original protocol with parsed or corrected data. Document corrections and retain the
original value alongside any corrected value.
