# =========================
# APP LOGIN CREDENTIALS
# =========================
[credentials]
username = "adminsst"   # Replace with your app login username
password = "isst@2025"   # Replace with your app login password

# =========================
# GOOGLE SERVICE ACCOUNT
# =========================
[google]
type = "service_account"
project_id = "groc-purchase-and-deliveryapp"  # Replace with your Google Cloud project ID
private_key_id = "f96135e39b56498527e6ac630bcd960a17e94771"         # Replace with your private key ID
private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkq...\n-----END PRIVATE KEY-----\n"  # Single-line with \n
client_email = "campusgroceryapp@groc-purchase-and-deliveryapp.iam.gserviceaccount.com"  # Replace with your service account email
client_id = "114261537315232932947"                                # Replace with your client ID
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/xxxx"  # Replace accordingly
