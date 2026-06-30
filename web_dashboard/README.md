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
   > Use the **Service Role Key** (not the anon key) – found in your Supabase project under Settings → API.

3. Run the built-in PHP server:
   ```bash
   cd web_dashboard
   php -S localhost:8080
   ```

4. Open `http://localhost:8080` in your browser.

## Deployment
Point Apache or Nginx at the `web_dashboard/` directory. Ensure `config.php` is not web-accessible (it's outside `api/` and not served directly).
