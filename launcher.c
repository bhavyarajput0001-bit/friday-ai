#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <spawn.h>
#include <unistd.h>
#include <mach-o/dyld.h>

extern char **environ;

int main(int argc, const char * argv[]) {
    char path[1024];
    uint32_t size = sizeof(path);

    if (_NSGetExecutablePath(path, &size) != 0) return 1;

    char *p = strstr(path, "MacOS/FridayAI");
    if (!p) return 1;
    strcpy(p, "Resources/main_app.py");

    char *python = "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3";
    char *args[] = {"python3", path, NULL};

    pid_t pid;
    posix_spawnattr_t attr;
    posix_spawnattr_init(&attr);
    posix_spawnattr_setflags(&attr, POSIX_SPAWN_SETPGROUP);

    posix_spawn_file_actions_t actions;
    posix_spawn_file_actions_init(&actions);
    posix_spawn_file_actions_addclose(&actions, 0);
    posix_spawn_file_actions_addclose(&actions, 1);
    posix_spawn_file_actions_addclose(&actions, 2);

    int ret = posix_spawnp(&pid, python, &actions, &attr, args, environ);

    posix_spawn_file_actions_destroy(&actions);
    posix_spawnattr_destroy(&attr);

    if (ret != 0) return 1;

    // Detach — don't wait. App runs independently.
    return 0;
}
