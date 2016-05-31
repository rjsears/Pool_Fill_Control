/*

  VERSION 1.1
  moteino Low Power Pool Level Monitor

  This sketch is designed to be used with the ETAPE resistive water/fluid level sensor sold
  by Adafruit and manufactured by Milone Tech. I needed a way to monitor my pool level, 
  transmit the information to emoncms and then take action when the pool level fell below a 
  critical level. In my case, I open a sprinkler valve and fill the pool back to its normal 
  level. This sketch turns on the onboard LED. Since my monitoring location and my sprinkler
  valve location are in different parts of my yard, this unit only monitors the level and 
  reports back to emoncms. I use a Raspberry Pi to read level from the emoncms database and 
  open or close the sprinkler valve.

  Currently I use pin A0  to read the resistance of the etape and then
  turn on LED 9 when it falls below my critical level. I have not bothered converting resistance
  into inches for the pool as it really is a totally unnecessary number in my case.

  ============================================
  How to connect the eTape to your Moteino


  .......................
  1) Connect one of the middle pins of the eTape to ground. (Some versions of eTape only have three leads)
  2) Connect one of the other pins to a 560 ohm resistor.
  3) Connect the same end of this resistor to pin A0.
  4) Connect the other end of the resistor to GPIO PIN 7 source on the Moteino. We do this so we can completely
     power down the etape when we are not reading the resistance from it.  
  
  
  Information is gathered (resistance from the eTape, battery voltage and pool level) and transmitted to am EmonPi
  made by the folks over at the Open Energy Monitor project. My EmonPi then retransmits that data to
  a remote emoncms system for storage, graphing, etc.

  On another system (Pi), I have a PHP script that checks the pool level in the emoncms database once per minute. When
  it detects that the pool level is low, it opens a sprinkler valve to refill the pool and sends me a notification.
  Once the pool is full, it shuts off the valve and then sends me another notification.
  
    
  Part of the openenergymonitor.org project
  Licence: GNU GPL V3

  Author: Richard Sears (richard@sears.net)
  Parts derived from sketches from Eric Ammann & Glyn Hudson
  Builds upon JCW JeeLabs RF12 library, Arduino and Martin Harizanov's work


  THIS SKETCH REQUIRES:

  Libraries in the standard arduino libraries folder:
  - JeeLib    https://github.com/jcw/jeelib
  - RFM69


  Recommended node ID allocation
  -----------------------------------------------------------------------------------------------------------
  -ID-  -Node Type-
  0 - Special allocation in JeeLib RFM12 driver - reserved for OOK use
  1-4     - Control nodes
  5-10  - Energy monitoring nodes
  11-14 --Un-assigned --
  15-16 - Base Station & logging nodes
  17-30 - Environmental sensing nodes (temperature humidity etc.)
  31  - Special allocation in JeeLib RFM12 driver - Node31 can communicate with nodes on any network group
  -------------------------------------------------------------------------------------------------------------

  Change log:
  V1.0         add support for reading resistance value from eTape manufactured by www.milonetech.com
  V1.1         made a bunch of different low power changes to reduce the overall usage

  
emonhub.conf nodes config:

[[25]]
    nodename = pool_level
    firmware = moteino_Pool_Water_Level_Sensor_ETAPE_digital
    hardware = moteino_eTape_RF69HW
    [[[rx]]]
       names = resistance, battery, level
       datacode = h
       scales = 1,0.001,1
       units = O,V
       
*/


// Let's get started

// Are we in Debug mode?
#define debug 0                                       // Set to 0 to save power, shuts down serial


#define RF69_COMPAT 1                                  // Set to 1 if using RFM69 or 0 is using RFM12B

// Include some libraries
#include <JeeLib.h>                                   //https://github.com/jcw/jeelib - Tested with JeeLib 3/11/14 
#include <avr/power.h>
#include <avr/sleep.h>
#include <RFM69.h>
#include <SPIFlash.h>                                 //get it here: https://www.github.com/lowpowerlab/spiflash


/*
 Wireless and Node Configuration
 -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
 - RFM12B frequency can be RF12_433MHZ, RF12_868MHZ or RF12_915MHZ. You should use the one matching the module you have.
  - RFM12B wireless network group - needs to be same as emonBase and emonGLCD
  - RFM12B node ID - should be unique on network

 Recommended node ID allocation
 ------------------------------------------------------------------------------------------------------------
 -ID- -Node Type-
 0  - Special allocation in JeeLib RFM12 driver - reserved for OOK use
 1-4    - Control nodes
 5-10 - Energy monitoring nodes
 11-14  --Un-assigned --
 15-16  - Base Station & logging nodes
 17-30  - Environmental sensing nodes (temperature humidity etc.)
 31 - Special allocation in JeeLib RFM12 driver - Node31 can communicate with nodes on any network group
 -------------------------------------------------------------------------------------------------------------
 */

//
// All the radio stuff....
//
// Transmitting Frequency
RFM69 radio;
#define RF_freq RF12_433MHZ                 // Frequency of RF12B module. Only uncomment one. It should match the rest of your system
//#define FREQUENCY RF12_915MHZ
//#define FREQUENCY RF12_868MHZ

#define IS_HIGHPOWER   true            // True only for RFM69HW High Power RFM69

// Node ID
int nodeID = 25;                               // Node ID - should be unique on network - DIP switches can increment this ID by 1, 2 or 3.

// Network Group
const int networkGroup = 210;                // RFM12B wireless network group - needs to be same as emonBase and emonGLCD

//
// Define where things are plugged in on the Moteino
//

// moteino pin allocations
const int LED_RED =        9;

// Where is the ETAPE connected
#define ETAPE A0                            // Where are we reading the resistance?
const int ETAPE_POWER = 7;                  // What GPIO pin will be powering the eTape?

// What is the CRUCIAL LEVEL of our pool water.
#define CRUCIAL_LEVEL 645                       // You will need to test your eTape to get a setting that
#define POOL_OK_LEVEL 570                       // works for you. In my case, 645 is about 4" on the tape for me                                             


// Set up a timer (in minutes)
const int time_between_readings = 1;           // How often do you want to measure and then transmit your readings to your Emonhub/Pi?


ISR(WDT_vect)
{
  Sleepy::watchdogEvent();    // Attached JeeLib sleep function to Atmega328 watchdog -enables MCU to be put into sleep mode in
}                             //between readings to reduce power consumption


// Define what our RF payload will look like
typedef struct
{
  int resistance;
  int battery;
  int level;
} Payload;
Payload pool;


SPIFlash flash(8, 0xEF30); //EF30 for 4mbit  Windbond chip (W25X40CL)


//
// We run this ONE time on boot
//
void setup(void)
{
  pinMode(LED_RED, OUTPUT);
  pinMode(ETAPE_POWER, OUTPUT);                       // Set the pin powering the eTape to OUTPUT
  
  pinMode(8, OUTPUT);                                 // Added to make sure flash stays asleep and does not use power!
  digitalWrite(8, HIGH);

// Initialize our RF
  rf12_initialize(nodeID, RF_freq, networkGroup);     // nodeID, RF_freq and networkGroup are taken from above
  if(IS_HIGHPOWER) radio.setHighPower();              // If we are using the RFM69HW version of the radio, set it to high power


// Tell thge wireless to take a nap until we need it again.....
  rf12_sleep(RF12_SLEEP);
  radio.sleep();

  flash.initialize();                                 // Initialize the flash and then put it to sleep!
  flash.sleep();

// Are we in debug mode? Output some information to the serial line....
  if (debug)
  {
    Serial.begin(9600);
    Serial.println("moteino_Pool_Water_Level_Sensor_ETAPE V1.0");
    Serial.println("OpenEnergyMonitor.org");
    Serial.println("RFM69HW Init> ");
    Serial.print("Node: ");
    Serial.print(nodeID);
    Serial.print(" Freq: ");
    if (RF_freq == RF12_433MHZ) Serial.print("433Mhz");
    if (RF_freq == RF12_868MHZ) Serial.print("868Mhz");
    if (RF_freq == RF12_915MHZ) Serial.print("915Mhz");
    Serial.print(" Network: ");
    Serial.println(networkGroup);
    delay(100);
    Serial.println();
    Serial.print("You are currently configured to transmit data every ");
    Serial.print(time_between_readings);
    Serial.println(" minute(s).");
    Serial.println();
    Serial.println("Here is the data that we are transmitting:");
  }


// Debug should look something like this
  /*
  moteino_Pool_Water_Level_Sensor_ETAPE V1.0
  OpenEnergyMonitor.org
  RFM69CW Init>
  Node: 25 Freq: 433Mhz Network: 210

  You are currently configured to transmit data every 1 minute(s).

  Here is the data that we are transmitting:
  ETape Resistance Level: 877 Ohms, Battery voltage: 3.20V
  ETape Resistance Level: 873 Ohms, Battery voltage: 3.20V
  ETape Resistance Level: 873 Ohms, Battery voltage: 3.20V
  ETape Resistance Level: 873 Ohms, Battery voltage: 3.20V
  ETape Resistance Level: 873 Ohms, Battery voltage: 3.40V
  */

// turn off non critical chip functions to reduce battery drain
  reduce_power();



}
// Here is where we do the actual work....

void loop(void)
{
  digitalWrite(ETAPE_POWER, HIGH);                          // Turn on the power to the eTape circuit
  pool.resistance = analogRead(ETAPE);                      // read etape resistance
  digitalWrite(ETAPE_POWER, LOW);                           // Turn off power to the eTape circuit

// Read our battery voltage  
  pool.battery = readVcc();                                 // read battery voltage


// OK, time to do something about our pool level

// Here is where you can do something besides turning on an LED, such as triggering
// a relay or nothing at all. In my case, I just need the information transmitted to
// emoncms. Once in a MyDQL database, I use another node (pi actually) to read the 
// entry in the DB and act on what it finds there.

    if (pool.resistance >= CRUCIAL_LEVEL)
   {
    pool.level = 0;
        if (debug)
        {
           digitalWrite(LED_RED, HIGH);
         }
    }
  else if (pool.resistance <= POOL_OK_LEVEL) 
      {
    pool.level = 1;
         if (debug) 
         {
            digitalWrite(LED_RED, LOW);
         }
      }
      
  delay(1000);
 
// Are we in debug mode? Output the resistance level and battery voltage to the serial port....
  if (debug)
  {
    Serial.print("ETape Level: ");
    Serial.print(pool.resistance);
    Serial.print(" Ohms, ");
    delay(100);

    Serial.print("Battery voltage: ");
    Serial.print(pool.battery * 0.001);
    Serial.print("V, ");
    delay(100);
    
    Serial.print("Pool Level is ");
    if (pool.level == 0) Serial.println("LOW");
    if (pool.level == 1) Serial.println("OK");
    delay(100);
  }


// Power up the Serial Peripheral Interface (SPI) for wireless communications...
  power_spi_enable();

  rf12_sleep(RF12_WAKEUP);
  dodelay(100);
  rf12_sendNow(0, &pool, sizeof pool);
  rf12_sendWait(2);
  rf12_sleep(RF12_SLEEP);
  radio.sleep();
  dodelay(100);

  // Power down the Serial Peripheral Interface (SPI) for wireless communications...
  power_spi_disable();



//delay loop, wait for time_between_reading minutes
  for (int i = 0; i < time_between_readings; i++)
  {
    dodelay(55000); //1 minute should be 60000 but is not because of variation of internal time source
    //caution parameter cannot be more than 65000, maybe find better solution
    //due to internal time source 60000 is longer than 1 minute. so 55s is used.
  }
}

void dodelay(unsigned int ms)
{
  byte oldADCSRA = ADCSRA;
  byte oldADCSRB = ADCSRB;
  byte oldADMUX = ADMUX;

  Sleepy::loseSomeTime(ms); // JeeLabs power save function: enter low power mode for x seconds (valid range 16-65000 ms)

  ADCSRA = oldADCSRA;       // restore ADC state
  ADCSRB = oldADCSRB;
  ADMUX = oldADMUX;
}

/**
 * Turn off what we don't need.
 * see http://www.nongnu.org/avr-libc/user-manual/group__avr__power.html
 */
void reduce_power()
{
  digitalWrite(ETAPE_POWER,LOW);   // Make sure eTape is not powered
  ACSR |= (1 << ACD);              // Disable Analog comparator
  power_twi_disable();             // Disable the Two Wire Interface module.
  power_timer1_disable();          // Timer 1
  power_spi_disable();             // Serial peripheral interface

  if (!debug)
  {
    power_usart0_disable();        // Disable serial UART if not connected
  }

  power_timer0_enable();           // Necessary for this sketch
}



// ******************************************************************************************************
// Read and return the current battery voltage
// ******************************************************************************************************
long readVcc()
{
  // Read 1.1V reference against AVcc
  // set the reference to Vcc and the measurement to the internal 1.1V reference
#if defined(__AVR_ATmega32U4__) || defined(__AVR_ATmega1280__) || defined(__AVR_ATmega2560__)
  ADMUX = _BV(REFS0) | _BV(MUX4) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
#elif defined (__AVR_ATtiny24__) || defined(__AVR_ATtiny44__) || defined(__AVR_ATtiny84__)
  ADMUX = _BV(MUX5) | _BV(MUX0);
#elif defined (__AVR_ATtiny25__) || defined(__AVR_ATtiny45__) || defined(__AVR_ATtiny85__)
  ADMUX = _BV(MUX3) | _BV(MUX2);
#else
  ADMUX = _BV(REFS0) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
#endif

  delay(2); // Wait for Vref to settle
  ADCSRA |= _BV(ADSC); // Start conversion
  while (bit_is_set(ADCSRA, ADSC)); // measuring

  uint8_t low  = ADCL; // must read ADCL first - it then locks ADCH
  uint8_t high = ADCH; // unlocks both

  long result = (high << 8) | low;

  result = 1125300L / result; // Calculate Vcc (in mV); 1125300 = 1.1*1023*1000
  return result; // Vcc in millivolts
}

