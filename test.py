import socket
import ssl
import subprocess
import urllib.parse
import shlex

# --------------------------
# Step 1: Verify TLS 1.3 support
# --------------------------
def verify_tls13(host="api.sandbox.africastalking.com", port=443):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_default_certs()

    try:
        with socket.create_connection((host, port)) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                print(f"✅ Connected to {host}:{port}")
                print(f"TLS version in use: {ssock.version()}")
                print(f"Cipher in use: {ssock.cipher()}")
                return True
    except ssl.SSLError as e:
        print(f"❌ SSL error: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

# --------------------------
# Step 2: Send booking SMS using curl
# --------------------------
def send_booking_sms(phone, message, api_key="atsk_0907008d273f5c058da129dd4bc8a6a733dd057c5e7eaa21f118f6c60094845b0748e03a", username="sandbox"):
    if not verify_tls13():
        print("❌ Cannot send SMS: TLS 1.3 not supported.")
        return

    # URL-encode form data
    data = {
        "username": username,
        "to": phone,
        "message": message
    }
    encoded_data = urllib.parse.urlencode(data)

    # Build curl command
    cmd = f'curl -s -X POST https://api.sandbox.africastalking.com/version1/messaging -d "{encoded_data}" -H "apiKey: {api_key}"'

    # Run the command
    result = subprocess.run(shlex.split(cmd), capture_output=True, text=True)

    print("\n📩 SMS API Response:")
    print(result.stdout.strip())
    if result.stderr.strip():
        print("Errors:", result.stderr.strip())

# --------------------------
# Step 3: Example usage
# --------------------------
if __name__ == "__main__":
    send_booking_sms(
        "+27707317823",
        "Yo! Booking confirmed. Test booking 001"
    )