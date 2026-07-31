/*
 * FRIDAY Push-to-Talk hotkey helper (macOS).
 *
 * Registers a global hotkey for Right-Option + Space.
 *   keydown  -> POST /api/voice/ptt {"action":"start"}  (start listening)
 *   keyup    -> POST /api/voice/ptt {"action":"stop"}   (transcribe + process)
 *
 * Uses Carbon RegisterEventHotKey — works system-wide without accessibility
 * permission. Build: clang -framework Carbon -o ptt_hotkey ptt_hotkey.c
 */

#include <Carbon/Carbon.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

#define SERVER_URL "http://127.0.0.1:5050/api/voice/ptt"

static EventHotKeyRef gHotKey = NULL;

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

static OSStatus hotkey_handler(EventHandlerCallRef next, EventRef event, void *userData) {
    UInt32 kind = GetEventKind(event);
    if (kind == kEventHotKeyPressed) {
        post_action("start");
    } else if (kind == kEventHotKeyReleased) {
        post_action("stop");
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
        fprintf(stderr, "FRIDAY PTT: InstallEventHandler failed (%d)\n", (int)err);
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
        fprintf(stderr, "FRIDAY PTT: RegisterEventHotKey failed (%d)\n", (int)err);
        return 1;
    }

    fprintf(stdout, "FRIDAY PTT: hold Right-Option + Space to talk\n");
    fflush(stdout);

    CFRunLoopRun();   /* pump the Carbon event loop */
    return 0;
}
