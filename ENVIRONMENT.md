This project requires a number of environment variables to be defined.

They are documented here.

#### PYTHONUNBUFFERED=1
This allows for stdout/stderr to be dumped immediately, preventing error messages from being lost in a crash.

#### UPDATE_PASS
This sets the password for the update url (accessed at /update/???).

#### S3_ACCESS_KEY, S3_SECRET_KEY, S3_ENDPOINT
These are needed for storing and fetching data in a persistent fashion.

#### BUCKET
Name of the bucket in S3.

#### PORT
Number of port to serve the site on.

#### FLASK_SECRET_KEY
Used to keep sessions private. Should be a random, secure value.
