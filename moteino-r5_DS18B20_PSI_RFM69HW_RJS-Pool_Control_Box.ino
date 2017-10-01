/*
 
  richard@ears.net
  10/01/2017
 
  moteino-r5_DS18B20_PSI_RFM69HW_RJS-Pool_Control_Box

  Reads PSI from a 100PSI pressure transducer
  Reads temperature from a DS18B20 temp sensor


  This sketch is designed to read temperature from a DS18B20 temp sensor and filter water pressure
  using a 100PSI pressure sensor all using a low-power USB powered Moteino R5 (http://www.moteino.com). 
  
  This sketch is derived from different sketches from both moteino.com and openenergymonitor.org. Many thanks to all who have helped
  in this process. 
 

  While the Moteino can transmit information to it's own gateway, I am using a RaspberryPi (emonPi) created and maintained by the folks
  at Open Energy Monitoring. I then take this information and write it to a privately hosted version of emoncms, although you could also
  use the free emoncms hoting provided by http://emoncms.org

  
  In this sketch I have the DS18B20 connected as follows:
  ........................
  1) Black (GND) on DS18B20 to GND on Moteino
  2) Red on DS18B20 to Pin D5 on Moteino
  3) Data on DS18B20 to A5 (D19 SCL) on Moteino
  4) 4.7k Resistor is connected across D5 & A5 
  

  In this sketch I have the Filter PSI transducer connected as follows:
  1) Black to GND on Moteino
  2) Red to VIN on Moteino
  3) Data to A0 on Moteino
  
  *** NOTE - I AM NOT using a resistor between A0 and data on the transducer but you may need to do so depending on your configuration.
  ***        In my case, my transducer is 4.5V at 100PSI. Since my filter never gets above 40PSI, I will not get close to the 4.5V and
  ***        hence I do not need a resistor or the associated code to create a new table of values. 
  
  Again, this sketch is designed to talk directly to an emonpi not to a moteino gateway, so if you want to talk to a moteino gateway,
  you will need to make modifications to this sketch.



 This is what my emonhub.conf looks like since I am using emoncms:

 
[[27]]
    nodename = pool_control_box
    firmware = moteino-r5_DS18B20_Pulse_RFM69HW_RJS_Pool_Control
    hardware = moteino_R5
    [[[rx]]]
       names = TEMP, PSI
       datacode = h
       scales = 1,1
       units = F,P


Additional information along with schematics can be found here: https://github.com/rjsears/Pool_Fill_Control

  
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
*/

#define debug 1                                                      // Set to 1 to few debug serial output, turning debug off increases battery life
#define serial_speed 9600
#define RF69_COMPAT 1                                                 // Set to 1 if using RFM69CW or 0 is using RFM12B

// Do we have a TEMP sensor and a Pressure Sensor?
boolean TEMP_SENSOR_PRESENT;
boolean PSI_SENSOR_PRESENT;

/*
 Libraries in the standard arduino libraries folder:
   - RFu JeeLib           https://github.com/openenergymonitor/RFu_jeelib   - to work with CISECO RFu328 module
   - DHT22 Sensor Library https://github.com/adafruit/DHT-sensor-library    - be sure to rename the sketch folder to remove the '-'
   - OneWire library      http://www.pjrc.com/teensy/td_libs_OneWire.html   - DS18B20 sensors
   - DallasTemperature    http://download.milesburton.com/Arduino/MaximTemperature/DallasTemperature_LATEST.zip - DS18B20 sensors
 */
#include <RFM69.h>         //get it here: http://github.com/lowpowerlab/rfm69
#include <WirelessHEX69.h> //get it here: https://github.com/LowPowerLab/WirelessProgramming
#include <avr/power.h>
#include <avr/sleep.h>
#include <JeeLib.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <DHT.h>


// Attached JeeLib sleep function to Atmega328 watchdog
// enables MCU to be put into sleep mode between readings to reduce power consumption

ISR(WDT_vect) {
  Sleepy::watchdogEvent();
} 


//*********************************************************************************************
//************  Here is all the radio stuff, change to meet your configuration!! **************
//*********************************************************************************************
RFM69 radio;
#define FREQUENCY RF12_433MHZ              // Frequency of RF12B module can be RF12_433MHZ, RF12_868MHZ or RF12_915MHZ.
#define IS_HIGHPOWER   true               // True only for RFM69HW High Power RFM69
int NODE_ID = 27;                         // Node ID - should be unique on network - I use 30 for testing
const int NETWORK_GROUP = 210;            // Network group                                                                           
//*********************************************************************************************


// Setup some pins for the Moteino R5
#define LED            9     // Moteinos have LEDs on D9

// DS18B20 pin allocation
const int DS18B20_PWR  = 5;

// Temp Sensor 
#define ONE_WIRE_BUS_A    19     // Temp Sensor(s) (A5 on MotenioUSB)
OneWire oneWireA(ONE_WIRE_BUS_A);
DallasTemperature sensors(&oneWireA);   

// Pool Filter Pressure Sensor Setup
#define PSI_SENSOR_PIN  0    // Sensor on A0 on MotenioUSB R5
float sensorVoltage = 0;
int PSI = 0;

/*
 Monitoring configuration
 ========================
 
  - how long to wait between readings, in minutes
  - DS18B20 temperature precision:
      9bit: 0.5C,  10bit: 0.25C,  11bit: 0.1125C, 12bit: 0.0625C
  - Required delay when reading DS18B20
      9bit: 95ms,  10bit: 187ms,  11bit: 375ms,   12bit: 750ms
 */
 
const int MINS_BETWEEN_READINGS = 1; // minutes between readings
const int TEMPERATURE_PRECISION = 11;
const int ASYNC_DELAY           = 375;


// What information are we going to be transmitting back to our gateway?

typedef struct {                               // RF payload datastructure
  int TEMP;
  int PSI;                                             
} SensorPayload;
SensorPayload pool_sensors;

/*
  External sensor addresses
  =========================  
 Hardcoding these guarantees emonCMS inputs won't flip around if you replace or add sensors.
 Use one of the address finding sketches to determine your sensors' unique addresses.
 
 Extend this if you have more sensors.
 */
 
DeviceAddress insideThermometer = {
0x28, 0x99, 0xA3, 0x1E, 0x00, 0x00, 0x80, 0xE5 };

// Let's get things setup:
//################################################################################################################################
//################################################################################################################################
void setup() {
//################################################################################################################################
 set_pin_modes();
  
// LED on
digitalWrite(LED, HIGH);                       // Status LED on

// Initialize RFM12B
rf12_initialize(NODE_ID, FREQUENCY, NETWORK_GROUP);
radio.setHighPower();              // If we are using the RFM69HW version of the radio, set it to high power
rf12_sleep(RF12_SLEEP);


// Initialize DS18B20 Sensor
initialise_DS18B20();
   
// If debug mode is set above, output some useful information to the serial port.
  
  if (debug)        
  {
    Serial.begin(serial_speed);
    Serial.println("moteino-r5_DS18B20_RFM69HW_RJS_Pool_Control_Box");
    Serial.println(); 
    #if (RF69_COMPAT)
      Serial.println("RFM69HW Radio Initialized");
      Serial.println();
    #else
      Serial.println("RFM12B Initialized");
      Serial.println();
    #endif
    Serial.print("Node: "); 
    Serial.print(NODE_ID); 
    Serial.print(",  Freq: "); 
    if (FREQUENCY == RF12_433MHZ) Serial.print("433Mhz");
    if (FREQUENCY == RF12_868MHZ) Serial.print("868Mhz");
    if (FREQUENCY == RF12_915MHZ) Serial.print("915Mhz"); 
    Serial.print(",  Network: "); 
    Serial.println(NETWORK_GROUP);
    Serial.println();
    delay(1000);
  }

  // LED off
digitalWrite(LED, LOW);

} // end of setup


// Here is where we do our work:
//################################################################################################################################
//################################################################################################################################
void loop() 
//################################################################################################################################
{

// Get Our Temp and Pressure Readings and trnsmit back to the mothership
take_sensor_readings();

  power_spi_enable();
  rf12_sleep(RF12_WAKEUP);
  rf12_sendNow(0, &pool_sensors, sizeof pool_sensors);
  rf12_sendWait(2);
  rf12_sleep(RF12_SLEEP);
  power_spi_disable();

  if (debug){
    flash_led(50);
    Serial.print("TEMP: "); Serial.print(pool_sensors.TEMP);
    Serial.print(", Filter PSI: "); Serial.println(pool_sensors.PSI); 
  }
//delay loop, wait for time_between_reading minutes
  for (int i=0; i<MINS_BETWEEN_READINGS; i++)
  {
    dodelay(55000); //1 minute should be 60000 but is not because of variation of internal time source
    //caution parameter cannot be more than 65000, maybe find better solution
    //due to internal time source 60000 is longer than 1 minute. so 55s is used.
  }
  
}

//####################################################################################################################################


// Setup our Pin Modes Here
void set_pin_modes()
{
  pinMode(LED, OUTPUT);
  pinMode(DS18B20_PWR, OUTPUT);
  pinMode(PSI_SENSOR_PIN, INPUT);
}
 
void initialise_DS18B20()
{
// Switch on
  digitalWrite(DS18B20_PWR, HIGH);
  delay(50);

  sensors.begin();
  Serial.begin(serial_speed);
  Serial.println("Dallas Temperature IC Control Library");

  // locate devices on the bus
  Serial.print("Locating devices...");
  sensors.begin();
  Serial.print("Found ");
  Serial.print(sensors.getDeviceCount(), DEC);
  Serial.println(" devices.");

  // report parasite power requirements
  Serial.print("Parasite power is: "); 
  if (sensors.isParasitePowerMode()) Serial.println("ON");
  else Serial.println("OFF");


  // set the resolution to 9 bit (Each Dallas/Maxim device is capable of several different resolutions)
  sensors.setResolution(insideThermometer, 12);
 
  Serial.print("Device 0 Resolution: ");
  Serial.print(sensors.getResolution(insideThermometer), DEC); 
  Serial.println();
  
  //Power Down
  digitalWrite(DS18B20_PWR, LOW);
}

/**
 * Flash the LED for the stated period
 */
void flash_led (int duration){
  digitalWrite(LED,HIGH);
  delay(duration);
  digitalWrite(LED,LOW);
}

void dodelay(unsigned int ms)
{
  byte oldADCSRA=ADCSRA;
  byte oldADCSRB=ADCSRB;
  byte oldADMUX=ADMUX;
      
  Sleepy::loseSomeTime(ms); // JeeLabs power save function: enter low power mode for x seconds (valid range 16-65000 ms)
      
  ADCSRA=oldADCSRA;         // restore ADC state
  ADCSRB=oldADCSRB;
  ADMUX=oldADMUX;
}

// Get our Filter Pressure
void get_filter_pressure()
{
  sensorVoltage = analogRead(PSI_SENSOR_PIN);   // Let's read our pressure sensor voltage
  PSI = ((sensorVoltage-146)/204)*25;  // Some calibration to convert the voltage to PSI and zero it 
  pool_sensors.PSI = PSI;
}

// Get our temperature reading
void take_ds18b20_reading ()
{
  digitalWrite(DS18B20_PWR, HIGH);
  delay(50);
  sensors.requestTemperatures(); // Send the command to get temperatures
  delay(10);
  int temp1=(sensors.getTempF(insideThermometer));
  pool_sensors.TEMP =  temp1;
  digitalWrite(DS18B20_PWR, LOW);
}


void take_sensor_readings()
{
  Serial.println("Getting Sensor Readings...");
  take_ds18b20_reading();
  delay(500);
  get_filter_pressure();
  delay(500);
  if (debug){
    Serial.print("TEMP: "); Serial.print(pool_sensors.TEMP);
    Serial.print(", Filter PSI: "); Serial.print(pool_sensors.PSI); 
    Serial.print(", Sensor Voltage: "); Serial.println(sensorVoltage);
    flash_led(50);
  }
  
}
