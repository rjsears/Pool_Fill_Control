/*
  pool_level V2 Low Power SI7021 Humidity & Temperature, Two Float Pool Water level
  emonTH_V2_pool_level_sensor_20190216_dual_float_sensor.ino
  Current as of February 16th, 2019

  Modified for pool control project by Richard J. Sears
  richard@sears.net
  https://github.com/rjsears/Pool_Fill_Control
  
  
  Si7201 = internal temperature & Humidity

  Based on the work of:
  Part of the openenergymonitor.org project
  Licence: GNU GPL V3
  Authors: Glyn Hudson
  Builds upon JCW JeeLabs RF12 library, Arduino and Martin Harizanov's work
 -------------------------------------------------------------------------------------------------------------
  emonhub.conf node decoder:
  See: https://github.com/openenergymonitor/emonhub/blob/emon-pi/configuration.md

    [[25]]
    nodename = pool_level
    firmware = emonTH_V2_pool_level_sensor_20190208_dual_float_sensor
    hardware = moteino_eTape_RF69HW
    [[[rx]]]
       names = battery, level, temperature, humidity
       datacode = h
       scales = 0.1,1,0.01,0.01
       units = V,F,%
  */
// -------------------------------------------------------------------------------------------------------------
boolean debug=0
;                                                      // Set to 1 to enable debug serial output

const unsigned int  version = 323;                                    // firmware version
// These variables control the transmit timing of the pool_level
const unsigned long WDT_PERIOD = 80;                                  // mseconds.
const unsigned long WDT_MAX_NUMBER = 690;                             // Data sent after WDT_MAX_NUMBER periods of WDT_PERIOD:
                                                                      // 690x 80 = 55.2 seconds (it needs to be about 5s less than the record interval in emoncms)


#define RF69_COMPAT 1                                                 // Set to 1 if using RFM69CW or 0 is using RFM12B
#include <JeeLib.h>                                                   // https://github.com/jcw/jeelib
#include <RF69_avr.h>
//#define REG_SYNCVALUE1      0x2F
boolean RF_STATUS;
                                                  
byte RF_freq=RF12_433MHZ;                                           // Frequency of RF12B module can be RF12_433MHZ, RF12_868MHZ or RF12_915MHZ. You should use the one matching the module you have.
byte nodeID = 25;                                                      // pool_level temperature RFM12B node ID - should be unique on network
int networkGroup = 210;                                         // pool_level RFM12B wireless network group - needs to be same as emonBase and emonGLCD
                                                                      
const int TEMPERATURE_PRECISION=11;                                   // 9 (93.8ms),10 (187.5ms) ,11 (375ms) or 12 (750ms) bits equal to resplution of 0.5C, 0.25C, 0.125C and 0.0625C
#define ASYNC_DELAY 375                                               // 9bit requres 95ms, 10bit 187ms, 11bit 375ms and 12bit resolution takes 750ms
#include <avr/power.h>
#include <avr/sleep.h>
ISR(WDT_vect) { Sleepy::watchdogEvent(); }                            // Attached JeeLib sleep function to Atmega328 watchdog -enables MCU to be put into sleep mode inbetween readings to reduce power consumption

// SI7021_status SPI temperature & humidity sensor
#include <Wire.h>
#include <SI7021.h>
SI7021 SI7021_sensor;
boolean SI7021_status;

// Hardwired pool_level pin allocations
const byte LED=            9;
const byte BATT_ADC=       1;
const byte DIP_switch1=    7;
const byte DIP_switch2=    8;

// Setup for reading two position stainless steel 
// water level float switch. This replaces my eTape
// for measuring water level.
String UPPER_Float_Position;
String LOWER_Float_Position;
int UPPER_Float;
int LOWER_Float;

// Setup our RF Payload. This is transitted to an EmonCMS platform for 
// logging and usage. See https://openenergymonitor.org
typedef struct {
  int battery;
  int level;
  int temperature;
  int humidity;
} Payload;
Payload pool_level;


// for sleeping
unsigned long WDT_number;
unsigned long now, start;

//Config via serial on boot
const char helpText1[] PROGMEM =                                 // Available Serial Commands
"\n"
"Available commands:\n"
"  <nn> i     - set node IDs (standard node ids are 1..30)\n"
"  <n> b      - set MHz band (4 = 433, 8 = 868, 9 = 915)\n"
"  <nnn> g    - set network group (RFM12 only allows 212, 0 = any)\n"
"  s          - save config to EEPROM\n"
"  v          - Show firmware version\n"
;


//################################################################################################################################
//################################################################################################################################
#ifndef UNIT_TEST // IMPORTANT LINE! // http://docs.platformio.org/en/stable/plus/unit-testing.html

void setup() {
//################################################################################################################################

  pinMode(LED,OUTPUT); digitalWrite(LED,HIGH);                       // Status LED on

  // Unused pins configure as input pull up for low power
  // http://electronics.stackexchange.com/questions/43460/how-should-unused-i-o-pins-be-configured-on-atmega328p-for-lowest-power-consumpt
  // port map: https://github.com/openenergymonitor/pool_level2/blob/master/hardware/readme.md
  
  pinMode(4, INPUT_PULLUP);
  pinMode(5, INPUT_PULLUP);                                  
  pinMode(6, INPUT_PULLUP);                                 
  pinMode(14, INPUT_PULLUP);
  pinMode(16, INPUT_PULLUP);
  pinMode(20, INPUT_PULLUP);
  pinMode(21, INPUT_PULLUP);
  pinMode(17, INPUT_PULLUP);
  pinMode(3, INPUT_PULLUP);
  pinMode(BATT_ADC, INPUT);

  if (debug==1)
  {
    Serial.begin(9600);
    delay(50);
    Serial.println("Pool Control Master");
    Serial.println("emonTH_V2_pool_level_sensor_20190208_dual_float_sensor.ino");
    Serial.println("Dual Float Pool Water Level Sensor");
    Serial.println("For more info visit:  https://github.com/rjsears/Pool_Fill_Control");
    Serial.println("");
    delay(100);
   }

RF_STATUS=1;   

  if (RF_STATUS==1)
  {
    load_config();                                                        // Load RF config from EEPROM (if any exist)

    if (debug) Serial.println("Int RFM...");
    rf12_initialize(nodeID, RF_freq, networkGroup);                       // Initialize RFM

    if (debug)
    {
      Serial.println("RFM Started");
      Serial.print("Node: ");
      Serial.print(nodeID);
      Serial.print(" Freq: 433Mhz");
      Serial.print(" Network: ");
      Serial.println(networkGroup);
    }
    
    // Send RFM69CW test sequence (for factory testing)
    for (int i=10; i>-1; i--)
    {
      pool_level.temperature=i;
      rf12_sendNow(0, &pool_level, sizeof pool_level);
      delay(100);
    }
    rf12_sendWait(2);
    pool_level.temperature=0;
    // end of factory test sequence
    rf12_sleep(RF12_SLEEP);
  }

  
  //########################################
  // Setup and check for presence of SI7201
  //########################################
  if (debug) 
  Serial.println("Int SI7201..");

  // check if the I2C lines are HIGH
  if (digitalRead(SDA) == HIGH || digitalRead(SCL) == HIGH)
  {
    SI7021_sensor.begin();
    int deviceid = SI7021_sensor.getDeviceId();
    if (deviceid!=0) {
      SI7021_status=1;
      if (debug)
      {
        si7021_env data = SI7021_sensor.getHumidityAndTemperature();
        Serial.print("SI7021 Started, ID: ");
        Serial.println(deviceid);
        Serial.print("SI7021 t: "); Serial.println(data.fahrenheitHundredths/100.0);
        Serial.print("SI7021 h: "); Serial.println(data.humidityBasisPoints/100.0);
      }
    }
    else {
      SI7021_status=0;
      if (debug) Serial.println("SI7021 Error");
    }
  }
  else {
    SI7021_status=0;
    if (debug) Serial.println("SI7021 Error");
  }

  //################################################################################################################################
  // RF Config mode
  //################################################################################################################################
  if (RF_STATUS==1){
    Serial.println("");
    Serial.println("'+++' then [Enter] for RF config mode");
    Serial.println("waiting 10s...");
    start = millis();
    while (millis() < (start + 10000)){
      // If serial input of keyword string '+++' is entered during 5s power-up then enter config mode
      if (Serial.available()){
        if ( Serial.readString() == "+++\r\n"){
          Serial.println("Entering config mode...");
          showString(helpText1);
          // char c[]="v"
          config(char('v'));
          while(1){
            if (Serial.available()){
              config(Serial.read());
            }
          }
        }
      }
    }
  }

  //################################################################################################################################
  // Power Save  - turn off what we don't need - http://www.nongnu.org/avr-libc/user-manual/group__avr__power.html
  //################################################################################################################################
  ACSR |= (1 << ACD);                     // disable Analog comparator
  if (debug==0) power_usart0_disable();   //disable serial UART
  power_twi_disable();                    //Two Wire Interface module:
  power_spi_disable();
  power_timer1_disable();
 // power_timer0_disable();              //don't disable necessary for the DS18B20 library

  // Only turn off LED if both sensor and RF69CW are working
  if ((RF_STATUS) && (SI7021_status)){
    digitalWrite(LED,LOW);                  // turn off LED to indciate end setup
  }
} // end of setup


//################################################################################################################################
//################################################################################################################################
void loop()
//################################################################################################################################
{
  
  if (Sleepy::loseSomeTime(WDT_PERIOD)==1) {
    WDT_number++;
  }

  if (WDT_number>=WDT_MAX_NUMBER)
  {
    cli();
    sei();

   pool_level.battery=int(analogRead(BATT_ADC)*0.03225806);  //read battery voltage, convert ADC to volts x10


// Here is where we read our float states and determine if the pool is (0) LOW, (1) Midway or (2) FULL

  UPPER_Float = digitalRead(17);
  LOWER_Float = digitalRead(3);

   if (UPPER_Float == LOW)
   {
     UPPER_Float_Position = "Closed";
   }
   else
   {
     UPPER_Float_Position = "Open";
   }

   if (LOWER_Float == LOW)
   {
     LOWER_Float_Position = "Closed";
   }
   else
   {
     LOWER_Float_Position = "Open";
   }

   if ((UPPER_Float == LOW) && (LOWER_Float == LOW))                    // If both floats are closed, pool is full
   {
    pool_level.level = 2;
   }
   else if ((UPPER_Float == HIGH) && (LOWER_Float == LOW))              // If upper float is open and lower is closed, pool is midway
   {
    pool_level.level = 1;
   }
   else
   {
    pool_level.level = 0;                                               // Both floats open = Pool low and we need to add water
   }

    // Read SI7201
    // Read from SI7021 SPI temp & humidity sensor
    if (SI7021_status==1){
      power_twi_enable();
      si7021_env data = SI7021_sensor.getHumidityAndTemperature();
      pool_level.temperature = (data.fahrenheitHundredths);
      pool_level.humidity = (data.humidityBasisPoints);
      power_twi_disable();
    }


    // Send data via RF
    if (RF_STATUS){
      power_spi_enable();
      rf12_sleep(RF12_WAKEUP);
      dodelay(30);                                   // wait for module to wakup
      rf12_sendNow(0, &pool_level, sizeof pool_level);
      // set the sync mode to 2 if the fuses are still the Arduino default
      // mode 3 (full powerdown) can only be used with 258 CK startup fuses
      rf12_sendWait(2);
      rf12_sleep(RF12_SLEEP);
      dodelay(100);
      power_spi_disable();
    }

    if (debug){
      digitalWrite(LED,HIGH);
      delay(100);   
      digitalWrite(LED,LOW);
      delay(100);
      Serial.print("Pool Level is ");
      if (pool_level.level == 0) Serial.println("LOW");
      if (pool_level.level == 1) Serial.println("MIDWAY");
      if (pool_level.level == 2) Serial.println("FULL");
      Serial.print("UPPER Float: ");
      Serial.println(UPPER_Float_Position);
      Serial.print("LOWER Float: ");
      Serial.println(LOWER_Float_Position);
    
      delay(100);
      Serial.print("Pool Level Sensor Housing Internal Temperature: ");
      Serial.print(pool_level.temperature*.01);
      Serial.println("°F");
      delay(100);
      Serial.print("Pool Level Sensor Housing Internal Humidity: ");
      Serial.print(pool_level.humidity*.01);
      Serial.println("%");
      delay(100);
      Serial.print("Battery voltage: ");
      Serial.print(pool_level.battery/10);
      Serial.print("V, ");
      delay(100);
      Serial.println();
      delay(5);
    } // end serial print debug


    unsigned long last = now;
    now = millis();
    WDT_number=0;
  } // end WDT

} // end loop


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

// Used to test for RFM69CW prescence
static void writeReg (uint8_t addr, uint8_t value) {
    RF69::control(addr | 0x80, value);
}

static uint8_t readReg (uint8_t addr) {
    return RF69::control(addr, 0);
}


#endif    // IMPORTANT LINE! end unit test
//http://docs.platformio.org/en/stable/plus/unit-testing.html
