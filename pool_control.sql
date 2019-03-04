-- pool_control_master MySQL Dump
-- version 3.5.1
-- 
--
-- Host: localhost:3306
-- Generation Time: Mar 04, 2019 at 04:36 PM
-- Server version: 5.7.25-0ubuntu0.18.04.2
-- PHP Version: 7.2.10-0ubuntu0.18.04.1

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `pool_control`
--

-- --------------------------------------------------------

--
-- Table structure for table `acid_level`
--

CREATE TABLE `acid_level` (
  `acid_level_ok` bit(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `filling_gallons`
--

CREATE TABLE `filling_gallons` (
  `gallons_start` int(10) UNSIGNED NOT NULL,
  `gallons_stop` int(10) UNSIGNED NOT NULL,
  `gallons_last_fill` smallint(5) UNSIGNED NOT NULL,
  `gallons_current_fill` smallint(5) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `filling_status`
--

CREATE TABLE `filling_status` (
  `pool_is_filling` tinyint(1) NOT NULL,
  `fill_critical_stop` tinyint(1) NOT NULL,
  `pool_manual_fill` tinyint(1) NOT NULL,
  `alexa_manual_fill` tinyint(1) NOT NULL,
  `alexa_test_sprinkler_running` tinyint(1) NOT NULL,
  `alexa_test_pool_is_filling` tinyint(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `filling_time`
--

CREATE TABLE `filling_time` (
  `pool_fill_start_time` int(10) UNSIGNED NOT NULL,
  `pool_fill_total_time` int(3) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `led_status`
--

CREATE TABLE `led_status` (
  `sprinkler_run_led` tinyint(1) NOT NULL,
  `pump_run_led` tinyint(1) NOT NULL,
  `system_run_led` tinyint(1) NOT NULL,
  `system_error_led` tinyint(1) NOT NULL,
  `pool_filling_led` tinyint(1) NOT NULL,
  `pool_fill_valve_disabled_led` tinyint(1) NOT NULL,
  `manual_fill_button_led` tinyint(1) NOT NULL,
  `test_led` varchar(5) COLLATE utf8_unicode_ci NOT NULL DEFAULT 'FALSE'
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `logging`
--

CREATE TABLE `logging` (
  `console` tinyint(1) NOT NULL,
  `logging` tinyint(1) NOT NULL,
  `level` varchar(8) COLLATE utf8_unicode_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `manual_buttons`
--

CREATE TABLE `manual_buttons` (
  `pool_manual_fill_button` bit(1) NOT NULL,
  `pool_valve_disabled_button` bit(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `notification_methods`
--

CREATE TABLE `notification_methods` (
  `pushbullet` bit(1) NOT NULL,
  `email` bit(1) NOT NULL,
  `sms` bit(1) NOT NULL,
  `logging` bit(1) NOT NULL,
  `debug` bit(1) NOT NULL,
  `verbose_debug` bit(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `notification_settings`
--

CREATE TABLE `notification_settings` (
  `pump_control_notifications` bit(1) NOT NULL,
  `pump_control_software_notifications` bit(1) NOT NULL,
  `pool_fill_notifications` bit(1) NOT NULL,
  `pool_level_sensor_notifications` bit(1) NOT NULL,
  `pool_temp_sensor_notifications` bit(1) NOT NULL,
  `pool_filter_psi_notifications` bit(1) NOT NULL,
  `pool_acid_level_notifications` bit(1) NOT NULL,
  `pool_fill_control_reset_notifications` bit(1) NOT NULL,
  `pool_database_notifications` bit(1) NOT NULL,
  `pump_error_notifications` bit(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `notification_status`
--

CREATE TABLE `notification_status` (
  `pool_level_sensor_timeout_alert_sent` bit(1) NOT NULL,
  `pool_level_low_voltage_alert_sent` bit(1) NOT NULL,
  `pool_temp_sensor_timeout_alert_sent` bit(1) NOT NULL,
  `pool_temp_low_voltage_alert_sent` bit(1) NOT NULL,
  `pool_filter_psi_alert_sent` bit(1) NOT NULL,
  `pool_filling_sent` bit(1) NOT NULL,
  `critical_time_warning_sent` bit(1) NOT NULL,
  `critical_stop_warning_sent` bit(1) NOT NULL,
  `critical_stop_enabled_warning_sent` bit(1) NOT NULL,
  `pool_database_error_alert_sent` bit(1) NOT NULL,
  `acid_level_low_alert_sent` bit(1) NOT NULL,
  `acid_level_low_alert_sent_time` int(10) UNSIGNED NOT NULL,
  `pump_not_running_error_alert_sent` bit(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `pool_chemicals`
--

CREATE TABLE `pool_chemicals` (
  `pool_current_ph` decimal(5,3) NOT NULL,
  `pool_current_orp` decimal(5,1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `pool_filling_history`
--

CREATE TABLE `pool_filling_history` (
  `time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `gallons` smallint(5) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `pool_level`
--

CREATE TABLE `pool_level` (
  `pool_level` varchar(10) COLLATE utf8_unicode_ci NOT NULL,
  `pool_level_percentage` int(3) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `power_solar`
--

CREATE TABLE `power_solar` (
  `total_current_power_utilization` smallint(5) NOT NULL,
  `total_current_power_import` smallint(5) NOT NULL,
  `total_current_solar_production` smallint(5) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `pump_status`
--

CREATE TABLE `pump_status` (
  `pump_control_active` tinyint(1) NOT NULL,
  `pump_running` tinyint(1) NOT NULL,
  `pump_watts` smallint(5) UNSIGNED NOT NULL,
  `pump_gpm` tinyint(3) UNSIGNED NOT NULL,
  `pump_rpm` smallint(4) UNSIGNED NOT NULL,
  `pump_program_running` varchar(10) COLLATE utf8_unicode_ci NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `reset_status`
--

CREATE TABLE `reset_status` (
  `system_reset_required` bit(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `sensor_status`
--

CREATE TABLE `sensor_status` (
  `pool_level_sensor_ok` bit(1) NOT NULL,
  `pool_temp_sensor_ok` bit(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `sprinkler_status`
--

CREATE TABLE `sprinkler_status` (
  `sprinklers_on` tinyint(1) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `system_status`
--

CREATE TABLE `system_status` (
  `current_military_time` varchar(35) COLLATE utf8_unicode_ci NOT NULL,
  `filter_current_psi` decimal(5,2) NOT NULL,
  `pool_current_temp` decimal(5,2) NOT NULL,
  `pool_level_batt_percentage` tinyint(3) NOT NULL,
  `pool_temp_batt_percentage` tinyint(3) NOT NULL,
  `pool_autofill_active` bit(1) NOT NULL,
  `garage_temp_batt_percentage` tinyint(3) NOT NULL,
  `attic_temp_batt_percentage` tinyint(3) NOT NULL,
  `pool_temp_sensor_humidity` tinyint(3) NOT NULL,
  `pool_level_sensor_humidity` tinyint(3) NOT NULL,
  `garage_temp_sensor_humidity` tinyint(3) NOT NULL,
  `pool_level_sensor_temp` decimal(5,2) NOT NULL,
  `pool_temp_sensor_temp` decimal(5,2) NOT NULL,
  `attic_current_temp` decimal(5,2) NOT NULL,
  `garage_current_temp` decimal(5,2) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `acid_level`
--
ALTER TABLE `acid_level`
  ADD UNIQUE KEY `acid_level_ok` (`acid_level_ok`);

--
-- Indexes for table `filling_gallons`
--
ALTER TABLE `filling_gallons`
  ADD UNIQUE KEY `gallons_start` (`gallons_start`);

--
-- Indexes for table `filling_status`
--
ALTER TABLE `filling_status`
  ADD UNIQUE KEY `pool_is_filling` (`pool_is_filling`);

--
-- Indexes for table `filling_time`
--
ALTER TABLE `filling_time`
  ADD UNIQUE KEY `pool_fill_start_time` (`pool_fill_start_time`);

--
-- Indexes for table `led_status`
--
ALTER TABLE `led_status`
  ADD UNIQUE KEY `sprinkler_run_led` (`sprinkler_run_led`);

--
-- Indexes for table `logging`
--
ALTER TABLE `logging`
  ADD UNIQUE KEY `console` (`console`);

--
-- Indexes for table `manual_buttons`
--
ALTER TABLE `manual_buttons`
  ADD UNIQUE KEY `pool_manual_fill_button` (`pool_manual_fill_button`);

--
-- Indexes for table `notification_methods`
--
ALTER TABLE `notification_methods`
  ADD UNIQUE KEY `pushbullet` (`pushbullet`);

--
-- Indexes for table `notification_settings`
--
ALTER TABLE `notification_settings`
  ADD UNIQUE KEY `pump_control_notifications` (`pump_control_notifications`);

--
-- Indexes for table `notification_status`
--
ALTER TABLE `notification_status`
  ADD UNIQUE KEY `pool_level_sensor_timeout_alert_sent` (`pool_level_sensor_timeout_alert_sent`);

--
-- Indexes for table `pool_chemicals`
--
ALTER TABLE `pool_chemicals`
  ADD UNIQUE KEY `pool_current_ph` (`pool_current_ph`);

--
-- Indexes for table `pool_filling_history`
--
ALTER TABLE `pool_filling_history`
  ADD UNIQUE KEY `time` (`time`);

--
-- Indexes for table `pool_level`
--
ALTER TABLE `pool_level`
  ADD UNIQUE KEY `pool_level` (`pool_level`);

--
-- Indexes for table `power_solar`
--
ALTER TABLE `power_solar`
  ADD UNIQUE KEY `total_current_power_utilization` (`total_current_power_utilization`);

--
-- Indexes for table `pump_status`
--
ALTER TABLE `pump_status`
  ADD UNIQUE KEY `pump_control_active` (`pump_control_active`);

--
-- Indexes for table `reset_status`
--
ALTER TABLE `reset_status`
  ADD UNIQUE KEY `system_reset_required` (`system_reset_required`);

--
-- Indexes for table `sensor_status`
--
ALTER TABLE `sensor_status`
  ADD UNIQUE KEY `pool_level_sensor_ok` (`pool_level_sensor_ok`);

--
-- Indexes for table `sprinkler_status`
--
ALTER TABLE `sprinkler_status`
  ADD UNIQUE KEY `sprinklers_on` (`sprinklers_on`);

--
-- Indexes for table `system_status`
--
ALTER TABLE `system_status`
  ADD UNIQUE KEY `current_military_time` (`current_military_time`);

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
