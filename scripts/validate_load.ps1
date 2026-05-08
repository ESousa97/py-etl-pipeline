param(
  [string]$DatabaseUrl = ""
)

if ($DatabaseUrl -ne "") {
  $env:DATABASE_URL = $DatabaseUrl
}

python scripts/validate_load.py

