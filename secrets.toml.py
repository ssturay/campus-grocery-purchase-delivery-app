# =========================
# APP LOGIN CREDENTIALS
# =========================
[credentials]
username = "your_username"   # Replace with your app login username
password = "your_password"   # Replace with your app login password

# =========================
# GOOGLE SERVICE ACCOUNT
# =========================
[google]
type = "service_account"
project_id = "your_project_id"  # Replace with your Google Cloud project ID
private_key_id = "xxxx"         # Replace with your private key ID
private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkq...\n-----END PRIVATE KEY-----\n"  # Single-line with \n
client_email = "xxxx@xxxx.iam.gserviceaccount.com"  # Replace with your service account email
client_id = "xxxx"                                # Replace with your client ID
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/xxxx"  # Replace accordingly
