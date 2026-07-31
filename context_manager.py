import time
import threading
from AppKit import NSWorkspace

class FridayContext:
    def __init__(self, callback=None):
        self.callback = callback
        self.active_app = None
        self.active_title = None
        self.start_time = time.time()
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                # Use AppKit to get frontmost app
                workspace = NSWorkspace.sharedWorkspace()
                active_app = workspace.frontmostApplication()
                
                if active_app:
                    app_name = active_app.localizedName()
                    # Window title extraction is trickier due to privacy/permissions,
                    # but localizedName works well for the "App context".
                    
                    if app_name != self.active_app:
                        # Logic to calculate duration of previous app
                        now = time.time()
                        duration = int(now - self.start_time)
                        
                        prev_app = self.active_app
                        self.active_app = app_name
                        self.start_time = now
                        
                        if self.callback and prev_app:
                            self.callback(prev_app, duration)
                            
                        # Notify about new app
                        if self.callback:
                            self.callback(app_name, 0, is_new=True)

            except Exception as e:
                print(f"[Context] Error: {e}")
            
            time.sleep(3) # Poll every 3 seconds

# Example usage/test
if __name__ == "__main__":
    def my_cb(name, duration, is_new=False):
        if is_new:
            print(f"--- Focused on: {name}")
        else:
            print(f"--- Spent {duration}s in {name}")

    ctx = FridayContext(callback=my_cb)
    ctx.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        ctx.stop()
