-- MySQL dump 10.13  Distrib 8.0.41, for Win64 (x86_64)
--
-- Host: localhost    Database: cms
-- ------------------------------------------------------
-- Server version	8.0.40

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `action_logs`
--

DROP TABLE IF EXISTS `action_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `action_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `username` varchar(255) NOT NULL,
  `role` varchar(50) NOT NULL,
  `action_type` varchar(50) NOT NULL,
  `module` varchar(50) NOT NULL,
  `details` text NOT NULL,
  `created_at` datetime DEFAULT (now()),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `action_logs`
--

LOCK TABLES `action_logs` WRITE;
/*!40000 ALTER TABLE `action_logs` DISABLE KEYS */;
INSERT INTO `action_logs` VALUES (1,19,'2_FOD','scme','CREATE','ECC','Recorded unit item state in TrackUnitItems for Item: \'Bag Sleeping MK-IV\', Division: 19_DOU','2026-08-03 12:34:21'),(2,19,'2_FOD','scme','CREATE','FOD Stock','Added FOD Stock: Voucher SCME_01, Qty 50, Type RES','2026-08-03 12:50:47'),(3,19,'2_FOD','scme','CREATE','ECC','Recorded unit item state in TrackUnitItems for Item: \'Sun Screen Lotion\', Division: 28_DOU','2026-08-03 12:51:44'),(4,19,'2_FOD','scme','CREATE','FOD Stock','Added FOD Stock: Voucher ECC_01, Qty 700, Type RES','2026-08-03 13:00:17'),(5,19,'2_FOD','scme','CREATE','ECC','Recorded unit item state in TrackUnitItems for Item: \'Snow Goggle / Goggle Cortina\', Division: 68_DOU','2026-08-03 13:00:46'),(6,19,'2_FOD','scme','CREATE','FOD Stock','Added FOD Stock: Voucher 800, Qty 1500, Type RES','2026-08-03 13:45:53'),(7,19,'2_FOD','scme','CREATE','ECC','Recorded unit item state in TrackUnitItems for Item: \'Trouser Down\', Division: 99_DOU','2026-08-03 13:46:25'),(8,19,'2_FOD','scme','CREATE','FOD Stock','Added FOD Stock: Voucher VCH-001, Qty 20, Type RES','2026-08-03 13:50:14'),(9,19,'2_FOD','scme','CREATE','ECC','Recorded unit item state in TrackUnitItems for Item: \'Bag Sleeping MK-IV\', Division: 19_DOU','2026-08-03 13:50:44'),(10,19,'2_FOD','scme','CREATE','ECC','Recorded unit item state in TrackUnitItems for Item: \'Bag Sleeping MK-IV\', Division: 19_DOU','2026-08-03 13:59:58'),(11,19,'2_FOD','scme','CREATE','FOD Stock','Added FOD Stock: Voucher SCME_01, Qty 22, Type RES','2026-08-03 14:16:17'),(12,19,'2_FOD','scme','CREATE','ECC','Recorded unit item state in TrackUnitItems for Item: \'Altimeter\', Division: 19_DOU','2026-08-03 14:16:43'),(13,19,'2_FOD','scme','CREATE','ECC','Recorded unit item state in TrackUnitItems for Item: \'Altimeter\', Division: 19_DOU','2026-08-03 14:17:40'),(14,19,'2_FOD','scme','CREATE','ECC','Recorded unit item state in TrackUnitItems for Item: \'Altimeter\', Division: 19_DOU','2026-08-03 15:02:07'),(15,19,'2_FOD','scme','CREATE','FOD Stock','Added FOD Stock: Voucher SCME_01, Qty 10, Type RES','2026-08-03 15:19:22'),(16,19,'2_FOD','scme','CREATE','ECC','Recorded unit item state in TrackUnitItems for Item: \'Bag Sleeping MK-IV\', Division: 19_DOU','2026-08-03 15:19:41'),(17,19,'2_FOD','scme','CREATE','ECC','Recorded unit item state in TrackUnitItems for Item: \'Bag Sleeping MK-IV\', Division: 19_DOU','2026-08-03 15:20:24'),(18,19,'2_FOD','scme','CREATE','FOD Stock','Added FOD Stock: Voucher 6768, Qty 20, Type RES','2026-08-03 15:20:47'),(19,19,'2_FOD','scme','CREATE','ECC','Recorded unit item state in TrackUnitItems for Item: \'Altimeter\', Division: 19_DOU','2026-08-03 15:21:22');
/*!40000 ALTER TABLE `action_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `alembic_version`
--

DROP TABLE IF EXISTS `alembic_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alembic_version`
--

LOCK TABLES `alembic_version` WRITE;
/*!40000 ALTER TABLE `alembic_version` DISABLE KEYS */;
INSERT INTO `alembic_version` VALUES ('4c35deb1ea1b');
/*!40000 ALTER TABLE `alembic_version` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `army_personnel`
--

DROP TABLE IF EXISTS `army_personnel`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `army_personnel` (
  `id` int NOT NULL AUTO_INCREMENT,
  `army_number` varchar(50) NOT NULL,
  `name` varchar(150) NOT NULL,
  `rank` varchar(50) NOT NULL,
  `company` varchar(100) DEFAULT NULL,
  `unit_name` varchar(100) DEFAULT NULL,
  `created_at` datetime DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_army_personnel_army_number` (`army_number`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `army_personnel`
--

LOCK TABLES `army_personnel` WRITE;
/*!40000 ALTER TABLE `army_personnel` DISABLE KEYS */;
INSERT INTO `army_personnel` VALUES (6,'JC67837','PRAVEEN KUMAR','Naib Subedar','3 COY','UNIT_11','2026-08-03 12:14:30');
/*!40000 ALTER TABLE `army_personnel` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `divs`
--

DROP TABLE IF EXISTS `divs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `divs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `authorized_strength` int DEFAULT NULL,
  `posted_strength` int DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `divs`
--

LOCK TABLES `divs` WRITE;
/*!40000 ALTER TABLE `divs` DISABLE KEYS */;
INSERT INTO `divs` VALUES (3,'28_DOU',700,850),(4,'19_DOU',1300,1200),(8,'68_DOU',1200,1000),(9,'57_DOU',700,500),(40,'99_DOU',700,600);
/*!40000 ALTER TABLE `divs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `ecc_scme_items`
--

DROP TABLE IF EXISTS `ecc_scme_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ecc_scme_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `item_name` varchar(255) NOT NULL,
  `category` varchar(50) NOT NULL,
  `type` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=65 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ecc_scme_items`
--

LOCK TABLES `ecc_scme_items` WRITE;
/*!40000 ALTER TABLE `ecc_scme_items` DISABLE KEYS */;
INSERT INTO `ecc_scme_items` VALUES (1,'Bag Sleeping MK-IV','CAT-I','ecc'),(2,'Coat ECC','CAT-I','ecc'),(3,'Socks Men\'s Woollen','CAT-I','ecc'),(4,'Trouser ECC / Trouser BD Serge','CAT-I','ecc'),(5,'Gloves Leather','CAT-I','ecc'),(6,'Cap Balaclava Snow','CAT-I','ecc'),(7,'Goggles GS MK-II','CAT-I','ecc'),(8,'Vest Thermal','CAT-I','ecc'),(9,'Under Pant Woollen','CAT-I','ecc'),(10,'Sun Screen Lotion','CAT-I','ecc'),(11,'Snow Boot / Boot RI','CAT-II','ecc'),(12,'Rucksack','CAT-II','ecc'),(13,'Gaiters','CAT-II','ecc'),(14,'Carrier Man Pack','CAT-II','ecc'),(15,'Hot Water Bottle Rubber','CAT-II','ecc'),(16,'Camp Mattress Outdoor','CAT-II','ecc'),(17,'Rescue Bag','CAT-II','ecc'),(18,'ISHD','CAT-II','ecc'),(19,'Rod Avalanche & Marker Trail','CAT-II','ecc'),(20,'Winter Overall','CAT-II','ecc'),(21,'Mattress Kapok MK-II Complete','CAT-II','ecc'),(22,'Tank Mule High Altitude','CAT-II','ecc'),(23,'Tent Arctic Small MK-II','CAT-II','ecc'),(24,'Tent Arctic Med MK-II','CAT-II','ecc'),(25,'Tent Arctic Large MK-II','CAT-II','ecc'),(26,'Tent Arctic Med Medical MK-II','CAT-II','ecc'),(27,'Face Mask','CAT-II','ecc'),(28,'Head Cap Woollen / Head Cap Spl','CAT-I','scme'),(29,'Socks Woollen Two Layer','CAT-I','scme'),(30,'Bag Water Proof','CAT-I','scme'),(31,'Drawers Cold Weather','CAT-I','scme'),(32,'Under Shirt Cold Weather','CAT-I','scme'),(33,'Sleeping Bag Spl','CAT-I','scme'),(34,'Mask Face (Balaclava)','CAT-I','scme'),(35,'Boot Multipurpose','CAT-I','scme'),(36,'Snow Goggle / Goggle Cortina','CAT-I','scme'),(37,'Jacket Down','CAT-I','scme'),(38,'Trouser Down','CAT-I','scme'),(39,'Mattress (Glacier)','CAT-I','scme'),(40,'Rucksack','CAT-I','scme'),(41,'Gloves inner and Gloves outer as a set','CAT-I','scme'),(42,'Professional Modular Gloves','CAT-I','scme'),(43,'Jacket Wind Cheater / Over Garment Blouse','CAT-I','scme'),(44,'Over Garment Trouser','CAT-I','scme'),(45,'ECWCS','CAT-I','scme'),(46,'Summer Suit for Super High Altitude Areas','CAT-I','scme'),(47,'Karabiner \'P\' Type','CAT-II','scme'),(48,'Karabiner \'S\' Type','CAT-II','scme'),(49,'Pulleys','CAT-II','scme'),(50,'Tent HA 10-12 Men','CAT-II','scme'),(51,'Spare Glasses Goggle','CAT-II','scme'),(52,'Rope Climbing Glacier','CAT-II','scme'),(53,'Thermal Insoles','CAT-II','scme'),(54,'Under Slung Cargo Nets','CAT-II','scme'),(55,'Knife All Purposes','CAT-II','scme'),(56,'Rock Piton (Horizontal) / Rock Piton (Vertical)','CAT-II','scme'),(57,'Fire Star Refill 4 Kg','CAT-II','scme'),(58,'Fire Star Cooker','CAT-II','scme'),(59,'Fire Star Refill Tube 150 gm','CAT-II','scme'),(60,'Oxygen Cylinder','CAT-II','scme'),(61,'Altimeter','CAT-II','scme'),(62,'Ladder Crevasse — Size 8-16 (20%), Size 12-24 (40%), Size 16-32 (40%)','CAT-II','scme'),(63,'Sunreal Blanket','CAT-II','scme'),(64,'Boot Crampons','CAT-II','scme');
/*!40000 ALTER TABLE `ecc_scme_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `fod_stock_table`
--

DROP TABLE IF EXISTS `fod_stock_table`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `fod_stock_table` (
  `id` int NOT NULL AUTO_INCREMENT,
  `voucher_no` varchar(100) NOT NULL,
  `category` varchar(50) NOT NULL,
  `item_id` int NOT NULL,
  `quantity` int NOT NULL,
  `source` varchar(20) NOT NULL,
  `pws` int NOT NULL,
  `ser` int NOT NULL,
  `type` varchar(20) NOT NULL,
  `created_at` datetime DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `item_id` (`item_id`),
  CONSTRAINT `fod_stock_table_ibfk_1` FOREIGN KEY (`item_id`) REFERENCES `ecc_scme_items` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `fod_stock_table`
--

LOCK TABLES `fod_stock_table` WRITE;
/*!40000 ALTER TABLE `fod_stock_table` DISABLE KEYS */;
INSERT INTO `fod_stock_table` VALUES (1,'SCME_01','CAT-II',61,4,'Depo',1,3,'RES','2026-08-03 14:16:17'),(2,'SCME_01','CAT-I',1,2,'Depo',1,1,'RES','2026-08-03 15:19:22'),(3,'6768','CAT-II',61,20,'Depo',10,10,'RES','2026-08-03 15:20:47');
/*!40000 ALTER TABLE `fod_stock_table` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `item_auth`
--

DROP TABLE IF EXISTS `item_auth`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `item_auth` (
  `id` int NOT NULL AUTO_INCREMENT,
  `unit_name` varchar(255) NOT NULL,
  `item_id` int NOT NULL,
  `auth` int NOT NULL,
  `created_at` datetime DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `item_id` (`item_id`),
  KEY `ix_item_auth_unit_name` (`unit_name`),
  CONSTRAINT `item_auth_ibfk_1` FOREIGN KEY (`item_id`) REFERENCES `ecc_scme_items` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `item_auth`
--

LOCK TABLES `item_auth` WRITE;
/*!40000 ALTER TABLE `item_auth` DISABLE KEYS */;
INSERT INTO `item_auth` VALUES (1,'19_DOU',1,400,'2026-08-03 13:50:44'),(2,'19_DOU',61,100,'2026-08-03 14:16:43');
/*!40000 ALTER TABLE `item_auth` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `item_request_table`
--

DROP TABLE IF EXISTS `item_request_table`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `item_request_table` (
  `id` int NOT NULL AUTO_INCREMENT,
  `item_id` int NOT NULL,
  `requested_by` int NOT NULL,
  `admin_id` int NOT NULL,
  `quantity` int NOT NULL,
  `reason` varchar(100) DEFAULT NULL,
  `priority` varchar(20) DEFAULT NULL,
  `remarks` varchar(255) DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `created_at` datetime DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `item_id` (`item_id`),
  CONSTRAINT `item_request_table_ibfk_1` FOREIGN KEY (`item_id`) REFERENCES `our_items` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `item_request_table`
--

LOCK TABLES `item_request_table` WRITE;
/*!40000 ALTER TABLE `item_request_table` DISABLE KEYS */;
/*!40000 ALTER TABLE `item_request_table` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `login_users`
--

DROP TABLE IF EXISTS `login_users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `login_users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` varchar(50) NOT NULL,
  `org_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `org_id` (`org_id`),
  CONSTRAINT `login_users_ibfk_1` FOREIGN KEY (`org_id`) REFERENCES `org_ladder` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `login_users`
--

LOCK TABLES `login_users` WRITE;
/*!40000 ALTER TABLE `login_users` DISABLE KEYS */;
INSERT INTO `login_users` VALUES (1,'ORD','123','super_admin',1),(3,'19_DOU','123','division_admin',3),(4,'28_DOU','123','division_admin',4),(5,'KFSR','123','division_admin',5),(7,'UNIT_11','123','unit',7),(8,'UNIT_12','123','unit',8),(9,'UNIT_14','123','unit',9),(10,'UNIT_15','123','unit',10),(11,'UNIT_16','123','unit',11),(12,'UNIT_20','123','unit',12),(13,'UNIT_21','123','unit',13),(14,'UNIT_22','123','unit',14),(15,'UNIT_25','123','unit',15),(16,'68_DOU','123','division_admin',16),(17,'57_DOU','123','division_admin',17),(18,'UNIT_50','123','unit',18),(19,'2_FOD','123','scme',20),(20,'77_DOU','123','division_admin',21),(21,'99_DOU','123','division_admin',22),(22,'UNIT_99','123','unit',23),(23,'UNIT_60','123','unit',24),(24,'UNIT_66','123','unit',25);
/*!40000 ALTER TABLE `login_users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `org_ladder`
--

DROP TABLE IF EXISTS `org_ladder`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `org_ladder` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `type` varchar(20) NOT NULL,
  `parent_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `parent_id` (`parent_id`),
  CONSTRAINT `org_ladder_ibfk_1` FOREIGN KEY (`parent_id`) REFERENCES `org_ladder` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `org_ladder`
--

LOCK TABLES `org_ladder` WRITE;
/*!40000 ALTER TABLE `org_ladder` DISABLE KEYS */;
INSERT INTO `org_ladder` VALUES (1,'ORD','ROOT',NULL),(3,'19_DOU','division',1),(4,'28_DOU','division',1),(5,'KFSR','division',1),(6,'2 FOD','division',1),(7,'UNIT_11','unit',3),(8,'UNIT_12','unit',3),(9,'UNIT_14','unit',3),(10,'UNIT_15','unit',3),(11,'UNIT_16','unit',3),(12,'UNIT_20','unit',4),(13,'UNIT_21','unit',4),(14,'UNIT_22','unit',4),(15,'UNIT_25','unit',4),(16,'68_DOU','division',1),(17,'57_DOU','division',1),(18,'UNIT_50','unit',17),(20,'2_FOD','division',1),(21,'77_DOU','division',1),(22,'99_DOU','division',1),(23,'UNIT_99','unit',22),(24,'UNIT_60','unit',16),(25,'UNIT_66','unit',16);
/*!40000 ALTER TABLE `org_ladder` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `our_items`
--

DROP TABLE IF EXISTS `our_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `our_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `item_name` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `our_items`
--

LOCK TABLES `our_items` WRITE;
/*!40000 ALTER TABLE `our_items` DISABLE KEYS */;
/*!40000 ALTER TABLE `our_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `scme_issued_items`
--

DROP TABLE IF EXISTS `scme_issued_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `scme_issued_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `unit_name` varchar(255) NOT NULL,
  `item_id` int NOT NULL,
  `scale` varchar(10) NOT NULL,
  `a_u` varchar(10) NOT NULL,
  `held` int NOT NULL,
  `deficiency` int NOT NULL,
  `created_at` datetime DEFAULT (now()),
  `unit_authorized` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `item_id` (`item_id`),
  CONSTRAINT `scme_issued_items_ibfk_1` FOREIGN KEY (`item_id`) REFERENCES `ecc_scme_items` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `scme_issued_items`
--

LOCK TABLES `scme_issued_items` WRITE;
/*!40000 ALTER TABLE `scme_issued_items` DISABLE KEYS */;
INSERT INTO `scme_issued_items` VALUES (1,'UNIT_11',61,'1 PER INDL','Nos',0,10,'2026-08-03 15:25:28',10),(2,'UNIT_12',1,'1 PER INDL','Nos',0,10,'2026-08-03 15:25:46',10);
/*!40000 ALTER TABLE `scme_issued_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `track_unit_items`
--

DROP TABLE IF EXISTS `track_unit_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `track_unit_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `unit_name` varchar(255) NOT NULL,
  `item_id` int NOT NULL,
  `scale` varchar(255) DEFAULT NULL,
  `auth` int NOT NULL,
  `held` int NOT NULL,
  `issued_at` datetime DEFAULT (now()),
  `ser` int NOT NULL DEFAULT '0',
  `pws` int NOT NULL DEFAULT '0',
  `add_knd` int NOT NULL DEFAULT '0',
  `add_tn_model` int NOT NULL DEFAULT '0',
  `add_n_area_otg` int NOT NULL DEFAULT '0',
  `add_idt_ict` int NOT NULL DEFAULT '0',
  `available_res` int NOT NULL DEFAULT '0',
  `available_ser` int NOT NULL DEFAULT '0',
  `available_pws` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `item_id` (`item_id`),
  KEY `ix_track_unit_items_unit_name` (`unit_name`),
  CONSTRAINT `track_unit_items_ibfk_1` FOREIGN KEY (`item_id`) REFERENCES `ecc_scme_items` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `track_unit_items`
--

LOCK TABLES `track_unit_items` WRITE;
/*!40000 ALTER TABLE `track_unit_items` DISABLE KEYS */;
INSERT INTO `track_unit_items` VALUES (1,'19_DOU',1,'1 PER INDL',400,10,'2026-08-03 09:50:24',1,1,0,0,0,0,8,3,3),(2,'19_DOU',61,'1 PER INDL',100,12,'2026-08-03 09:51:22',1,1,0,0,0,0,10,4,4),(3,'UNIT_11',61,'1 PER INDL',10,2,'2026-08-03 09:55:28',0,0,0,0,0,0,2,0,1),(4,'UNIT_12',1,'1 PER INDL',10,2,'2026-08-03 09:55:46',0,0,0,0,0,0,2,1,1);
/*!40000 ALTER TABLE `track_unit_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `transactions`
--

DROP TABLE IF EXISTS `transactions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `transactions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `issued_by` varchar(255) NOT NULL,
  `received_by` varchar(255) NOT NULL,
  `item_id` int NOT NULL,
  `ser` int NOT NULL,
  `pws` int NOT NULL,
  `scale` varchar(255) DEFAULT NULL,
  `remarks` varchar(255) DEFAULT NULL,
  `timestamp` datetime DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `item_id` (`item_id`),
  KEY `ix_transactions_received_by` (`received_by`),
  CONSTRAINT `transactions_ibfk_1` FOREIGN KEY (`item_id`) REFERENCES `ecc_scme_items` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `transactions`
--

LOCK TABLES `transactions` WRITE;
/*!40000 ALTER TABLE `transactions` DISABLE KEYS */;
INSERT INTO `transactions` VALUES (1,'2_FOD','19_DOU',1,1,1,'1 PER INDL',NULL,'2026-07-03 09:49:41'),(2,'2_FOD','19_DOU',1,3,3,'1 PER INDL',NULL,'2026-08-03 09:50:24'),(3,'2_FOD','19_DOU',61,5,5,'1 PER INDL',NULL,'2026-08-03 09:51:22'),(4,'19_DOU','UNIT_11',61,1,1,NULL,NULL,'2026-08-03 09:55:28'),(5,'19_DOU','UNIT_12',1,1,1,NULL,NULL,'2026-08-03 09:55:46'),(6,'UNIT_11','JC67837',61,1,0,NULL,'WE ARE GIVING AN ALTIMETER TO YOU','2026-08-03 15:26:37');
/*!40000 ALTER TABLE `transactions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `unit_strength`
--

DROP TABLE IF EXISTS `unit_strength`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `unit_strength` (
  `id` int NOT NULL AUTO_INCREMENT,
  `unit_name` varchar(255) NOT NULL,
  `posted_strength` int NOT NULL,
  `authorized_strength` int DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `unit_strength`
--

LOCK TABLES `unit_strength` WRITE;
/*!40000 ALTER TABLE `unit_strength` DISABLE KEYS */;
INSERT INTO `unit_strength` VALUES (1,'UNIT_11',600,0),(2,'UNIT_12',500,0),(3,'UNIT_14',400,0),(4,'UNIT_15',900,0),(5,'UNIT_16',800,0),(6,'UNIT_20',700,700),(7,'UNIT_21',0,400),(8,'UNIT_25',0,500),(9,'UNIT_22',0,500),(10,'UNIT_22',0,0),(11,'UNIT_20',700,700),(12,'UNIT_20',700,700),(14,'UNIT_99',0,0),(15,'UNIT_60',0,0),(16,'UNIT_66',0,0);
/*!40000 ALTER TABLE `unit_strength` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `unit_tps_stock`
--

DROP TABLE IF EXISTS `unit_tps_stock`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `unit_tps_stock` (
  `id` int NOT NULL AUTO_INCREMENT,
  `unit_name` varchar(100) NOT NULL,
  `item_id` int NOT NULL,
  `army_number` varchar(50) DEFAULT NULL,
  `tps_ser` int NOT NULL,
  `tps_pws` int NOT NULL,
  `updated_at` datetime DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `item_id` (`item_id`),
  KEY `army_number` (`army_number`),
  CONSTRAINT `unit_tps_stock_ibfk_1` FOREIGN KEY (`item_id`) REFERENCES `ecc_scme_items` (`id`),
  CONSTRAINT `unit_tps_stock_ibfk_2` FOREIGN KEY (`army_number`) REFERENCES `army_personnel` (`army_number`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `unit_tps_stock`
--

LOCK TABLES `unit_tps_stock` WRITE;
/*!40000 ALTER TABLE `unit_tps_stock` DISABLE KEYS */;
INSERT INTO `unit_tps_stock` VALUES (1,'UNIT_11',61,'JC67837',1,0,'2026-08-03 15:26:37');
/*!40000 ALTER TABLE `unit_tps_stock` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` varchar(50) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-03 15:35:43
