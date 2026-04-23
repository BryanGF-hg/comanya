sudo mysql -u root -p
CREATE DATABASE IF NOT EXISTS comanya;
USE comanya;

CREATE TABLE IF NOT EXISTS entrada (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    empresa VARCHAR(255),
    cnae VARCHAR(10),
    provincia VARCHAR(100),
    empleados INT,
    facturacion DECIMAL(15,2),
    archivo_excel VARCHAR(255)
);

CREATE USER IF NOT EXISTS 'comanya'@'localhost' IDENTIFIED BY 'comanya';

GRANT USAGE ON *.* TO 'comanya'@'localhost';
ALTER USER 'comanya'@'localhost' 
REQUIRE NONE 
WITH MAX_QUERIES_PER_HOUR 0 
MAX_CONNECTIONS_PER_HOUR 0 
MAX_UPDATES_PER_HOUR 0 
MAX_USER_CONNECTIONS 0;

GRANT ALL PRIVILEGES ON comanya.* TO 'comanya'@'localhost';

FLUSH PRIVILEGES;
