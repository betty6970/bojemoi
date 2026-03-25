/*
 * DVAR - Damn Vulnerable ARM Router
 * Vulnerable HTTP server — lab target only
 *
 * Vulnerabilities:
 *   1. Command injection via /cgi-bin/ping.cgi?host=
 *   2. Command injection via POST /apply.cgi (Linksys-style, ping_ipaddr param)
 *   3. Stack buffer overflow via /overflow?data= (for ARM BoF training)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/wait.h>
#include <signal.h>

#define PORT     80
#define BUFSIZE  4096

/* URL decode in-place */
static void url_decode(const char *src, char *dst, size_t dstsz) {
    size_t i = 0;
    while (*src && i + 1 < dstsz) {
        if (*src == '%' && src[1] && src[2]) {
            char hex[3] = { src[1], src[2], 0 };
            dst[i++] = (char)strtol(hex, NULL, 16);
            src += 3;
        } else if (*src == '+') {
            dst[i++] = ' ';
            src++;
        } else {
            dst[i++] = *src++;
        }
    }
    dst[i] = '\0';
}

/* Extract param value from query string — returns static buffer */
static char *get_param(const char *query, const char *name) {
    static char val[512];
    char needle[64];
    snprintf(needle, sizeof(needle), "%s=", name);
    const char *p = strstr(query, needle);
    if (!p) return NULL;
    p += strlen(needle);
    const char *end = strchr(p, '&');
    size_t len = end ? (size_t)(end - p) : strlen(p);
    if (len >= sizeof(val)) len = sizeof(val) - 1;
    strncpy(val, p, len);
    val[len] = '\0';
    char decoded[512];
    url_decode(val, decoded, sizeof(decoded));
    strncpy(val, decoded, sizeof(val));
    return val;
}

/* Deliberately vulnerable — strcpy with no bounds check */
static void vuln_parse(const char *input) {
    char buf[64];
    strcpy(buf, input);   /* BOF: stack buffer overflow */
    (void)buf;
}

static void http_respond(int fd, int status, const char *body) {
    char hdr[256];
    snprintf(hdr, sizeof(hdr),
        "HTTP/1.1 %d OK\r\n"
        "Content-Type: text/html\r\n"
        "Content-Length: %zu\r\n"
        "Connection: close\r\n"
        "Server: DVAR/1.0 (Linux; ARM)\r\n"
        "\r\n",
        status, strlen(body));
    write(fd, hdr, strlen(hdr));
    write(fd, body, strlen(body));
}

static void handle(int fd) {
    char buf[BUFSIZE];
    int n = read(fd, buf, sizeof(buf) - 1);
    if (n <= 0) { close(fd); return; }
    buf[n] = '\0';

    char method[16], path[256];
    sscanf(buf, "%15s %255s", method, path);

    /* Split path and query string */
    char query[1024] = "";
    char *qs = strchr(path, '?');
    if (qs) { *qs = '\0'; strncpy(query, qs + 1, sizeof(query) - 1); }

    /* For POST: pull body as query string */
    if (strcmp(method, "POST") == 0) {
        char *body_start = strstr(buf, "\r\n\r\n");
        if (body_start) {
            body_start += 4;
            strncpy(query, body_start, sizeof(query) - 1);
        }
    }

    char out[4096] = "";

    /* Route: / */
    if (strcmp(path, "/") == 0) {
        snprintf(out, sizeof(out),
            "<html><head><title>DVAR Router</title></head><body>"
            "<h1>Damn Vulnerable ARM Router</h1>"
            "<p>Firmware: v1.0.0 | Arch: ARMv7-LE | OS: Linux 2.6.36</p>"
            "<ul>"
            "<li><a href='/cgi-bin/ping.cgi'>Ping Utility</a> (GET ?host=)</li>"
            "<li><a href='/apply.cgi'>Apply Settings</a> (POST ping_ipaddr=)</li>"
            "<li><a href='/overflow?data=AAAA'>Stack Overflow Test</a></li>"
            "</ul>"
            "</body></html>");

    /* Route: /cgi-bin/ping.cgi?host=<INJECT> */
    } else if (strcmp(path, "/cgi-bin/ping.cgi") == 0) {
        char *host = get_param(query, "host");
        if (host && *host) {
            char cmd[512];
            /* VULN: command injection — no sanitization of $host */
            snprintf(cmd, sizeof(cmd), "ping -c2 %s 2>&1", host);
            FILE *fp = popen(cmd, "r");
            if (fp) { fread(out, 1, sizeof(out) - 1, fp); pclose(fp); }
        } else {
            strcpy(out,
                "<html><body><h1>Ping</h1>"
                "<form><input name=host><input type=submit value=Ping></form>"
                "</body></html>");
        }

    /* Route: /apply.cgi  POST ping_ipaddr=<INJECT>  (Linksys E1500 style) */
    } else if (strcmp(path, "/apply.cgi") == 0) {
        char *ip = get_param(query, "ping_ipaddr");
        if (!ip) ip = get_param(query, "cmdinput");
        if (ip && *ip) {
            char cmd[512];
            /* VULN: command injection */
            snprintf(cmd, sizeof(cmd), "ping -c2 %s 2>&1", ip);
            FILE *fp = popen(cmd, "r");
            if (fp) { fread(out, 1, sizeof(out) - 1, fp); pclose(fp); }
        } else {
            strcpy(out, "result=0");
        }

    /* Route: /overflow?data=<LONG>  — stack buffer overflow */
    } else if (strcmp(path, "/overflow") == 0) {
        char *data = get_param(query, "data");
        if (data && *data) {
            vuln_parse(data);   /* VULN: stack BOF */
        }
        strcpy(out, "<html><body>OK</body></html>");

    } else {
        http_respond(fd, 404, "<html><body>404 Not Found</body></html>");
        close(fd);
        return;
    }

    http_respond(fd, 200, out);
    close(fd);
}

static void reap(int s) { (void)s; while (waitpid(-1, NULL, WNOHANG) > 0); }

int main(void) {
    signal(SIGCHLD, reap);

    int srv = socket(AF_INET, SOCK_STREAM, 0);
    int opt = 1;
    setsockopt(srv, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr = {
        .sin_family      = AF_INET,
        .sin_addr.s_addr = INADDR_ANY,
        .sin_port        = htons(PORT),
    };
    bind(srv, (struct sockaddr *)&addr, sizeof(addr));
    listen(srv, 10);

    fprintf(stdout, "[DVAR] HTTP listening on :%d  (ARM vuln httpd)\n", PORT);
    fflush(stdout);

    while (1) {
        socklen_t al = sizeof(addr);
        int cli = accept(srv, (struct sockaddr *)&addr, &al);
        if (cli < 0) continue;
        if (fork() == 0) { close(srv); handle(cli); exit(0); }
        close(cli);
    }
}
