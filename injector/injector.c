#include <stdio.h>
#include <stdlib.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    pid_t target_pid = atoi(argv[1]);

    if (ptrace(PTRACE_ATTACH, target_pid, NULL, NULL) == -1) {
        perror("PTRACE_ATTACH failed");
        return 1;
    }

    waitpid(target_pid, NULL, 0);
    printf("[+] Attached to PID %d\n", target_pid);

    // TODO: mmap, write shellcode, hijack PC to injected shellcode

    ptrace(PTRACE_DETACH, target_pid, NULL, NULL);
    return 0;
}
