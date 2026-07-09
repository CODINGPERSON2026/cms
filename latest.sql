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
INSERT INTO `alembic_version` VALUES ('ddef8ff8d849');
/*!40000 ALTER TABLE `alembic_version` ENABLE KEYS */;
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
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=37 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `ecc_scme_items`
--

LOCK TABLES `ecc_scme_items` WRITE;
/*!40000 ALTER TABLE `ecc_scme_items` DISABLE KEYS */;
INSERT INTO `ecc_scme_items` VALUES (1,'Gaiters','CAT-II'),(2,'Poncho Glacier','CAT-II'),(3,'Karabiner \"P\" Type','CAT-II'),(4,'Karabiner \"S\" Type','CAT-II'),(5,'Pulleys','CAT-II'),(6,'Tent HA 10–12 Men','CAT-II'),(7,'Spare Glass Goggles','CAT-II'),(8,'Rope Climbing Glacier','CAT-II'),(9,'Thermal Insoles','CAT-II'),(10,'Under Slung Cargo Nets','CAT-II'),(11,'Knife All Purpose','CAT-II'),(12,'Rock Piton','CAT-II'),(13,'Fire Star Refill 4 Kg','CAT-II'),(14,'Fire Star Cooker','CAT-II'),(15,'Fire Star Refill Tube 150 gm','CAT-II'),(16,'Oxygen Cylinder','CAT-II'),(17,'Altimeter','CAT-II'),(18,'Ladder Crevasse','CAT-II'),(19,'Survival Blanket','CAT-II'),(20,'Boot Crampons','CAT-II'),(21,'Ice Axe & Shovel','CAT-II'),(22,'Cord Avalanche','CAT-II'),(23,'AVD / Pipes','CAT-II'),(24,'Ice Piton \"F\" Type','CAT-II'),(25,'Ice Piton \"G\" Type','CAT-II'),(26,'Combination Harness','CAT-II'),(27,'Splint Inflatable','CAT-II'),(28,'Hammer Piton','CAT-II'),(29,'Ladder Ice Wall Climbing','CAT-II'),(30,'Jummer (Ascender / Descender LH)','CAT-II'),(31,'Jummer (Ascender / Descender RH)','CAT-II'),(32,'Sledge Evacuation / Metallic Sledge','CAT-II'),(33,'Hyper Baric Chamber','CAT-II'),(34,'Rescue Bag','CAT-II'),(35,'Rod Avalanche','CAT-II'),(36,'Avalanche Air Bag with Backpack, Flask & Snow Shoe Flak (Trigger)','CAT-II');
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
  `issue_count` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `item_id` (`item_id`),
  CONSTRAINT `scme_issued_items_ibfk_1` FOREIGN KEY (`item_id`) REFERENCES `ecc_scme_items` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `scme_issued_items`
--

LOCK TABLES `scme_issued_items` WRITE;
/*!40000 ALTER TABLE `scme_issued_items` DISABLE KEYS */;
INSERT INTO `scme_issued_items` VALUES (1,'15 CESR',17,'50%','Nos',300,100,'2026-07-09 14:20:33',500,100),(2,'8 INF DIV',17,'50%','Nos',600,0,'2026-07-09 14:39:15',700,100),(4,'28 INF DIV',6,'50%','Nos',300,150,'2026-07-09 15:26:45',500,50);
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
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `units`
--

LOCK TABLES `units` WRITE;
/*!40000 ALTER TABLE `units` DISABLE KEYS */;
INSERT INTO `units` VALUES (1,'19 INF DIV'),(2,'28 INF DIV'),(3,'8 INF DIV'),(4,'15 CESR');
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

-- Dump completed on 2026-07-09 15:35:16
