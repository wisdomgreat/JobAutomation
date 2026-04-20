"""
Sovereign Agent - Cross-Platform Notifier
Handles native desktop notifications for mission-critical events.
"""

import platform
import os
import sys

def notify(title: str, message: str):
    """
    Sends a native desktop notification.
    Tries multiple backends depending on OS availability.
    """
    system = platform.system()
    print(f"[System] MISSION ALERT: {title} - {message}")

    try:
        if system == "Windows":
            _notify_windows(title, message)
        elif system == "Darwin": # macOS
            _notify_mac(title, message)
        else: # Linux
            _notify_linux(title, message)
    except Exception as e:
        print(f"[Warning] Could not send desktop notification: {e}")

def _notify_windows(title, message):
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        # Path to icon if available
        icon = os.path.join(os.path.dirname(__file__), "..", "image", "favicon.ico")
        if not os.path.exists(icon): icon = None
        
        toaster.show_toast(title, message, icon_path=icon, duration=10, threaded=True)
    except ImportError:
        # Silently fail, we already printed to console in notify()
        pass
    except Exception:
        pass

def _notify_mac(title, message):
    import subprocess
    subprocess.run(["osascript", "-e", f'display notification "{message}" with title "{title}"'])

def _notify_linux(title, message):
    import subprocess
    subprocess.run(["notify-send", title, message])

if __name__ == "__main__":
    # Test
    notify("Sovereign Agent", "Intelligence synchronization successful.")
