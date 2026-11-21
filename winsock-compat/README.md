# winsock-compat

A tiny set of header stand-ins that let the **unchanged** POSIX socket programs of
Experiments 02 – 05 compile with **MinGW gcc on Windows**.

```powershell
cd Experiment-02-TCP-Server
gcc -Wall tcp_server.c -o tcp_server.exe -I ..\winsock-compat -lws2_32
```

On Linux, WSL or macOS you do **not** need this folder: just `gcc tcp_server.c -o tcp_server`.

| Header here | What it does on Windows |
| ----------- | ----------------------- |
| `sys/socket.h`, `netinet/in.h`, `arpa/inet.h` | include `winsock_compat.h` (Winsock 2 + `ws2tcpip.h`) |
| `unistd.h` | includes the real `<unistd.h>`, then maps `close()` → `closesocket()` and `read()` → `recv()` for sockets |
| `winsock_compat.h` | calls `WSAStartup()` before `main()`, defines `SO_REUSEPORT` / `SHUT_RDWR`, adds `inet_pton()` for IPv4, unbuffers `stdout` |

Because `-I` directories are searched before the system include directories, the programs pick
up these files instead of the (missing) POSIX headers, and nothing in the `.c` files changes.
