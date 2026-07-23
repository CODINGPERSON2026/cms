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
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `action_logs`
--

LOCK TABLES `action_logs` WRITE;
/*!40000 ALTER TABLE `action_logs` DISABLE KEYS */;
INSERT INTO `action_logs` VALUES (1,1,'scme','scme','CREATE','SCME','Recorded new SCME item: \'Altimeter\' (Unit: 19 INF DIV, Unit Auth: 500, Held: 300)','2026-07-10 11:26:25'),(2,1,'scme','scme','CREATE','SCME','Recorded new SCME item: \'Hammer Piton\' (Unit: 28 INF DIV, Unit Auth: 600, Held: 100)','2026-07-10 11:26:42'),(3,1,'scme','scme','CREATE','SCME','Recorded new SCME item: \'Thermal Insoles\' (Unit: VFSR, Unit Auth: 600, Held: 300)','2026-07-10 11:26:59'),(4,1,'scme','scme','CREATE','SCME','Recorded new SCME item: \'Avalanche Air Bag with Backpack, Flask & Snow Shoe Flak (Trigger)\' (Unit: 19 INF DIV, Unit Auth: 100, Held: 80)','2026-07-10 11:27:22'),(5,1,'scme','scme','UPDATE','SCME','Issued 100 of \'Hammer Piton\' for unit 28 INF DIV. (New Held: 200)','2026-07-10 11:27:47'),(6,1,'scme','scme','CREATE','ECC','Recorded monthly state for Item: \'Rucksack\', Division: 19 INF DIV','2026-07-14 15:44:36'),(7,1,'scme','scme','CREATE','ECC','Recorded monthly state for Item: \'Sleeping Bag Spl\', Division: 28 MOU','2026-07-14 16:00:38'),(8,2,'scme','scme','DELETE','ECC','Deleted ECC monthly state for Item: \'Bag Sleeping MK-IV\', Division: 19 INF DOU','2026-07-22 11:55:50');
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
-- Table structure for table `ecc_monthly_state`
--

DROP TABLE IF EXISTS `ecc_monthly_state`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ecc_monthly_state` (
  `id` int NOT NULL AUTO_INCREMENT,
  `item_id` int NOT NULL,
  `scale` varchar(100) DEFAULT NULL,
  `auth_auth` int DEFAULT NULL,
  `auth_res` int DEFAULT NULL,
  `auth_total` int DEFAULT NULL,
  `bbf_division` varchar(255) NOT NULL,
  `bbf_ser` int DEFAULT NULL,
  `bbf_pws` int DEFAULT NULL,
  `bbf_total` int DEFAULT '0',
  `bbf_comd` int DEFAULT NULL,
  `bbf_ihq` int DEFAULT NULL,
  `recd_ser` int DEFAULT NULL,
  `recd_pws` int DEFAULT NULL,
  `recd_total` int DEFAULT '0',
  `issd_ser` int DEFAULT NULL,
  `issd_pws` int DEFAULT NULL,
  `issd_total` int DEFAULT '0',
  `stock_ser` int DEFAULT NULL,
  `stock_pws` int DEFAULT NULL,
  `stock_total` int DEFAULT '0',
  `stock_comd` int DEFAULT NULL,
  `stock_ihq` int DEFAULT NULL,
  `add_knd` int DEFAULT NULL,
  `add_tn_model` int DEFAULT NULL,
  `add_n_area_otg` int DEFAULT NULL,
  `add_idt_ict` int DEFAULT NULL,
  `add_remarks_ro_bal` int DEFAULT '0',
  `tps` int DEFAULT NULL,
  `created_at` datetime DEFAULT (now()),
  `deficiency` int NOT NULL DEFAULT '0',
  `unit_auth` int DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `item_id` (`item_id`),
  CONSTRAINT `ecc_monthly_state_ibfk_1` FOREIGN KEY (`item_id`) REFERENCES `ecc_scme_items` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=37 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ecc_monthly_state`
--

LOCK TABLES `ecc_monthly_state` WRITE;
/*!40000 ALTER TABLE `ecc_monthly_state` DISABLE KEYS */;
INSERT INTO `ecc_monthly_state` VALUES (2,1,'Scale 2',147,27,174,'2 FOD',100,20,120,5,4,14,6,20,5,4,9,109,22,131,4,5,9,7,0,7,8,19,'2026-07-14 23:35:47',43,174),(3,1,'Scale 2',119,2,121,'28_DOU',106,15,121,4,3,12,8,20,14,7,40,104,16,120,2,1,6,7,7,3,17,24,'2026-07-14 23:35:47',20,140),(4,2,'Scale 2',112,20,132,'19 INF DOU',90,13,103,3,2,15,6,21,17,2,19,88,17,105,0,4,15,10,6,9,17,43,'2026-07-14 23:35:47',27,132),(5,2,'Scale 3',201,36,237,'2 FOD',95,11,106,3,0,8,2,10,19,2,21,84,11,95,5,1,4,3,2,0,12,59,'2026-07-14 23:35:47',142,237),(6,2,'Scale 1',176,9,185,'28_DOU',134,18,152,4,1,11,7,18,13,8,44,132,17,149,0,4,17,0,5,15,13,90,'2026-07-14 23:35:47',59,208),(7,3,'Scale 3',113,20,133,'19 INF DOU',97,11,108,2,2,6,6,12,13,2,15,90,15,105,3,4,19,2,4,15,10,52,'2026-07-14 23:35:47',28,133),(8,3,'Scale 1',86,16,102,'2 FOD',96,23,119,5,0,19,8,27,16,3,19,99,28,127,3,0,17,10,7,0,18,27,'2026-07-14 23:35:47',-25,102),(9,3,'Scale 2',130,24,154,'28 INF DOU',143,17,160,4,3,10,6,16,8,3,11,145,20,165,5,1,13,17,5,10,16,20,'2026-07-14 23:35:47',-11,154),(10,4,'Scale 3',99,18,117,'19 INF DOU',126,11,137,4,2,17,3,20,20,7,27,123,7,130,2,0,8,13,7,7,12,52,'2026-07-14 23:35:47',-13,117),(11,4,'Scale 3',102,18,120,'2 FOD',111,18,129,5,5,13,5,18,5,2,7,119,21,140,0,0,16,12,0,9,14,70,'2026-07-14 23:35:47',-20,120),(12,4,'Scale 3',141,16,157,'28_DOU',111,13,124,3,3,14,8,22,26,3,29,117,20,137,2,5,9,17,6,11,10,84,'2026-07-14 23:35:47',40,167),(13,5,'Scale 2',182,33,215,'19 INF DOU',149,21,170,5,5,19,8,27,6,8,14,162,21,183,5,5,20,11,8,13,10,54,'2026-07-14 23:35:47',32,215),(14,5,'Scale 2',161,29,190,'2 FOD',140,27,167,5,4,6,7,13,8,4,12,138,30,168,2,5,19,5,0,4,11,10,'2026-07-14 23:35:47',22,190),(15,5,'Scale 2',324,58,382,'28_DOU',119,25,144,1,2,17,7,24,12,3,15,124,29,153,2,0,14,12,2,9,4,54,'2026-07-14 23:35:47',229,382),(16,6,'Scale 3',75,14,89,'19 INF DOU',83,30,113,0,4,19,7,26,6,7,13,96,30,126,4,4,12,3,9,8,17,77,'2026-07-14 23:35:47',-37,89),(17,6,'Scale 1',123,22,145,'2 FOD',100,28,128,5,4,6,3,9,17,6,23,89,25,114,1,2,13,15,2,5,18,61,'2026-07-14 23:35:47',31,145),(18,6,'Scale 2',161,29,190,'28_DOU',127,27,154,3,5,7,2,9,14,5,19,120,24,144,5,0,11,19,1,10,12,91,'2026-07-14 23:35:47',46,190),(19,11,'Scale 1',137,25,162,'19 INF DOU',108,22,130,2,0,8,3,11,17,6,23,99,19,118,5,0,12,0,10,7,12,81,'2026-07-14 23:35:47',44,162),(20,11,'Scale 1',120,22,142,'2 FOD',106,22,128,0,3,10,5,15,6,5,11,110,22,132,2,1,11,7,9,1,11,85,'2026-07-14 23:35:47',10,142),(21,11,'Scale 3',107,20,127,'28_DOU',87,29,116,2,3,5,2,7,19,6,25,73,25,98,3,2,2,12,8,8,16,29,'2026-07-14 23:35:47',29,127),(22,12,'Scale 3',172,31,203,'19 INF DOU',148,10,158,2,2,10,2,12,6,4,10,152,8,160,3,5,4,6,5,5,15,45,'2026-07-14 23:35:47',43,203),(23,12,'Scale 3',96,18,114,'2 FOD',120,14,134,3,0,6,6,12,16,4,20,110,16,126,4,1,13,20,1,8,20,67,'2026-07-14 23:35:47',-12,114),(24,12,'Scale 3',118,21,139,'28_DOU',111,13,124,3,3,5,5,10,18,7,25,98,11,109,3,1,16,5,3,14,12,35,'2026-07-14 23:35:47',30,139),(25,13,'Scale 1',122,22,144,'19 INF DOU',114,25,139,4,1,11,7,18,14,6,20,111,26,137,0,5,8,13,8,1,5,77,'2026-07-14 23:35:47',7,144),(26,13,'Scale 1',91,17,108,'2 FOD',117,24,141,0,0,6,7,13,15,4,19,108,27,135,0,3,4,20,10,11,6,67,'2026-07-14 23:35:47',-27,108),(27,13,'Scale 3',119,3,122,'28_DOU',109,26,135,5,4,6,6,12,22,5,40,96,29,125,4,2,8,14,0,0,17,45,'2026-07-14 23:35:47',15,140),(28,14,'Scale 2',51,9,60,'19 INF DOU',86,14,100,4,0,19,2,21,18,6,24,87,10,97,1,2,11,6,5,10,7,31,'2026-07-14 23:35:47',-37,60),(29,14,'Scale 1',149,27,176,'2 FOD',121,11,132,1,1,14,2,16,11,6,17,124,7,131,0,4,19,9,6,3,15,49,'2026-07-14 23:35:47',45,176),(30,14,'Scale 3',164,20,184,'28_DOU',142,11,153,3,5,14,6,20,7,3,20,149,14,163,4,4,2,13,1,10,11,24,'2026-07-14 23:35:47',31,194),(31,15,'Scale 1',96,17,113,'19 INF DOU',104,20,124,0,5,16,3,19,8,4,12,112,19,131,3,1,3,1,8,13,2,98,'2026-07-14 23:35:47',-18,113),(32,15,'Scale 2',147,27,174,'2 FOD',101,25,126,4,1,17,2,19,5,7,12,113,20,133,4,0,9,9,4,12,2,74,'2026-07-14 23:35:47',41,174),(33,15,'Scale 1',113,21,134,'28_DOU',97,17,114,3,1,19,7,26,17,3,20,99,21,120,4,5,16,11,10,9,6,26,'2026-07-14 23:35:47',14,134),(34,16,'Scale 3',163,29,192,'19 INF DOU',143,30,173,4,4,5,7,12,8,8,16,140,29,169,5,1,12,14,1,1,7,44,'2026-07-14 23:35:47',23,192),(35,16,'Scale 3',104,19,123,'2 FOD',131,17,148,1,4,17,3,20,11,3,14,137,17,154,5,5,2,15,2,7,4,13,'2026-07-14 23:35:47',-31,123),(36,16,'Scale 1',163,29,192,'28_DOU',139,22,161,1,1,20,3,23,19,6,25,140,19,159,4,4,14,5,9,9,3,16,'2026-07-14 23:35:47',33,192);
/*!40000 ALTER TABLE `ecc_monthly_state` ENABLE KEYS */;
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
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `login_users`
--

LOCK TABLES `login_users` WRITE;
/*!40000 ALTER TABLE `login_users` DISABLE KEYS */;
INSERT INTO `login_users` VALUES (1,'ORD','123','super_admin',1),(2,'scme','123','scme',2),(3,'19_DOU','123','division_admin',3),(4,'28_DOU','123','division_admin',4),(5,'KFSR','123','division_admin',5),(6,'2 FOD','123','division_admin',6),(7,'UNIT_11','123','unit',7),(8,'UNIT_12','123','unit',8),(9,'UNIT_14','123','unit',9),(10,'UNIT_15','123','unit',10),(11,'UNIT_16','123','unit',11),(12,'UNIT_20','123','unit',12),(13,'UNIT_21','123','unit',13),(14,'UNIT_22','123','unit',14),(15,'UNIT_25','123','unit',15),(16,'68_DOU','123','division_admin',16),(17,'57_DOU','123','division_admin',17),(18,'UNIT_50','123','unit',18);
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
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `org_ladder`
--

LOCK TABLES `org_ladder` WRITE;
/*!40000 ALTER TABLE `org_ladder` DISABLE KEYS */;
INSERT INTO `org_ladder` VALUES (1,'ORD','ROOT',NULL),(2,'scme','user',1),(3,'19_DOU','division',1),(4,'28_DOU','division',1),(5,'KFSR','division',1),(6,'2 FOD','division',1),(7,'UNIT_11','unit',3),(8,'UNIT_12','unit',3),(9,'UNIT_14','unit',3),(10,'UNIT_15','unit',3),(11,'UNIT_16','unit',3),(12,'UNIT_20','unit',4),(13,'UNIT_21','unit',4),(14,'UNIT_22','unit',4),(15,'UNIT_25','unit',4),(16,'68_DOU','division',1),(17,'57_DOU','division',1),(18,'UNIT_50','unit',17);
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
) ENGINE=InnoDB AUTO_INCREMENT=39 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `scme_issued_items`
--

LOCK TABLES `scme_issued_items` WRITE;
/*!40000 ALTER TABLE `scme_issued_items` DISABLE KEYS */;
INSERT INTO `scme_issued_items` VALUES (1,'28 INF DOU',54,'2 per indl','Prs',42,171,'2026-07-14 16:28:36',213),(2,'19 INF DOU',54,'1 per indl','Prs',38,191,'2026-07-14 16:28:36',229),(3,'19 INF DOU',64,'Nos','Nos',43,92,'2026-07-14 16:28:36',135),(4,'2 FOD',64,'1 per indl','Prs',128,113,'2026-07-14 16:28:36',241),(5,'19 INF DOU',41,'Prs','Prs',115,21,'2026-07-14 16:28:36',136),(6,'2 FOD',41,'2 per indl','Nos',134,103,'2026-07-14 16:28:36',237),(7,'2 FOD',41,'Prs','Nos',116,67,'2026-07-14 16:28:36',183),(8,'19 INF DOU',39,'Prs','Prs',129,26,'2026-07-14 16:28:36',155),(9,'2 FOD',39,'2 per indl','Prs',123,30,'2026-07-14 16:28:36',153),(10,'19 INF DOU',31,'2 per indl','Nos',82,18,'2026-07-14 16:28:36',100),(11,'2 FOD',52,'1 per indl','Nos',138,72,'2026-07-14 16:28:36',210),(12,'19 INF DOU',52,'2 per indl','Nos',60,81,'2026-07-14 16:28:36',141),(13,'28 INF DOU',52,'2 per indl','Prs',155,0,'2026-07-14 16:28:36',155),(14,'28 INF DOU',45,'Nos','Nos',38,125,'2026-07-14 16:28:36',163),(15,'28 INF DOU',40,'Prs','Prs',63,125,'2026-07-14 16:28:36',188),(16,'19 INF DOU',40,'1 per indl','Nos',113,100,'2026-07-14 16:28:36',213),(17,'28 INF DOU',40,'Prs','Prs',112,97,'2026-07-14 16:28:36',209),(18,'2 FOD',55,'Nos','Prs',163,72,'2026-07-14 16:28:36',235),(19,'28 INF DOU',59,'1 per indl','Prs',181,5,'2026-07-14 16:28:36',186),(20,'2 FOD',59,'Prs','Prs',38,176,'2026-07-14 16:28:36',214),(21,'28 INF DOU',59,'Prs','Prs',135,69,'2026-07-14 16:28:36',204),(22,'19 INF DOU',49,'Prs','Prs',48,37,'2026-07-14 16:28:36',85),(23,'28 INF DOU',49,'Prs','Prs',58,35,'2026-07-14 16:28:36',93),(24,'2 FOD',49,'2 per indl','Prs',130,43,'2026-07-14 16:28:36',173),(25,'2 FOD',33,'Nos','Nos',143,30,'2026-07-14 16:28:36',173),(26,'28 INF DOU',61,'Nos','Prs',36,74,'2026-07-14 16:28:36',110),(27,'2 FOD',32,'Prs','Prs',137,75,'2026-07-14 16:28:36',212),(28,'2 FOD',32,'2 per indl','Nos',207,40,'2026-07-14 16:28:36',247),(29,'28 INF DOU',32,'1 per indl','Nos',40,156,'2026-07-14 16:28:36',196),(30,'UNIT_20',1,'100%','Nos',9,891,'2026-07-22 12:59:03',900),(31,'UNIT_25',2,'100%','Nos',11,0,'2026-07-22 13:30:16',11),(32,'UNIT_22',2,'100%','Nos',11,0,'2026-07-22 13:38:09',11),(33,'UNIT_22',1,'100%','Nos',10,0,'2026-07-22 13:42:53',10),(34,'UNIT_20',2,'100%','Nos',1,0,'2026-07-22 13:44:34',1),(35,'UNIT_20',14,'100%','Nos',10,0,'2026-07-22 13:54:16',10),(36,'UNIT_22',13,'100%','Nos',13,887,'2026-07-22 14:34:07',900),(37,'UNIT_21',13,'100%','Nos',5,15,'2026-07-23 12:18:27',20),(38,'UNIT_20',4,'100%','Nos',10,50,'2026-07-23 12:36:57',60);
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
  `auth` int NOT NULL,
  `held` int NOT NULL,
  `issued_at` datetime DEFAULT (now()),
  `ser` int NOT NULL DEFAULT '0',
  `pws` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `item_id` (`item_id`),
  KEY `ix_track_unit_items_unit_name` (`unit_name`),
  CONSTRAINT `track_unit_items_ibfk_1` FOREIGN KEY (`item_id`) REFERENCES `ecc_scme_items` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `track_unit_items`
--

LOCK TABLES `track_unit_items` WRITE;
/*!40000 ALTER TABLE `track_unit_items` DISABLE KEYS */;
INSERT INTO `track_unit_items` VALUES (1,'UNIT_20',1,900,9,'2026-07-23 05:28:47',5,4),(2,'UNIT_21',5,400,0,'2026-07-22 13:22:10',0,0),(3,'UNIT_25',2,500,11,'2026-07-22 08:07:28',6,5),(4,'UNIT_22',2,500,11,'2026-07-22 08:08:38',8,3),(5,'UNIT_22',1,70,10,'2026-07-22 08:12:53',5,5),(6,'UNIT_20',2,500,1,'2026-07-22 08:14:34',0,1),(7,'UNIT_20',14,700,10,'2026-07-22 08:24:17',5,5),(8,'UNIT_22',13,900,13,'2026-07-22 09:04:08',10,3),(9,'UNIT_21',13,20,5,'2026-07-23 06:50:01',3,2),(10,'UNIT_20',4,60,10,'2026-07-23 07:06:57',9,1);
/*!40000 ALTER TABLE `track_unit_items` ENABLE KEYS */;
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
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `unit_strength`
--

LOCK TABLES `unit_strength` WRITE;
/*!40000 ALTER TABLE `unit_strength` DISABLE KEYS */;
INSERT INTO `unit_strength` VALUES (1,'UNIT_11',600,0),(2,'UNIT_12',500,0),(3,'UNIT_14',400,0),(4,'UNIT_15',900,0),(5,'UNIT_16',800,0),(6,'UNIT_20',700,700),(7,'UNIT_21',0,400),(8,'UNIT_25',0,500),(9,'UNIT_22',0,500),(10,'UNIT_22',0,0),(11,'UNIT_20',700,700),(12,'UNIT_20',700,700);
/*!40000 ALTER TABLE `unit_strength` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `units`
--

DROP TABLE IF EXISTS `units`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `units` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `authorized_strength` int DEFAULT '0',
  `posted_strength` int DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `units`
--

LOCK TABLES `units` WRITE;
/*!40000 ALTER TABLE `units` DISABLE KEYS */;
INSERT INTO `units` VALUES (1,'19 INF DOU',600,900),(2,'2 FOD',500,700),(3,'28 INF DOU',700,850),(8,'68_DOU',1200,1000),(9,'57_DOU',700,500);
/*!40000 ALTER TABLE `units` ENABLE KEYS */;
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

-- Dump completed on 2026-07-23 15:08:59
