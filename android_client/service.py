"""
Background service stub for Android (Buildozer/p4a service entrypoint).
This keeps room for future always-on behaviors (heartbeat, notifications, etc.).
"""
import time


def run_service_loop():
    while True:
        # Reserved for future background logic.
        time.sleep(30)


if __name__ == "__main__":
    run_service_loop()
