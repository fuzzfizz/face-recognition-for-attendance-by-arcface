FROM php:8.2-apache

# Install PDO MySQL extension
RUN docker-php-ext-install pdo pdo_mysql

# Enable Apache rewrite module for .htaccess support
RUN a2enmod rewrite

# Set directory permissions for security
RUN sed -ri -e 's!/var/www/html!/var/www/html!g' /etc/apache2/sites-available/*.conf
RUN sed -ri -e 's!/var/www/!/var/www/!g' /etc/apache2/apache2.conf /etc/apache2/conf-available/*.conf

# Copy application files to web server root
COPY . /var/www/html/

# Ensure proper file ownership
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80