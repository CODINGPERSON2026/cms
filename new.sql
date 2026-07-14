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
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `action_logs`
--

LOCK TABLES `action_logs` WRITE;
/*!40000 ALTER TABLE `action_logs` DISABLE KEYS */;
INSERT INTO `action_logs` VALUES (1,1,'scme','scme','CREATE','SCME','Recorded new SCME item: \'Altimeter\' (Unit: 19 INF DIV, Unit Auth: 500, Held: 300)','2026-07-10 11:26:25'),(2,1,'scme','scme','CREATE','SCME','Recorded new SCME item: \'Hammer Piton\' (Unit: 28 INF DIV, Unit Auth: 600, Held: 100)','2026-07-10 11:26:42'),(3,1,'scme','scme','CREATE','SCME','Recorded new SCME item: \'Thermal Insoles\' (Unit: VFSR, Unit Auth: 600, Held: 300)','2026-07-10 11:26:59'),(4,1,'scme','scme','CREATE','SCME','Recorded new SCME item: \'Avalanche Air Bag with Backpack, Flask & Snow Shoe Flak (Trigger)\' (Unit: 19 INF DIV, Unit Auth: 100, Held: 80)','2026-07-10 11:27:22'),(5,1,'scme','scme','UPDATE','SCME','Issued 100 of \'Hammer Piton\' for unit 28 INF DIV. (New Held: 200)','2026-07-10 11:27:47'),(6,1,'scme','scme','CREATE','ECC','Recorded monthly state for Item: \'Rucksack\', Division: 19 INF DIV','2026-07-14 15:44:36'),(7,1,'scme','scme','CREATE','ECC','Recorded monthly state for Item: \'Sleeping Bag Spl\', Division: 28 MOU','2026-07-14 16:00:38');
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
  PRIMARY KEY (`id`),
  KEY `item_id` (`item_id`),
  CONSTRAINT `ecc_monthly_state_ibfk_1` FOREIGN KEY (`item_id`) REFERENCES `ecc_scme_items` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ecc_monthly_state`
--

LOCK TABLES `ecc_monthly_state` WRITE;
/*!40000 ALTER TABLE `ecc_monthly_state` DISABLE KEYS */;
INSERT INTO `ecc_monthly_state` VALUES (1,8,'Scale 2',151,14,165,'2 FOD',195,35,230,5,3,28,7,35,25,13,38,198,29,227,1,5,19,14,4,10,18,88,'2026-07-14 16:40:23',0),(2,7,'Scale 4',458,15,473,'FC (L)',178,16,194,9,8,21,2,23,52,10,62,147,8,155,0,2,1,11,11,13,11,67,'2026-07-14 16:40:23',318),(3,19,'Scale 4',188,21,209,'3 Inf Div',253,20,273,6,10,39,5,44,46,13,59,246,12,258,2,4,19,6,6,8,15,112,'2026-07-14 16:40:23',0),(4,6,'Scale 4',207,13,220,'2 FOD',390,27,417,9,10,44,4,48,37,11,48,397,20,417,3,1,13,1,11,1,19,196,'2026-07-14 16:40:23',0),(5,20,'Scale 6',147,30,177,'2 FOD',307,10,317,6,2,20,6,26,54,15,69,273,1,274,4,3,12,16,17,13,2,141,'2026-07-14 16:40:23',0),(6,25,'Scale 8',356,49,405,'FC (L)',378,17,395,9,1,24,10,34,37,17,54,365,10,375,3,0,7,11,11,1,4,97,'2026-07-14 16:40:23',30),(7,15,'Scale 8',460,17,477,'FC (L)',326,24,350,10,6,18,8,26,13,17,30,331,15,346,5,3,17,10,7,11,20,146,'2026-07-14 16:40:23',131),(8,7,'Scale 1',459,35,494,'2 FOD',242,37,279,10,0,34,2,36,10,16,26,266,23,289,3,2,17,9,14,7,11,165,'2026-07-14 16:40:23',205),(9,19,'Scale 4',162,38,200,'3 Inf Div',150,12,162,10,5,41,3,44,43,2,45,148,13,161,4,4,17,17,11,14,0,187,'2026-07-14 16:40:23',39),(10,26,'Scale 10',470,23,493,'14 Corps',321,35,356,1,10,27,6,33,58,2,60,290,39,329,3,4,11,2,1,5,18,125,'2026-07-14 16:40:23',164),(11,18,'Scale 5',171,19,190,'2 FOD',312,12,324,5,6,17,5,22,56,13,69,273,4,277,2,5,17,10,20,5,16,182,'2026-07-14 16:40:23',0),(12,2,'Scale 2',191,28,219,'14 Corps',390,27,417,8,3,30,7,37,55,17,72,365,17,382,5,5,12,4,10,1,13,172,'2026-07-14 16:40:23',0),(13,26,'Scale 7',490,15,505,'8 Mtn Div',349,15,364,9,2,33,1,34,39,13,52,343,3,346,5,2,8,10,17,3,4,100,'2026-07-14 16:40:23',159),(14,1,'Scale 9',178,24,202,'FC (L)',156,24,180,2,9,14,7,21,58,17,75,112,14,126,2,0,1,10,7,1,8,164,'2026-07-14 16:40:23',76);
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
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `login_users`
--

LOCK TABLES `login_users` WRITE;
/*!40000 ALTER TABLE `login_users` DISABLE KEYS */;
INSERT INTO `login_users` VALUES (1,'ORD','123','super_admin',1),(2,'scme','123','scme',2);
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
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `org_ladder`
--

LOCK TABLES `org_ladder` WRITE;
/*!40000 ALTER TABLE `org_ladder` DISABLE KEYS */;
INSERT INTO `org_ladder` VALUES (1,'ORD','ROOT',NULL),(2,'scme','user',NULL);
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
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `scme_issued_items`
--

LOCK TABLES `scme_issued_items` WRITE;
/*!40000 ALTER TABLE `scme_issued_items` DISABLE KEYS */;
INSERT INTO `scme_issued_items` VALUES (1,'28_inf_div',54,'2 per indl','Prs',42,171,'2026-07-14 16:28:36',213),(2,'kfsr',54,'1 per indl','Prs',38,191,'2026-07-14 16:28:36',229),(3,'kfsr',64,'Nos','Nos',43,92,'2026-07-14 16:28:36',135),(4,'vfsr',64,'1 per indl','Prs',128,113,'2026-07-14 16:28:36',241),(5,'kfsr',41,'Prs','Prs',115,21,'2026-07-14 16:28:36',136),(6,'2_fod',41,'2 per indl','Nos',134,103,'2026-07-14 16:28:36',237),(7,'vfsr',41,'Prs','Nos',116,67,'2026-07-14 16:28:36',183),(8,'19_inf_div',39,'Prs','Prs',129,26,'2026-07-14 16:28:36',155),(9,'2_fod',39,'2 per indl','Prs',123,30,'2026-07-14 16:28:36',153),(10,'kfsr',31,'2 per indl','Nos',82,18,'2026-07-14 16:28:36',100),(11,'2_fod',52,'1 per indl','Nos',138,72,'2026-07-14 16:28:36',210),(12,'kfsr',52,'2 per indl','Nos',60,81,'2026-07-14 16:28:36',141),(13,'28_inf_div',52,'2 per indl','Prs',155,0,'2026-07-14 16:28:36',155),(14,'28_mou',45,'Nos','Nos',38,125,'2026-07-14 16:28:36',163),(15,'28_inf_div',40,'Prs','Prs',63,125,'2026-07-14 16:28:36',188),(16,'kfsr',40,'1 per indl','Nos',113,100,'2026-07-14 16:28:36',213),(17,'28_mou',40,'Prs','Prs',112,97,'2026-07-14 16:28:36',209),(18,'2_fod',55,'Nos','Prs',163,72,'2026-07-14 16:28:36',235),(19,'28_mou',59,'1 per indl','Prs',181,5,'2026-07-14 16:28:36',186),(20,'2_fod',59,'Prs','Prs',38,176,'2026-07-14 16:28:36',214),(21,'28_inf_div',59,'Prs','Prs',135,69,'2026-07-14 16:28:36',204),(22,'kfsr',49,'Prs','Prs',48,37,'2026-07-14 16:28:36',85),(23,'28_inf_div',49,'Prs','Prs',58,35,'2026-07-14 16:28:36',93),(24,'2_fod',49,'2 per indl','Prs',130,43,'2026-07-14 16:28:36',173),(25,'vfsr',33,'Nos','Nos',143,30,'2026-07-14 16:28:36',173),(26,'28_inf_div',61,'Nos','Prs',36,74,'2026-07-14 16:28:36',110),(27,'vfsr',32,'Prs','Prs',137,75,'2026-07-14 16:28:36',212),(28,'2_fod',32,'2 per indl','Nos',207,40,'2026-07-14 16:28:36',247),(29,'28_mou',32,'1 per indl','Nos',40,156,'2026-07-14 16:28:36',196);
/*!40000 ALTER TABLE `scme_issued_items` ENABLE KEYS */;
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
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `units`
--

LOCK TABLES `units` WRITE;
/*!40000 ALTER TABLE `units` DISABLE KEYS */;
INSERT INTO `units` VALUES (1,'19 INF DIV',15000,14200),(2,'28 INF DIV',12000,11500),(3,'KFSR',8000,7700),(4,'VFSR',9500,9100),(5,'2 FOD',3500,3200),(7,'28 MOU',4000,3800);
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
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'scme','123','scme');
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

-- Dump completed on 2026-07-14 17:28:12
