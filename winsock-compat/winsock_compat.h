/*
 * winsock_compat.h
 *
 * Lets the POSIX socket programs in this repository build with MinGW gcc
 * on Windows without changing a single line of the experiment code.
 *
 *   gcc tcp_server.c -o tcp_server.exe -I ..\winsock-compat -lws2_32
 *
 * On Linux / WSL / macOS this folder is simply not used.
 */
#ifndef CN_WINSOCK_COMPAT_H
#define CN_WINSOCK_COMPAT_H

#ifdef _WIN32

#include <winsock2.h>
#include <ws2tcpip.h>
#include <stdio.h>
#include <string.h>

/* Windows has no SO_REUSEPORT; SO_REUSEADDR on its own is enough here. */
#ifndef SO_REUSEPORT
#define SO_REUSEPORT 0
#endif

#ifndef SHUT_RDWR
#define SHUT_RDWR SD_BOTH
#endif

/* Winsock declares the option value as const char *. */
#define setsockopt(s, level, name, val, len) \
    setsockopt((s), (level), (name), (const char *)(val), (len))

/* Older MinGW headers do not provide inet_pton(); IPv4 is all we need. */
__attribute__((unused))
static int cn_inet_pton(int af, const char *src, void *dst) {
    struct in_addr a;

    if (af != AF_INET)
        return -1;

    a.s_addr = inet_addr(src);
    if (a.s_addr == INADDR_NONE && strcmp(src, "255.255.255.255") != 0)
        return 0;

    memcpy(dst, &a, sizeof(a));
    return 1;
}
#define inet_pton cn_inet_pton

/*
 * Runs before main(): starts Winsock (required on Windows before any socket
 * call) and makes stdout unbuffered so output appears immediately, the same
 * way it does in a Linux terminal.
 */
__attribute__((constructor))
static void cn_winsock_init(void) {
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
    setvbuf(stdout, NULL, _IONBF, 0);
}

#endif /* _WIN32 */

#endif /* CN_WINSOCK_COMPAT_H */
