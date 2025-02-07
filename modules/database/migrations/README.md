# Migrations
Here the migrations are stored that make up the structure of the database
Migrations are not to be altered once created and should not be deleted.

If something needs to be changed, added, or reverted, create a new valid migration adhering to the naming convention.

## Migrations Naming Convention
Migrations should follow the naming convention: `YYYYMMDDHHMMSS_PURPOSE.(UP|DOWN).sql`, where `UP` is used when adding something new, and `DOWN` is used when reversing changes.
