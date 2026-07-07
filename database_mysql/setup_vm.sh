#!/usr/bin/env bash
set -euo pipefail

# Get directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "=== Installing MySQL Server ==="
sudo apt-get update
sudo apt-get install -y mysql-server python3-pip

echo "=== Configuring MySQL for Remote Connections ==="
# Bind to 0.0.0.0 to allow connection from the FastAPI app server
sudo sed -i "s/bind-address.*/bind-address = 0.0.0.0/" /etc/mysql/mysql.conf.d/mysqld.cnf
sudo systemctl restart mysql

echo "=== Creating Database and User ==="
# Set database name, user, and password
DB_NAME="face_attendance"
DB_USER="face_admin"
DB_PASS="SecurePassword123!" # Change this on deployment!

sudo mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS ${DB_NAME};
CREATE USER IF NOT EXISTS '${DB_USER}'@'%' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'%';
FLUSH PRIVILEGES;
EOF

echo "=== Running init_schema.sql ==="
sudo mysql -u root < "${SCRIPT_DIR}/init_schema.sql"

echo "=== Setup Complete ==="
echo "MySQL is running and listening on 0.0.0.0:3306"
