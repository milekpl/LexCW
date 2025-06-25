# Dictionary Writing System Scripts

This directory contains utility scripts for the Dictionary Writing System.

## Available Scripts

### Import LIFT File

Import a LIFT file into the dictionary database.

```
python -m scripts.import_lift path/to/lift_file.lift [path/to/lift_ranges.lift-ranges]
```

### Export LIFT File

Export the dictionary to a LIFT file.

```
python -m scripts.export_lift path/to/output.lift
```

## Environment Variables

These scripts use the following environment variables:

- `BASEX_HOST`: BaseX server hostname (default: localhost)
- `BASEX_PORT`: BaseX server port (default: 1984)
- `BASEX_USERNAME`: BaseX username (default: admin)
- `BASEX_PASSWORD`: BaseX password (default: admin)
- `BASEX_DATABASE`: BaseX database name (default: dictionary)

You can set these variables in a `.env` file in the project root directory.
