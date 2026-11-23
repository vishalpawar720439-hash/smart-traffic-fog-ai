"""
AURA-FOG // Real-Time AI Smart Traffic & Accident Detection
Launcher and Startup Script
"""
import sys
import os
import time
import webbrowser
import uvicorn

BANNER = r"""
   ___   __  ______  ___      _______  ____ 
  / _ | / / / / __ \/ _ |____/ __/ _ \/ ___/
 / __ |/ /_/ / /_/ / __ /___/ _// // / (_ / 
/_/ |_|\____/\____/_/ |_|  /_/  \___/\___/  
                                            
Real-Time AI Smart Traffic & Accident Detection Fog Computing System
=====================================================================
>> Decentralized Edge Vision Processing
>> Sub-10ms Accident Collision AI Detection
>> Dynamic Webster-Adaptive Traffic Signal Control
>> Emergency Vehicle "Green Wave" Preemption
>> 99%+ Bandwidth Filtering (Fog Edge vs Cloud)
=====================================================================
"""


def main():
    print(BANNER)
    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}"

    print(f"[*] Starting Fog Computing Gateway at {url}...")
    print(f"[*] Live Dashboard available at: {url}")
    print("[*] Press Ctrl+C in terminal to stop server.\n")

    # Optional: open browser after short delay
    def open_browser():
        time.sleep(1.2)
        print(f"[*] Opening browser to {url}...")
        webbrowser.open(url)

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # Run Uvicorn server
    uvicorn.run("backend.main:app", host=host, port=port, reload=False, log_level="info")


if __name__ == "__main__":
    main()
