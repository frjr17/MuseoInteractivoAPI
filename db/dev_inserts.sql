-- Seed roles and 50 users for development
-- WARNING: This SQL assumes your DB accepts UUID literals in standard text form (Postgres does).
-- It inserts roles with the exact enum values used in `db/rol.py` (note spelling: 'SOPORTE').

BEGIN;

-- Roles
INSERT INTO roles (id, nombre, descripcion) VALUES
  ('00000000-0000-0000-0000-000000000001', 'ADMIN', 'Administrador con todos los privilegios'),
  ('00000000-0000-0000-0000-000000000002', 'SOPORTE', 'Soporte técnico'),
  ('00000000-0000-0000-0000-000000000003', 'USER', 'Usuario normal'),
  ('00000000-0000-0000-0000-000000000004', 'HOST', 'Anfitrión / curator de exposiciones');

-- 50 usuarios distribuidos aleatoriamente entre los roles
-- We'll reference role ids by the ones we just created.

INSERT INTO usuarios (id, nombre, apellido, email, password, role_id) VALUES
  ('10000000-0000-0000-0000-000000000001', 'Ana', 'García', 'ana.garcia@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-000000000002', 'Luis', 'Martínez', 'luis.martinez@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-000000000003', 'María', 'López', 'maria.lopez@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-000000000004', 'Carlos', 'Sánchez', 'carlos.sanchez@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-000000000005', 'Laura', 'Torres', 'laura.torres@example.com', 'password', '00000000-0000-0000-0000-000000000002'),
  ('10000000-0000-0000-0000-000000000006', 'Jorge', 'Ramírez', 'jorge.ramirez@example.com', 'password', '00000000-0000-0000-0000-000000000002'),
  ('10000000-0000-0000-0000-000000000007', 'Sofía', 'Gómez', 'sofia.gomez@example.com', 'password', '00000000-0000-0000-0000-000000000004'),
  ('10000000-0000-0000-0000-000000000008', 'Mateo', 'Díaz', 'mateo.diaz@example.com', 'password', '00000000-0000-0000-0000-000000000001'),
  ('10000000-0000-0000-0000-000000000009', 'Valeria', 'Vargas', 'valeria.vargas@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-00000000000a', 'Diego', 'Rojas', 'diego.rojas@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-00000000000b', 'Lucía', 'Méndez', 'lucia.mendez@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-00000000000c', 'Andrés', 'Núñez', 'andres.nunez@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-00000000000d', 'Paula', 'Castro', 'paula.castro@example.com', 'password', '00000000-0000-0000-0000-000000000002'),
  ('10000000-0000-0000-0000-00000000000e', 'Rafael', 'Herrera', 'rafael.herrera@example.com', 'password', '00000000-0000-0000-0000-000000000001'),
  ('10000000-0000-0000-0000-00000000000f', 'Camila', 'Silva', 'camila.silva@example.com', 'password', '00000000-0000-0000-0000-000000000004'),
  ('10000000-0000-0000-0000-000000000010', 'Hugo', 'Beltrán', 'hugo.beltran@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-000000000011', 'Irene', 'Paz', 'irene.paz@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-000000000012', 'Nicolás', 'Vega', 'nicolas.vega@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-000000000013', 'Marta', 'Ramos', 'marta.ramos@example.com', 'password', '00000000-0000-0000-0000-000000000002'),
  ('10000000-0000-0000-0000-000000000014', 'Óscar', 'Acosta', 'oscar.acosta@example.com', 'password', '00000000-0000-0000-0000-000000000001'),
  ('10000000-0000-0000-0000-000000000015', 'Elena', 'Paredes', 'elena.paredes@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-000000000016', 'Gonzalo', 'Flores', 'gonzalo.flores@example.com', 'password', '00000000-0000-0000-0000-000000000004'),
  ('10000000-0000-0000-0000-000000000017', 'Iris', 'Mora', 'iris.mora@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-000000000018', 'Raúl', 'Salinas', 'raul.salinas@example.com', 'password', '00000000-0000-0000-0000-000000000002'),
  ('10000000-0000-0000-0000-000000000019', 'Sergio', 'Cruz', 'sergio.cruz@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-00000000001a', 'Teresa', 'León', 'teresa.leon@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-00000000001b', 'Federico', 'Ortega', 'federico.ortega@example.com', 'password', '00000000-0000-0000-0000-000000000004'),
  ('10000000-0000-0000-0000-00000000001c', 'Noemí', 'Peralta', 'noemi.peralta@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-00000000001d', 'Esteban', 'Camacho', 'esteban.camacho@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-00000000001e', 'Adriana', 'Solís', 'adriana.solis@example.com', 'password', '00000000-0000-0000-0000-000000000002'),
  ('10000000-0000-0000-0000-00000000001f', 'Pablo', 'Benítez', 'pablo.benitez@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-000000000020', 'Marcos', 'Leiva', 'marcos.leiva@example.com', 'password', '00000000-0000-0000-0000-000000000001'),
  ('10000000-0000-0000-0000-000000000021', 'Bianca', 'Arias', 'bianca.arias@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-000000000022', 'Agustín', 'Ibarra', 'agustin.ibarra@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-000000000023', 'Daniela', 'Paz', 'daniela.paz2@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-000000000024', 'Fabián', 'Quintero', 'fabian.quintero@example.com', 'password', '00000000-0000-0000-0000-000000000001'),
  ('10000000-0000-0000-0000-000000000025', 'Silvana', 'Molina', 'silvana.molina@example.com', 'password', '00000000-0000-0000-0000-000000000004'),
  ('10000000-0000-0000-0000-000000000026', 'Óliver', 'Pinto', 'oliver.pinto@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-000000000027', 'Catalina', 'Reyes', 'catalina.reyes@example.com', 'password', '00000000-0000-0000-0000-000000000002'),
  ('10000000-0000-0000-0000-000000000028', 'Hernán', 'Bravo', 'hernan.bravo@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-000000000029', 'Lorena', 'Córdoba', 'lorena.cordoba@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-00000000002a', 'Rocio', 'Aguirre', 'rocio.aguirre@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-00000000002b', 'Alvaro', 'Mora', 'alvaro.mora@example.com', 'password', '00000000-0000-0000-0000-000000000001'),
  ('10000000-0000-0000-0000-00000000002c', 'Ximena', 'Fuentes', 'ximena.fuentes@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-00000000002d', 'Bruno', 'Salcedo', 'bruno.salcedo@example.com', 'password', '00000000-0000-0000-0000-000000000004'),
  ('10000000-0000-0000-0000-00000000002e', 'Iván', 'Soto', 'ivan.soto@example.com', 'password', '00000000-0000-0000-0000-000000000003'),
  ('10000000-0000-0000-0000-00000000002f', 'Yasmin', 'Cárdenas', 'yasmin.cardenas@example.com', 'password', '00000000-0000-0000-0000-000000000002');

COMMIT;

-- End of seed file