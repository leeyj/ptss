import paramiko


def test_manual_connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        print("Connecting to 192.168.0.20 as az001...")
        client.connect(
            "192.168.0.20", port=22, username="az001", password="***REMOVED***"
        )
        print("✅ Connection Success!")
        client.close()
    except Exception as e:
        print(f"❌ Connection Failed: {e}")


if __name__ == "__main__":
    test_manual_connect()
