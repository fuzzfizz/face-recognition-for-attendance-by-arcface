# FaceAttend Web Dashboard

A PHP dashboard for the face recognition attendance system.

## Requirements
- PHP 8.0+
- Access to your Supabase project

## Setup

1. Copy the config template:
   ```bash
   cp config.example.php config.php
   ```

2. Edit `config.php` and fill in your Supabase URL and Service Role Key.
   > [!IMPORTANT]
   > Use the **Service Role Key** (not the anon key) – found in your Supabase project under Settings → API.
   >
   > **Security Note:** `config.php` contains sensitive credentials and must **NEVER** be committed to Git. The project `.gitignore` file is pre-configured to exclude `config.php` from version control.

3. Run the built-in PHP server:
   ```bash
   cd web_dashboard
   php -S localhost:8080
   ```

4. Open `http://localhost:8080` in your browser.

## Deployment
Point Apache or Nginx at the `web_dashboard/` directory. 

### Restricting Access to `config.php`
Because `config.php` resides within the web root, it is critical to configure your web server to block direct HTTP requests to it, preventing credential exposure if the PHP interpreter is disabled or misconfigured.

#### Apache (.htaccess)
An `.htaccess` file should be placed in the `web_dashboard/` directory containing:
```apache
<Files "config.php">
    <IfModule authz_core_module>
        Require all denied
    </IfModule>
    <IfModule !authz_core_module>
        Order deny,allow
        Deny from all
    </IfModule>
</Files>
```
*(Ensure `AllowOverride All` or `AllowOverride Limit` is enabled in your Apache virtual host configuration.)*

#### Nginx
Add the following location block to your server configuration:
```nginx
location ~ /config\.php$ {
    deny all;
    return 404;
}
```

