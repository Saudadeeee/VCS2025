#include <iostream>
#include <string>
#include <vector>
#include <memory>
#include <pwd.h>
#include <grp.h>
#include <unistd.h>

int main() {
    std::string username;
    struct passwd *pwd;
    struct group *grp;
    
    std::cout << "Enter username: ";
    std::cin >> username;
    if (std::cin.fail()) {
        std::cerr << "Error reading username" << std::endl;
        return 1;
    }
    
    // Find user in /etc/passwd
    pwd = getpwnam(username.c_str());
    if (pwd == NULL) {
        std::cout << "User '" << username << "' not found" << std::endl;
        return 1;
    }
    int ngroups = 10;
    std::vector<gid_t> groups(ngroups);
    
    int result = getgrouplist(username.c_str(), pwd->pw_gid, groups.data(), &ngroups);
    if (result == -1) {

        groups.resize(ngroups);
        getgrouplist(username.c_str(), pwd->pw_gid, groups.data(), &ngroups);
    }
    std::cout << "uid=" << pwd->pw_uid << "(" << pwd->pw_name << ") ";
    
    // Find primary group
    grp = getgrgid(pwd->pw_gid);
    if (grp)
        std::cout << "gid=" << pwd->pw_gid << "(" << grp->gr_name << ") ";
    else
        std::cout << "gid=" << pwd->pw_gid << " ";
    
    // Display home directory
    std::cout << "home=" << pwd->pw_dir << std::endl;
    
    // List all groups
    std::cout << "groups=";
    for (int i = 0; i < ngroups; i++) {
        grp = getgrgid(groups[i]);
        if (grp)
            std::cout << groups[i] << "(" << grp->gr_name << ")" << (i < ngroups-1 ? "," : "");
        else
            std::cout << groups[i] << (i < ngroups-1 ? "," : "");
    }
    std::cout << std::endl;
    
    return 0;
}
