-- =============================================
-- RezerviŠik - INSERT Skript
-- Postojeci legacy useri: 1-6
-- Postojeci auth_useri: 1-14
-- Novi legacy useri: 7-14
-- Novi auth_useri: 15-22
-- =============================================

SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE notification;
TRUNCATE TABLE appointment;
TRUNCATE TABLE review;
TRUNCATE TABLE google_calendar_connection;
TRUNCATE TABLE staff;
TRUNCATE TABLE owner;
TRUNCATE TABLE service;
TRUNCATE TABLE salon;

SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------
-- Novi legacy korisnici (7-14)
-- 7, 8, 9    = vlasnici salona
-- 10, 11, 12 = osoblje
-- 13, 14     = klijenti
-- ----------------------------
INSERT INTO user (useriId, name, surname, email, password, phone) VALUES
(7,  'Stefan',   'Nikolić',   'stefan.nikolic@gmail.com',   'pbkdf2_sha256$dummy$hash', '0663456789'),
(8,  'Milica',   'Djordjevic','milica.djordjevic@gmail.com','pbkdf2_sha256$dummy$hash', '0674567890'),
(9,  'Jovana',   'Stankovic', 'jovana.stankovic2@gmail.com','pbkdf2_sha256$dummy$hash', '0685678901'),
(10, 'Nikola',   'Vasic',     'nikola.vasic@gmail.com',     'pbkdf2_sha256$dummy$hash', '0696789012'),
(11, 'Tijana',   'Ilic',      'tijana.ilic@gmail.com',      'pbkdf2_sha256$dummy$hash', '0607890123'),
(12, 'Aleksa',   'Popovic',   'aleksa.popovic@gmail.com',   'pbkdf2_sha256$dummy$hash', '0618901234'),
(13, 'Katarina', 'Lazic',     'katarina.lazic@gmail.com',   'pbkdf2_sha256$dummy$hash', '0629012345'),
(14, 'Luka',     'Savic',     'luka.savic2@gmail.com',      'pbkdf2_sha256$dummy$hash', '0631234567');

-- ----------------------------
-- Novi auth_useri (15-22)
-- ----------------------------
INSERT INTO auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) VALUES
(15, 'pbkdf2_sha256$dummy$hash', NULL, 0, 'stefan.nikolic@gmail.com',   'Stefan',   'Nikolic',   'stefan.nikolic@gmail.com',   0, 1, '2026-01-01 10:00:00'),
(16, 'pbkdf2_sha256$dummy$hash', NULL, 0, 'milica.djordjevic@gmail.com','Milica',   'Djordjevic','milica.djordjevic@gmail.com', 0, 1, '2026-01-02 10:00:00'),
(17, 'pbkdf2_sha256$dummy$hash', NULL, 0, 'jovana.stankovic2@gmail.com','Jovana',   'Stankovic', 'jovana.stankovic2@gmail.com', 0, 1, '2026-01-03 10:00:00'),
(18, 'pbkdf2_sha256$dummy$hash', NULL, 0, 'nikola.vasic@gmail.com',     'Nikola',   'Vasic',     'nikola.vasic@gmail.com',      0, 1, '2026-01-04 10:00:00'),
(19, 'pbkdf2_sha256$dummy$hash', NULL, 0, 'tijana.ilic@gmail.com',      'Tijana',   'Ilic',      'tijana.ilic@gmail.com',       0, 1, '2026-01-05 10:00:00'),
(20, 'pbkdf2_sha256$dummy$hash', NULL, 0, 'aleksa.popovic@gmail.com',   'Aleksa',   'Popovic',   'aleksa.popovic@gmail.com',    0, 1, '2026-01-06 10:00:00'),
(21, 'pbkdf2_sha256$dummy$hash', NULL, 0, 'katarina.lazic@gmail.com',   'Katarina', 'Lazic',     'katarina.lazic@gmail.com',    0, 1, '2026-01-07 10:00:00'),
(22, 'pbkdf2_sha256$dummy$hash', NULL, 0, 'luka.savic2@gmail.com',      'Luka',     'Savic',     'luka.savic2@gmail.com',       0, 1, '2026-01-08 10:00:00');

-- ----------------------------
-- user_profile za nove korisnike
-- ----------------------------
INSERT INTO user_profile (django_user_id, legacy_user_id) VALUES
(15, 7),
(16, 8),
(17, 9),
(18, 10),
(19, 11),
(20, 12),
(21, 13),
(22, 14);

-- ----------------------------
-- Saloni
-- ----------------------------
INSERT INTO salon (salonId, name, description, address, working_hours, contact, grade) VALUES
(1, 'Salon Elegance',   'Frizerski salon sa dugogodisnjim iskustvom',        'Knez Mihailova 12, Beograd',      '08:00-20:00', '011-123-4567', 4.8),
(2, 'Beauty Studio',    'Kozmeticki studio za kompletan tretman lica i tela','Terazije 5, Beograd',             '09:00-19:00', '011-234-5678', 4.5),
(3, 'Barber Shop King', 'Muski frizerski salon u modernom stilu',            'Bulevar Oslobodjenja 22, Novi Sad','09:00-18:00', '021-345-6789', 4.7),
(4, 'Wellness Centar',  'Masaze, spa i wellness tretmani',                   'Cara Dusana 8, Nis',              '10:00-21:00', '018-456-7890', 4.6),
(5, 'Nail Art Studio',  'Specijalizovani salon za nokte',                    'Zmaj Jovina 3, Subotica',         '09:00-17:00', '024-567-8901', 4.3);

-- ----------------------------
-- Usluge
-- ----------------------------
INSERT INTO service (idService, name, price, duration, salonId, category, is_active) VALUES
(1,  'Sisanje zene',       1800, 60,  1, 'frizerske',  1),
(2,  'Bojenje kose',       4500, 120, 1, 'frizerske',  1),
(3,  'Feniranje',          1200, 45,  1, 'frizerske',  1),
(4,  'Pramenovi',          5500, 150, 1, 'frizerske',  1),
(5,  'Ciscenje lica',      2500, 60,  2, 'kozmetičke', 1),
(6,  'Lifting tretman',    4000, 90,  2, 'kozmetičke', 1),
(7,  'Depilacija noge',    1500, 45,  2, 'kozmetičke', 1),
(8,  'Sisanje musko',      1200, 30,  3, 'frizerske',  1),
(9,  'Brijanje',           800,  20,  3, 'frizerske',  1),
(10, 'Sisanje + brijanje', 1800, 45,  3, 'frizerske',  1),
(11, 'Masaza ledja',       3000, 60,  4, 'wellness',   1),
(12, 'Masaza celog tela',  5000, 90,  4, 'wellness',   1),
(13, 'Aromaterapija',      4000, 75,  4, 'wellness',   1),
(14, 'Manikir',            1200, 45,  5, 'kozmetičke', 1),
(15, 'Pedikir',            1500, 60,  5, 'kozmetičke', 1),
(16, 'Gel lak',            2000, 60,  5, 'kozmetičke', 1);

-- ----------------------------
-- Vlasnici (legacy useri 7, 8, 9)
-- ----------------------------
INSERT INTO owner (userId, salonId, verified) VALUES
(7, 1, 1),
(8, 3, 1),
(9, 5, 0);

-- ----------------------------
-- Osoblje (legacy useri 10, 11, 12)
-- ----------------------------
INSERT INTO staff (staffId, userId, salonId, position) VALUES
(1, 10, 1, 'Frizer'),
(2, 11, 1, 'Frizer'),
(3, 12, 3, 'Berberin'),
(4, 1,  2, 'Kozmeticar'),
(5, 2,  4, 'Masazer');

-- ----------------------------
-- Termini (klijenti su legacy useri 13 i 14)
-- ----------------------------
INSERT INTO appointment (appointmentId, userId, staffId, serviceId, dateTime, status, google_event_id) VALUES
(1,  13, 1, 1,  '2026-03-01 10:00:00', 1, NULL),
(2,  14, 2, 2,  '2026-03-02 11:00:00', 1, NULL),
(3,  13, 3, 8,  '2026-03-03 12:00:00', 1, NULL),
(4,  14, 4, 5,  '2026-03-04 13:00:00', 1, NULL),
(5,  13, 5, 11, '2026-03-05 14:00:00', 1, NULL),
(6,  14, 1, 3,  '2026-03-06 09:00:00', 1, NULL),
(7,  13, 2, 4,  '2026-03-07 10:30:00', 1, NULL),
(8,  14, 3, 9,  '2026-03-08 11:30:00', 1, NULL),
(9,  13, 4, 6,  '2026-03-09 12:30:00', 0, NULL),
(10, 14, 5, 12, '2026-03-10 15:00:00', 0, NULL),
(11, 13, 1, 1,  '2026-03-20 10:00:00', 0, NULL),
(12, 14, 2, 2,  '2026-03-21 11:00:00', 0, NULL),
(13, 13, 3, 8,  '2026-03-22 12:00:00', 0, NULL);

-- ----------------------------
-- Recenzije
-- ----------------------------
INSERT INTO review (reviewId, userId, salonId, rating, comment, createdAt) VALUES
(1, 13, 1, 5, 'Odlican salon, preporucujem svima!',           '2026-03-02 10:00:00'),
(2, 14, 1, 4, 'Vrlo profesionalni, malo duze cekanje.',       '2026-03-03 11:00:00'),
(3, 13, 3, 5, 'Majstor svog posla, uvek zadovoljna.',         '2026-03-04 12:00:00'),
(4, 14, 2, 4, 'Lepo udjen prostor, ljubazno osoblje.',        '2026-03-05 13:00:00'),
(5, 13, 4, 5, 'Fantasticna masaza, svakako se vracam!',       '2026-03-06 14:00:00'),
(6, 14, 4, 3, 'Dobra usluga ali cena malo visoka.',           '2026-03-07 15:00:00'),
(7, 13, 5, 4, 'Gel lak izdrzi dugo, zadovoljna kvalitetom.',  '2026-03-08 16:00:00'),
(8, 14, 3, 5, 'Brzo i kvalitetno, definitivno preporucujem.', '2026-03-09 17:00:00');

-- ----------------------------
-- Notifikacije
-- ----------------------------
INSERT INTO notification (notificationId, appointmentId, userId, message, sendAt, type) VALUES
(1,  1,  13, 'Vas termin je zakazan za 01.03.2026. u 10:00.', '2026-02-28 10:00:00', 1),
(2,  2,  14, 'Vas termin je zakazan za 02.03.2026. u 11:00.', '2026-03-01 10:00:00', 1),
(3,  3,  13, 'Podsetnik: termin sutra u 12:00.',              '2026-03-02 12:00:00', 2),
(4,  4,  14, 'Podsetnik: termin sutra u 13:00.',              '2026-03-03 13:00:00', 2),
(5,  5,  13, 'Vas termin je otkazan.',                        '2026-03-04 14:00:00', 3),
(6,  6,  14, 'Podsetnik: termin sutra u 09:00.',              '2026-03-05 09:00:00', 2),
(7,  11, 13, 'Vas termin je zakazan za 20.03.2026. u 10:00.', '2026-03-19 10:00:00', 1),
(8,  12, 14, 'Vas termin je zakazan za 21.03.2026. u 11:00.', '2026-03-20 10:00:00', 1);