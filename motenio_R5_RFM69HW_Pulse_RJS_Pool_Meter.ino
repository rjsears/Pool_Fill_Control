/* 


** moteino_R5_RFM69HW_Pulse_RJS_Pool_Meter
** Node 28
** 433Mhz


RJS PulseMeter V2.0 Moteino 9/25/2017



  This sketch is designed to read pulses from a water meter using a low-power, battery operated Moteino R4 (http://www.moteino.com). 
  This sketch is derived from different sketches from both moteino.com and openenergymonitor.org. Many thanks to all who have helped
  in this process. Parts of this sketch are derived from a sketch that Felix at LowPowerLabs wrote called PulseMeter. It has been 
  modified to work for my situation. 

  While the Moteino can transmit information to it's own gateway, I am using a RaspberryPi (emonPi) created and maintained by the folks
  at Open Energy Monitoring. I then take this information and write it to a privately hosted version of emoncms, although you could also
  use the free emoncms hoting provided by http://emoncms.org

  While every effort has been made to keep the power consumption as low as possible, I am sure it could be better, so this should be 
  considered a starting point!

  The particular meters I am using output 10 pulses per gallon using a reed style switch. 

  I was having a bunch of problems debouncing in software as my water meters would kick out upwards of 300 pulses per minute. I tried a variety 
  of options but was never quite able to get it right, so I spent $2.00 on a Max6816 digital debouncer (thanks MikeSims). It works like magic! 

  In addition, the Moteinos that I am using have onboard flash, so I write the pulsecount every minute to the flash, this way I never lose (or reset)
  my overall pulsecount. In addition, you can wirelessly program the Moteinos which is very nice.

  

  
  How to connect a two wire reed meter to your Moteino (if you are not using a physical debouncer)
  .......................
  1) Connect one of the leads of the meter to 3.3v
  2) Connect the other lead to a 10k ohm resistor.
  3) Connect the same end of this resistor to pin D3 (INT1).
  4) Connect the other end of the resistor to ground.  


  How to connect a two wire reed meter to your Moteino (if you are using the Max6816 physical debouncer)
  .......................
  1) Connect VCC on Max6816 to 3.3v.
  2) Connect Ground on Max6816 to ground.
  3) Connect a .1uF cap between VCC and Ground on Max 6816. (May not be needed...I added it anyway).
  4) Connect one lead from water meter to IN on Max6816.
  5) Connect the other lead from the meter to ground.
  6) Finally connect the OUT on the MAX6816 to D3.

  
  Again, this is designed to talk directly to an emonpi not to a moteino gateway, so if you want to talk to a gateway,
  you will need to make modifications to this sketch.

  

 This is what my emonhub.conf looks like:

 
[[28]]
    nodename = pool_water_meter
    firmware = moteino_R5_RFM69HW_Pulse_RJS_Pool_Meter
    hardware = moteino_R5
    [[[rx]]]
       names = GAL, GPM, GLM
       datacodes = f,f,f
       scales = 1,1,1
       units = G,G,G




  
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


//*********************************************************************************************
//***********  Include these libraries:
//*********************************************************************************************
#include <RFM69.h>         //get it here: http://github.com/lowpowerlab/rfm69
#include <SPIFlash.h>      //get it here: http://github.com/lowpowerlab/spiflash
#include <WirelessHEX69.h> //get it here: https://github.com/LowPowerLab/WirelessProgramming
#include <EEPROM.h>
#include <SPI.h>
#include <TimerOne.h>
#include <JeeLib.h>
#include <avr/power.h>
#include <avr/sleep.h>


 
//*********************************************************************************************
ISR(WDT_vect) {
  Sleepy::watchdogEvent();
} // Attached JeeLib sleep function to Atmega328 watchdog - enables MCU to be put into sleep mode between readings to reduce power consumption
//*********************************************************************************************


//*********************************************************************************************
//***********  Here is where we setup our flash if we have it. 
//*********************************************************************************************
#ifdef __AVR_ATmega1284P__
  #define LED           15 // Moteino MEGAs have LEDs on D15
  #define INTERRUPTPIN   1  //INT1 = digital pin 11 (must be a hardware interrupt pin!)
  #define FLASH_SS      23 // and FLASH SS on D23
#else
  #define LED            9 // Moteinos have LEDs on D9
  #define INTERRUPTPIN   1  //INT1 = digital pin 3 (must be a hardware interrupt pin!)
  #define FLASH_SS       8 // and FLASH SS on D8
#endif

#define wireless_programming   1       // Set to 1 to allow wireless programming, 0 to disable. If you enable, you must enable use_flash
#define use_flash              1      // Are we going to use the flash? If not, we can put it to sleep and save some power...

SPIFlash flash(FLASH_SS, 0xEF30); //WINDBOND 4MBIT flash chip on CS pin D8 (default for Moteino)

//*********************************************************************************************


//*********************************************************************************************
//************  Here is all the radio stuff, change to meet your configuration!! **************
//*********************************************************************************************
RFM69 radio;
#define RF_freq RF12_433MHZ               // Frequency of RF12B module can be RF12_433MHZ, RF12_868MHZ or RF12_915MHZ. You should use the one matching the module you have.
#define IS_HIGHPOWER   true               // True only for RFM69HW High Power RFM69
int nodeID = 28;                          // Node ID - should be unique on network - I use 30 for testing
const int networkGroup = 210;             // Network group                                                                           
//*********************************************************************************************



//*********************************************************************************************
//************  Here is all the pulse stuff, change to meet your configuration!! **************
//*********************************************************************************************
#define PULSESPERGALLON    10 //how many pulses from sensor equal 1 gallon
#define GPMTHRESHOLD       8000  // GPM will reset after this many MS if no pulses are registered
#define XMITPERIOD         5000  // GPMthreshold should be less than 2*XMITPERIOD

volatile byte ledState = LOW;
volatile unsigned long PulseCounterVolatile = 0; // use volatile for shared variables
unsigned long NOW = 0;
unsigned long PulseCounter = 0;
unsigned long LASTMINUTEMARK = 0;
unsigned long PULSECOUNTLASTMINUTEMARK = 0; //keeps pulse count at the last minute mark

byte COUNTEREEPROMSLOTS = 10;
unsigned long COUNTERADDRBASE = 8; //address in EEPROM that points to the first possible slot for a counter
unsigned long COUNTERADDR = 0;     //address in EEPROM that points to the latest Counter in EEPROM
byte secondCounter = 0;

unsigned long TIMESTAMP_pulse_prev = 0;
unsigned long TIMESTAMP_pulse_curr = 0;
int pulseAVGInterval = 0;
int pulsesPerXMITperiod = 0;
//
int newgal = 67100;
//

float GALlast=0;
float GPMlast=0;
float GLMlast=0;

// What information are we going to be transmitting back to our gateway?

typedef struct {                             // RF payload datastructure
  float GAL;
  float GPM;
  float GLM;                                             
} Payload;
Payload water;


//################################################################################################################################
//################################################################################################################################
void setup() {
//################################################################################################################################

pinMode(LED,OUTPUT); digitalWrite(LED,HIGH);                       // Status LED on



// Because of the Moteino, we are using two different radio libraries to control the radio. rf_12 (jeelib) and radio (RFM69).
// We only use the radio() commands to control the power output and the sleeping. If you have the HW radio, I have found that
// you must use the radio.setHighPower() or the radio simply will not transmit. At some point I will dig through the libraries
// and adjust this so we do not need both libraries.


//*********************************************************************************************
//***********  Initialize our radio. I use the High Power version of the RFM69. 
//********************************************************************************************* 
   rf12_initialize(nodeID, RF_freq, networkGroup);     
   if(IS_HIGHPOWER) radio.setHighPower();              // If we are using the RFM69HW version of the radio, set it to high power
   rf12_sleep(RF12_SLEEP);
   radio.sleep();

//*********************************************************************************************
// Since we are using a Moteino with onboard flash, we are able to save our meter readings to 
// flash so we do not lose them in the  event of a power outage or other problem. Here is where 
// we initialize our counter from flash.
//*********************************************************************************************

  unsigned long savedCounter = EEPROM_Read_Counter();
  if (savedCounter <=0) savedCounter = 1; //avoid division by 0
  PulseCounterVolatile = PulseCounter = PULSECOUNTLASTMINUTEMARK = savedCounter;
  attachInterrupt(INTERRUPTPIN, pulseCounterInterrupt, RISING);
  Timer1.initialize(XMITPERIOD * 1000L);
  Timer1.attachInterrupt(XMIT);
  


//*********************************************************************************************
//***********  If we are not going to use flash, we can put it to sleep to save power. 
//*********************************************************************************************

if (!use_flash)
   {
    flash_sleep();
   }



//*********************************************************************************************
//***********  If debug mode is set above, output some useful information to the serial port. 
//********************************************************************************************* 
  
  if (debug)        
  {
    Serial.begin(serial_speed);
        if (use_flash)
        {
    Serial.println("Checking for presence of onboard Flash...");
       if (flash.initialize())
  {
    Serial.println("Onboard Flash Detected...attempting to initialize...");
    dodelay(1000);
    Serial.println("SPI Flash Init OK!");
    Serial.println();
  }
  else
    Serial.println("SPI Flash Init FAIL! (is chip present?)");
    Serial.println();
        }
        else
          Serial.println("Flash Not in Use, We are putting it to sleep to save power....");
    dodelay(100);
    Serial.println("moteino_RFM69HW_PULSE_Pool_Meter");
    Serial.println(); 
    #if (RF69_COMPAT)
      Serial.println("RFM69HW Radio Initialized");
      Serial.println();
    #else
      Serial.println("RFM12B Initialized");
      Serial.println();
    #endif
    Serial.print("Node: "); 
    Serial.print(nodeID); 
    Serial.print(",  Freq: "); 
    if (RF_freq == RF12_433MHZ) Serial.print("433Mhz");
    if (RF_freq == RF12_868MHZ) Serial.print("868Mhz");
    if (RF_freq == RF12_915MHZ) Serial.print("915Mhz"); 
    Serial.print(",  Network: "); 
    Serial.println(networkGroup);
    Serial.println();
    dodelay(1000);
  }


//*********************************************************************************************
//***********  Shut off some other things we do not need to save power. 
//*********************************************************************************************

 reduce_power();


//*********************************************************************************************
//***********  All done with our setup. 
//*********************************************************************************************

} 


//################################################################################################################################
//################################################################################################################################
void loop() 
//################################################################################################################################
{


//*********************************************************************************************
//*********** If you want to wireless program your Mote, set this to True above.
//*********************************************************************************************

  if (use_flash && wireless_programming)
  {
  CheckForWirelessHEX(radio, flash, true);
  }
 
}


//*********************************************************************************************
//**** Configure our interrupts, setup counters and timers and configure transmittions.
//*********************************************************************************************

void pulseCounterInterrupt()
{
  noInterrupts();
  ledState = !ledState;
  PulseCounterVolatile++;  // increase when LED turns on
  digitalWrite(LED, ledState);
  NOW = millis();

  //remember how long between pulses (sliding window)
  TIMESTAMP_pulse_prev = TIMESTAMP_pulse_curr;
  TIMESTAMP_pulse_curr = NOW;
  
  if (TIMESTAMP_pulse_curr - TIMESTAMP_pulse_prev > GPMTHRESHOLD)
    //more than 'GPMthreshold' seconds passed since last pulse... resetting GPM
    pulsesPerXMITperiod=pulseAVGInterval=0;
  else
  {
    pulsesPerXMITperiod++;
    pulseAVGInterval += TIMESTAMP_pulse_curr - TIMESTAMP_pulse_prev;
  }
  interrupts();
}



void XMIT()
{
  noInterrupts();
  PulseCounter = PulseCounterVolatile;
  interrupts();
  
  if (millis() - TIMESTAMP_pulse_curr >= 5000)
  {
    ledState = !ledState;
    digitalWrite(LED, ledState);
  }


//calculate Gallons counter 
  water.GAL = ((float)PulseCounter)/PULSESPERGALLON;

  //calculate & output GPM
  water.GPM = pulseAVGInterval > 0 ? 60.0 * 1000 * (1.0/PULSESPERGALLON)/(pulseAVGInterval/pulsesPerXMITperiod):0;
  pulsesPerXMITperiod = 0;
  pulseAVGInterval = 0;
  secondCounter += XMITPERIOD/1000;



//*********************************************************************************************
//*********** Once per minute, put out a GallonsLastMinute count.
//*********************************************************************************************
 
  if (secondCounter>=60)
  {
    if (debug)
    {
    Serial.println("60sec mark ... ");
    }
    secondCounter=0;
    water.GLM = ((float)(PulseCounter - PULSECOUNTLASTMINUTEMARK))/PULSESPERGALLON;
    PULSECOUNTLASTMINUTEMARK = PulseCounter;
    EEPROM_Write_Counter(PulseCounter);

    if (debug)
    {
      Serial.print("GAL: "); Serial.print(water.GAL);
      Serial.print(", GPM: "); Serial.print(water.GPM);
      Serial.print(", GLM: "); Serial.println(water.GLM);
    } 

  }
  else
  {
    if (debug)
    {
      Serial.print("GAL: "); Serial.print(water.GAL);
      Serial.print(", GPM: "); Serial.println(water.GPM); 
    }
  }


//*********************************************************************************************
//*********** We only transmit if there are changes to send...helps to save power....
//*********************************************************************************************

  if (water.GPM!=GPMlast || water.GAL!=GALlast || water.GLM!=GLMlast)  //Check and see if we used any water.....
  {
    power_spi_enable();
    
    if (debug)
       {
       Serial.println("Time to transmit.......");
       }
    
    rf12_sleep(RF12_WAKEUP);
    dodelay(100);
    rf12_sendNow(0, &water, sizeof water);
    rf12_sendWait(2);

//*********************************************************************************************
//*********** Reset our readings so we know when to transmit again...
//*********************************************************************************************

    GALlast = water.GAL;
    GPMlast = water.GPM;
    GLMlast = water.GLM;
    
    power_spi_disable();
   }


}




//*********************************************************************************************
//*********** Flash/EEProm and powersaving Subroutines
//*********************************************************************************************


unsigned long EEPROM_Read_Counter()

{
  return EEPROM_Read_ULong(EEPROM_Read_ULong(COUNTERADDR));
}



void EEPROM_Write_Counter(unsigned long counterNow)

{
  if (counterNow == EEPROM_Read_Counter())
  {
    if (debug)
      {
      Serial.print("{EEPROM-SKIP(no changes)}");
      }   
    return; //skip if nothing changed
  }
  if (debug)
     {
     Serial.print("{EEPROM-SAVE(");
     Serial.print(EEPROM_Read_ULong(COUNTERADDR));
     Serial.print(")=");
     Serial.print(PulseCounter);
     Serial.print("}");
     }
    
  unsigned long CounterAddr = EEPROM_Read_ULong(COUNTERADDR);
  if (CounterAddr == COUNTERADDRBASE+8*(COUNTEREEPROMSLOTS-1))
    CounterAddr = COUNTERADDRBASE;
  else CounterAddr += 8;
  
  
  EEPROM_Write_ULong(CounterAddr, counterNow);
  EEPROM_Write_ULong(COUNTERADDR, CounterAddr);
}





unsigned long EEPROM_Read_ULong(int address)
{
  unsigned long temp;
  for (byte i=0; i<8; i++)
    temp = (temp << 8) + EEPROM.read(address++);
  return temp;
}





void EEPROM_Write_ULong(int address, unsigned long data)
{
  for (byte i=0; i<8; i++)
  {
    EEPROM.write(address+7-i, data);
    data = data >> 8;
  }
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


//******************************************************************************************************
// If we are not going to be using flash, there are some power savings things we can do. Here we make 
// sure the flash pin is set to OUTPUT and HIGH so that it is not floating if we are not going to use it. 
//******************************************************************************************************

void flash_sleep()
{
  pinMode(FLASH_SS, OUTPUT);                                 // Added to make sure flash stays asleep and does not use power!
  digitalWrite(FLASH_SS, HIGH);
  flash.sleep();  
}



/**
 * Turn off what we don't need.
 * see http://www.nongnu.org/avr-libc/user-manual/group__avr__power.html
 */
void reduce_power()
{
  // Shut off the LED for now....
  digitalWrite(LED,LOW);
  
  // Put the radio into sleep mode until we need it
  rf12_sleep(RF12_SLEEP);                             // Put the radio to sleep using both libraries
  radio.sleep();
 

  ACSR |= (1 << ACD);              // Disable Analog comparator
  power_twi_disable();             // Disable the Two Wire Interface module.
  
  power_spi_disable();             // Serial peripheral interface

  if (!debug)
  {
    power_usart0_disable();        // Disable serial UART if not in debug
  }

  power_timer0_enable();           // Necessary for this sketch
  power_timer1_enable();           // Necessary for this sketch
 
}
