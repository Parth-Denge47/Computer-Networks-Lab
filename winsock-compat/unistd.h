/* Windows stand-in for <unistd.h>: sockets are closed and read with Winsock. */
#ifndef CN_COMPAT_UNISTD_H
#define CN_COMPAT_UNISTD_H

#include_next <unistd.h>
#include "winsock_compat.h"

#ifdef _WIN32
#define close(fd)        closesocket(fd)
#define read(fd, buf, n) recv((fd), (char *)(buf), (n), 0)
#endif

#endif
