/*
 * FRIDAY Push-to-Talk hotkey helper (macOS).
 *
 * Registers a global hotkey for Right-Option + Space.
 *   App running + press    -> POST /api/voice/ptt start (hold to talk)
 *   Release                -> POST /api/voice/ptt stop (transcribe + process)
 *   App closed + press     -> does nothing (app only starts when you open it)
 *
 * Uses Carbon RegisterEventHotKey — works system-wide without accessibility
 * permission. Build: clang -framework Carbon -o ptt_hotkey ptt_hotkey.c
 */

#include <Carbon/Carbon.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

#define SERVER_URL  "http://127.0.0.1:5050/api/voice/ptt"
#define HEALTH_URL  "http://127.0.0.1:5050/api/health"

static EventHotKeyRef gHotKey = NULL;
static int gListening = 0;   /* whether current press started listening */

/* Minimal HTTP POST via curl — fire and forget. */
static void post_action(const char *action) {
    char cmd[512];
    snprintf(cmd, sizeof(cmd),
        "curl -s -m 2 -X POST " SERVER_URL
        " -H 'Content-Type: application/json'"
        " -d '{\"action\":\"%s\"}' >/dev/null 2>&1 &",
        action);
    (void)system(cmd);
}

/* Returns 1 if the FRIDAY core is already running and reachable. */
static int server_running(void) {
    char cmd[512];
    snprintf(cmd, sizeof(cmd),
        "curl -s -m 1 -o /dev/null -w '%%{http_code}' " HEALTH_URL " 2>/dev/null");
    FILE *fp = popen(cmd, "r");
    if (!fp) return 0;
    char buf[16] = {0};
    if (fgets(buf, sizeof(buf), fp) == NULL) { pclose(fp); return 0; }
    pclose(fp);
    return strncmp(buf, "200", 3) == 0;
}

static OSStatus hotkey_handler(EventHandlerCallRef next, EventRef event, void *userData) {
    UInt32 kind = GetEventKind(event);
    if (kind == kEventHotKeyPressed) {
        if (server_running()) {
            gListening = 1;
            post_action("start");
        } else {
            /* App closed — do nothing. FRIDAY only starts when the user opens it. */
            gListening = 0;
        }
    } else if (kind == kEventHotKeyReleased) {
        if (gListening) {
            gListening = 0;
            post_action("stop");
        }
    }
    return noErr;
}

int main(int argc, const char *argv[]) {
    EventTypeSpec specs[] = {
        { kEventClassKeyboard, kEventHotKeyPressed },
        { kEventClassKeyboard, kEventHotKeyReleased },
    };

    OSStatus err = InstallEventHandler(
        GetApplicationEventTarget(),
        NewEventHandlerUPP(hotkey_handler),
        2, specs, NULL, NULL);
    if (err != noErr) {
        fprintf(stderr, "FRIDAY hotkey: InstallEventHandler failed (%d)\n", (int)err);
        return 1;
    }

    EventHotKeyID hotKeyID = { 'FRDY', 1 };
    err = RegisterEventHotKey(
        kVK_Space,                     /* Space */
        rightOptionKey | optionKey,    /* Right Option (allow either option) */
        hotKeyID,
        GetApplicationEventTarget(),
        0, &gHotKey);
    if (err != noErr) {
        fprintf(stderr, "FRIDAY hotkey: RegisterEventHotKey failed (%d)\n", (int)err);
        return 1;
    }

    fprintf(stdout, "FRIDAY: press Right-Option + Space to talk (app must be open)\n");
    fflush(stdout);

    CFRunLoopRun();   /* pump the Carbon event loop */
    return 0;
}
