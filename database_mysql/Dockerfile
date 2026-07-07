FROM mysql:8.0

# Copy the schema initialization script
# Any .sql or .sh files copied here are executed on startup when the database starts for the first time
COPY init_schema.sql /docker-entrypoint-initdb.d/

# Expose standard MySQL port
EXPOSE 3306
