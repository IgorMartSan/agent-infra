CREATE TABLE IF NOT EXISTS test_customers (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE,
  city VARCHAR(80) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS test_products (
  id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  sku VARCHAR(40) NOT NULL UNIQUE,
  price NUMERIC(10, 2) NOT NULL,
  stock INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS test_orders (
  id SERIAL PRIMARY KEY,
  customer_email VARCHAR(150) NOT NULL,
  product_sku VARCHAR(40) NOT NULL,
  quantity INTEGER NOT NULL,
  status VARCHAR(30) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO test_customers (name, email, city) VALUES
  ('Ana Silva', 'ana.silva@example.com', 'Sao Paulo'),
  ('Bruno Costa', 'bruno.costa@example.com', 'Rio de Janeiro'),
  ('Carla Mendes', 'carla.mendes@example.com', 'Belo Horizonte'),
  ('Diego Rocha', 'diego.rocha@example.com', 'Curitiba'),
  ('Elisa Nunes', 'elisa.nunes@example.com', 'Porto Alegre'),
  ('Felipe Martins', 'felipe.martins@example.com', 'Recife'),
  ('Gabriela Lima', 'gabriela.lima@example.com', 'Salvador'),
  ('Henrique Alves', 'henrique.alves@example.com', 'Fortaleza'),
  ('Isabela Torres', 'isabela.torres@example.com', 'Brasilia'),
  ('Joao Pereira', 'joao.pereira@example.com', 'Goiania')
ON CONFLICT (email) DO NOTHING;

INSERT INTO test_products (name, sku, price, stock) VALUES
  ('Notebook Pro 14', 'NB-PRO-14', 5299.90, 12),
  ('Mouse Wireless', 'MS-WLS-01', 129.90, 80),
  ('Teclado Mecanico', 'KB-MEC-01', 349.90, 35),
  ('Monitor 27 4K', 'MN-27-4K', 2199.90, 18),
  ('Headset USB', 'HS-USB-01', 249.90, 42),
  ('Webcam Full HD', 'WC-FHD-01', 199.90, 25),
  ('Dock USB-C', 'DK-USBC-01', 399.90, 16),
  ('SSD 1TB NVMe', 'SSD-NVME-1T', 499.90, 50),
  ('Cadeira Office', 'CH-OFF-01', 899.90, 10),
  ('Hub HDMI', 'HB-HDMI-01', 159.90, 60)
ON CONFLICT (sku) DO NOTHING;

INSERT INTO test_orders (customer_email, product_sku, quantity, status) VALUES
  ('ana.silva@example.com', 'NB-PRO-14', 1, 'paid'),
  ('bruno.costa@example.com', 'MS-WLS-01', 2, 'paid'),
  ('carla.mendes@example.com', 'KB-MEC-01', 1, 'pending'),
  ('diego.rocha@example.com', 'MN-27-4K', 1, 'shipped'),
  ('elisa.nunes@example.com', 'HS-USB-01', 1, 'paid'),
  ('felipe.martins@example.com', 'WC-FHD-01', 3, 'pending'),
  ('gabriela.lima@example.com', 'DK-USBC-01', 1, 'cancelled'),
  ('henrique.alves@example.com', 'SSD-NVME-1T', 2, 'paid'),
  ('isabela.torres@example.com', 'CH-OFF-01', 1, 'shipped'),
  ('joao.pereira@example.com', 'HB-HDMI-01', 4, 'paid');
