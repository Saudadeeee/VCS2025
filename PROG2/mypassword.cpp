#include <iostream>
#include <string>
#include <cstring>
#include <fstream>
#include <unistd.h>
#include <shadow.h>
#include <crypt.h>
#include <pwd.h>
#include <errno.h>
#include <termios.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <cstdlib>
#include <ctime>

// Function to read password without echoing to screen
std::string getpass_custom(const std::string &prompt) {
    struct termios old_t, new_t;
    std::string password;
    char c;
    if (tcgetattr(STDIN_FILENO, &old_t) != 0)
        return "";
    
    new_t = old_t;
    new_t.c_lflag &= ~ECHO; // Disable echo
    
    // Set new terminal attributes
    if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &new_t) != 0)
        return "";
    std::cout << prompt;
    std::cout.flush();
    
    // Read password
    while (true) {
        c = getchar();
        if (c == '\n' || c == '\r')
            break;
        password += c;
    }
    tcsetattr(STDIN_FILENO, TCSAFLUSH, &old_t);
    
    std::cout << std::endl;
    return password;
}

int update_shadow_file(const std::string &username, const std::string &new_encrypted_password) {
    std::ifstream shadow_file("/etc/shadow");
    if (!shadow_file) {
        std::cerr << "Failed to open shadow file: " << strerror(errno) << std::endl;
        return -1;
    }
    
    // Create temporary file in /etc directory to avoid cross-filesystem issues
    std::string temp_file = "/etc/shadow.tmp";
    std::ofstream temp_shadow(temp_file);
    if (!temp_shadow) {
        std::cerr << "Failed to create temporary file: " << strerror(errno) << std::endl;
        return -1;
    }
    
    // Set secure permissions on temporary file
    if (chmod(temp_file.c_str(), S_IRUSR | S_IWUSR) != 0) {
        std::cerr << "Failed to set permissions on temporary file: " << strerror(errno) << std::endl;
        unlink(temp_file.c_str());
        return -1;
    }
    
    std::string line;
    bool found = false;
    while (std::getline(shadow_file, line)) {
        std::string current_line = line;
        size_t pos = current_line.find(':');
        
        if (pos != std::string::npos) {
            std::string current_username = current_line.substr(0, pos);
            
            if (current_username == username) {
                // Found the user, update the password
                std::string remaining = current_line.substr(pos + 1);
                pos = remaining.find(':');
                std::string rest_of_line = (pos != std::string::npos) ? 
                                          remaining.substr(pos + 1) : "";
                
                temp_shadow << username << ":" << new_encrypted_password << ":"
                           << rest_of_line << std::endl;
                found = true;
            } else {
                temp_shadow << line << std::endl;
            }
        } else {
            temp_shadow << line << std::endl;
        }
    }
    
    shadow_file.close();
    temp_shadow.close();
    
    if (!found) {
        unlink(temp_file.c_str());
        return -1;  // User not found
    }
    
    // Replace the shadow file with updated one
    if (rename(temp_file.c_str(), "/etc/shadow") != 0) {
        std::cerr << "Failed to update shadow file: " << strerror(errno) << std::endl;
        unlink(temp_file.c_str());
        return -1;
    }
    
    return 0;
}

int main() {
    struct passwd *pw;
    struct spwd *spw;
    std::string old_password, new_password, confirm_password;
    char *encrypted_old, *encrypted_new;
    
    // Get current user
    pw = getpwuid(getuid());
    if (pw == NULL) {
        std::cerr << "getpwuid error: " << strerror(errno) << std::endl;
        return 1;
    }
    
    // Get shadow password entry
    spw = getspnam(pw->pw_name);
    if (spw == NULL) {
        std::cerr << "Error accessing shadow password file. Are you root?" << std::endl;
        return 1;
    }
    old_password = getpass_custom("Current password: ");
    if (old_password.empty()) {
        std::cerr << "Error reading password" << std::endl;
        return 1;
    }
    
    // Verify current password
    encrypted_old = crypt(old_password.c_str(), spw->sp_pwdp);
    if (encrypted_old == NULL) {
        std::cerr << "crypt error: " << strerror(errno) << std::endl;
        return 1;
    }
    
    if (strcmp(encrypted_old, spw->sp_pwdp) != 0) {
        std::cerr << "Incorrect password" << std::endl;
        return 1;
    }
    
    // Ask for new password
    new_password = getpass_custom("New password: ");
    if (new_password.empty()) {
        std::cerr << "Error reading password" << std::endl;
        return 1;
    }
    
    // Confirm new password
    confirm_password = getpass_custom("Confirm new password: ");
    if (confirm_password.empty()) {
        std::cerr << "Error reading password" << std::endl;
        return 1;
    }
    
    if (new_password != confirm_password) {
        std::cerr << "Passwords do not match" << std::endl;
        return 1;
    }
    
    // Generate encrypted password
    std::srand(std::time(nullptr));
    char salt[16];
    snprintf(salt, sizeof(salt), "$6$%08x%08x", rand(), rand());
    encrypted_new = crypt(new_password.c_str(), salt);
    if (encrypted_new == NULL) {
        std::cerr << "crypt error: " << strerror(errno) << std::endl;
        return 1;
    }
    
    // Update password in /etc/shadow
    if (update_shadow_file(pw->pw_name, encrypted_new) != 0) {
        std::cerr << "Failed to update password. Make sure you have sufficient privileges." << std::endl;
        return 1;
    }
    
    std::cout << "Password changed successfully" << std::endl;
    return 0;
}
