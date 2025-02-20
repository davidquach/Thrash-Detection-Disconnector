#include <Wire.h>
#include <HT_SSD1306Wire.h> // OLED library
#include <TimeLib.h>
#include <HX711.h>          // HX711 library

// low power libraries
#include "Arduino.h"
//#include "LoRa_APP.h"

// low power constants
#define timetillsleep 10000
#define timetillwakeup 500
static TimerEvent_t sleep;
static TimerEvent_t wakeUp;
uint8_t lowpower=1;

// HX711 declarations
// #define DOUT GPIO5
// #define SCK GPIO6
#define DOUT GPIO8
#define SCK GPIO9
HX711 scale;

float calibration_factor = -1.966;
// float calibration_factor = 10.0;
float units;
float ounces;
float pounds;

// Button pins
int resetButton = GPIO1;
int menueButton1 = GPIO2;
int menueButton2 = GPIO3;
int menueButton3 = GPIO4;

// LED pins
int ledPin = GPIO11;
int flashLed = GPIO12;
// int rgbLed1 = GPIO8;
// int rgbLed2 = GPIO9;
int rgbLed1 = GPIO5;
int rgbLed2 = GPIO6;
int rgbLed3 = GPIO7;

// Constants and flags
int threshold = 50;
int maxValues = 5;
int flag = 0;

// Button state flags
volatile bool resetPressed = false;
volatile bool menuBackPressed = false;
volatile bool menuForwardPressed = false;
volatile bool menuConfirmPressed = false;

unsigned long debounceDelay = 50;
unsigned long lastDebounceReset = 0;
unsigned long lastDebounceMenuBack = 0;
unsigned long lastDebounceMenuForward = 0;
unsigned long lastDebounceMenuConfirm = 0;

// Display Global Variables
int battery = 0;
int peakCnt = 0;

// Timer 
unsigned long peakTimer = 0;  // Stores the last peak time
const unsigned long countdownTime = 20000;  // 20 seconds
bool timerActive = false;  // Flag for active timer

// OLED setup
SSD1306Wire display(0x3c, 500000, SDA, SCL, GEOMETRY_128_64, GPIO10);
unsigned long lastOLEDUpdate = 0;
unsigned long oledUpdateInterval = 50; // 1/4-second interval for OLED update

// data logging struct
struct logEntry {
  unsigned long timestamp;
  float strain;
};

void displayBootScreen() {
    display.clear();
    display.setTextAlignment(TEXT_ALIGN_CENTER);
    display.setFont(ArialMT_Plain_24);
    display.drawString(display.getWidth() / 2, 5, "Nova");
    display.drawString(display.getWidth() / 2, 25, "Robotics");
    display.display();
    delay(1000); // Display boot screen for 3 seconds
    display.clear();
}

// low power functions
void onSleep()
{
  lowpower=1;
  TimerSetValue( &wakeUp, timetillwakeup );
  TimerStart( &wakeUp );
}
void onWakeUp()
{
  lowpower=0;
  TimerSetValue( &sleep, timetillsleep );
  TimerStart( &sleep );
}

void setup() {
    Serial.begin(9600);
    scale.begin(DOUT, SCK, 128);
    scale.set_scale(calibration_factor);
    scale.set_gain(64);
    scale.tare();
    delay(500);

    // Initialize buttons with interrupts
    pinMode(resetButton, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(resetButton), handleResetPress, FALLING);
    pinMode(menueButton1, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(menueButton1), handleMenuBackPress, FALLING);
    pinMode(menueButton2, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(menueButton2), handleMenuForwardPress, FALLING);
    pinMode(menueButton3, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(menueButton3), handleMenuConfirmPress, FALLING);

    // Initialize LEDs
    pinMode(ledPin, OUTPUT);
    pinMode(flashLed, OUTPUT);
    pinMode(rgbLed1, OUTPUT);
    pinMode(rgbLed2, OUTPUT);
    pinMode(rgbLed3, OUTPUT);

    // Initialize OLED
    display.init();
    displayBootScreen();

  // low power setup
  //Radio.Sleep( );
  TimerInit( &sleep, onSleep );
  TimerInit( &wakeUp, onWakeUp );
  onSleep();
}

//------------------------------------------------------------------------------------------------------------------------------------------------------------
// Display Battery 

void displayStrain() {
    display.clear();
    display.setTextAlignment(TEXT_ALIGN_LEFT);

    // Get strain gauge readings
    double strainUnits = scale.get_units(5); // Adjust number of samples as needed
    if (strainUnits < 0) strainUnits = 0.0;  // Ensure no negative values
    double strainOunces = strainUnits * 0.035274 / 100;
    
    display.setFont(ArialMT_Plain_10);
    display.drawString(0, 0, "Strain Reading:");
    display.drawString(0, 12, String(strainUnits, 2) + " units");
    display.drawString(0, 24, String(strainOunces, 2) + " oz");
    display.drawString(0, 36, "Threshold : " + String(threshold));   // Adjust Y value as needed
    display.drawString(0, 48, "Calibration : " + String(calibration_factor));   // Adjust Y value as needed


    // Peak Detection
    for(int i = 0; i < flag && i < 5; i++) {
      display.drawString(80 + (i * 8), 0, "*");
    }

    display.display();
}

void drawConfig() {
  display.clear();
  display.setTextAlignment(TEXT_ALIGN_LEFT);

  // BATTERY DISPLAY
  int battery_level = 100; // Change to reflect current battery level
  display.drawString(0, 0, "Battery Level  " + String(battery) + "%");
  display.drawProgressBar(0, 15, 120, 10, battery_level);

  // UPTIME DISPLAY
  static unsigned long uptime = 0;
  uptime = millis() / 1000; // Calculate uptime in seconds
  int hours = uptime / 3600;
  int minutes = (uptime % 3600) / 60;
  int seconds = uptime % 60;
  display.drawString(0, 30, "Device Uptime:");
  display.drawString(0, 45, String(hours) + "h " + String(minutes) + "m " + String(seconds) + "s");
  
  display.display();
}

// Screen Variables
int screenMode = 0; 
typedef void (*Screen)(void);
Screen screens[] = {displayStrain, drawConfig};
int screenLength = (sizeof(screens) / sizeof(Screen));

// Windowing 
int window_size = 5;
float window[5] = {0, 0, 0, 0, 0};  

//------------------------------------------------------------------------------------------------------------------------------------------------------------

bool isPeak(int index) {
    if (index == 0 || index == 9) {
        return false;
    }

    return (window[index] > window[index - 1] + threshold && window[index] > window[index + 1] + threshold);
}

void loop() {

  if(lowpower){
    lowPowerHandler();
  }

  // Non-blocking OLED updates
  if (millis() - lastOLEDUpdate >= oledUpdateInterval) {
    lastOLEDUpdate = millis();
    screens[screenMode]();
  }

  // Handle button presses
  if (resetPressed) {
    resetPressed = false;
    digitalWrite(ledPin, HIGH);
    scale.tare();
    flag = 0;
    delay(500);
    digitalWrite(ledPin, LOW);
  }

  if (menuBackPressed) {
    menuBackPressed = false;
    digitalWrite(rgbLed1, LOW);
    digitalWrite(rgbLed2, LOW);
    digitalWrite(rgbLed3, HIGH);
    delay(500);
    digitalWrite(rgbLed3, LOW);
  }

  if (menuForwardPressed) {
    menuForwardPressed = false;
    digitalWrite(rgbLed1, HIGH);
    digitalWrite(rgbLed2, LOW);
    digitalWrite(rgbLed3, LOW);
    delay(500);
    digitalWrite(rgbLed1, LOW);
  }

  if (menuConfirmPressed) {
    menuConfirmPressed = false;
    digitalWrite(rgbLed1, LOW);
    digitalWrite(rgbLed2, HIGH);
    digitalWrite(rgbLed3, LOW);
    delay(500);
    digitalWrite(rgbLed2, LOW);
  }

  // Read HX711 scale values
  // units = scale.get_units(1);
  // ounces = abs(units * 0.035274) / 100;

  units = scale.get_units(5);
  ounces = abs(units * 0.035274 / 100);

  // Serial.print("Ounces: ");
  Serial.println(ounces);
  // Serial.print("Raw: ");
  // Serial.println(scale.read());
  // Serial.print("Units: ");
  // Serial.println(units);
  // Serial.print("Value: ");
  // Serial.println(scale.get_value(1));
  // Serial.println("");
  

  if (Serial.available() > 0) {
    String inputString = Serial.readStringUntil('\n');  // Read input from the serial buffer
    inputString.trim();  // Remove leading/trailing spaces

    if (inputString.length() > 1) {
      char identifier = inputString.charAt(0);  // First character tells us if it's threshold or calibration
      String valueString = inputString.substring(1);  // The remaining part is the value
      int receivedValue = valueString.toInt();  // Convert value to integer

      if (receivedValue > 0) {  // Ensure the value is positive
        if (identifier == 'T') {
          threshold = receivedValue;
        } else if (identifier == 'C') {
          calibration_factor = receivedValue;
        }
      }
    }
  }

  //Shift Window
  for (int i = window_size - 1; i > 0; i--) {
        window[i] = window[i - 1];
    }
  
  window[0] = ounces;

  // Peak Detection Compulation
    if (isPeak(1)) {
        peakCnt += 1;
        peakTimer = millis();  // Reset timer when peak is detected
        timerActive = true;  // Start the countdown
        
        
        // {p}{peak #}{peak in oz}
        Serial.print("p");
        Serial.print(peakCnt);
        Serial.println(window[1]);      
    }

  //   // Timer logic
    if (timerActive) {
        unsigned long timeLeft = (countdownTime - (millis() - peakTimer)) / 1000;
        
        if (millis() - peakTimer >= countdownTime) {
            Serial.println("pz");
            peakCnt = 0;
            timerActive = false;  // Stop the countdown
            
        } 
        // else {
        //     Serial.print("Time remaining: ");
        //     Serial.print(timeLeft);
        //     Serial.println(" seconds");
        // }
    }

  if (peakCnt == 3) {
    peakCnt = 0; // Reset Peak Count  
    Serial.println("px");
  }
}


void ledFlash() {
  for (int i = 0; i < 5; i++) {
    digitalWrite(flashLed, HIGH);
    delay(500);
    digitalWrite(flashLed, LOW);
    delay(500);
  }
}

void handleResetPress() {
  if ((millis() - lastDebounceReset) > debounceDelay) {
    resetPressed = true;
    lastDebounceReset = millis();
  }
}

void handleMenuBackPress() {
  if ((millis() - lastDebounceMenuBack) > debounceDelay) {
    screenMode = (screenMode + 1)  % screenLength;
    menuBackPressed = true;
    lastDebounceMenuBack = millis();
  }
}

void handleMenuForwardPress() {
  if ((millis() - lastDebounceMenuForward) > debounceDelay) {
    screenMode = (screenMode + 1)  % screenLength;
    menuForwardPressed = true;
    lastDebounceMenuForward = millis();
  }
}

void handleMenuConfirmPress() {
  if ((millis() - lastDebounceMenuConfirm) > debounceDelay) {
    menuConfirmPressed = true;
    lastDebounceMenuConfirm = millis();
  }
}
