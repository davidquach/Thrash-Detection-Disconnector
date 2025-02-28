#include <Wire.h>
#include <HT_SSD1306Wire.h> // OLED library
#include <TimeLib.h>
#include <HX711.h>          // HX711 library

// low power libraries
#include "Arduino.h"

// low power constants
#define timetillsleep 30000
#define timetillwakeup 5000
static TimerEvent_t sleep;
static TimerEvent_t wakeUp;
uint8_t lowpower=1;

// HX711 declarations
#define DOUT GPIO13
#define SCK GPIO14
// #define DOUT GPIO12
// #define SCK GPIO13
HX711 scale;

float calibration_factor = -0.0433;
float units;
float ounces;
float pounds;

// Button pins
int resetButton = GPIO4;
int menueButton1 = GPIO3;
int menueButton2 = GPIO2;
int menueButton3 = GPIO1;

// LED pins
int ledPin = GPIO8;
int flashLed = GPIO9;
int rgbLed1 = GPIO5;
int rgbLed2 = GPIO6;
int rgbLed3 = GPIO7;

// Constants and flags
int threshold = 10;
int maxValues = 5;
int flag = 0;

bool peakActive = false;

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

unsigned long lastSampleTime = 0;
unsigned long sampleInterval = 500; // Delay between samples

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
    delay(100); 
    display.clear();
}

// low power functions
void onSleep()
{
  if (timerActive) {
    // If a peak has been detected, do not allow sleep
    Serial.println("Peak detected, skipping sleep");
    TimerSetValue(&sleep, timetillsleep); // Reset sleep timer
    TimerStart(&sleep);
    return;
  }

  Serial.println("LP");
  lowpower=1;
  //timetillwakeup ms later wake up;  
  TimerSetValue( &wakeUp, timetillwakeup );
  TimerStart( &wakeUp );
}

void onWakeUp()
{
  Serial.println("WU");
  lowpower=0;
  //timetillsleep ms later into lowpower mode;
  TimerSetValue( &sleep, timetillsleep );
  TimerStart( &sleep );
}



void setup() {
    Serial.begin(9600);
    scale.begin(DOUT, SCK, 128);
    scale.set_scale(calibration_factor);
    scale.set_gain(64);
    //scale.set_gain(128);
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

    TimerInit( &sleep, onSleep );
    TimerInit( &wakeUp, onWakeUp );
    onSleep();
}

//------------------------------------------------------------------------------------------------------------------------------------------------------------
// Display Battery 

void displayStrain() {
    display.clear();
    display.setTextAlignment(TEXT_ALIGN_LEFT);

    display.setFont(ArialMT_Plain_10);
    display.drawString(0, 0, "Strain Reading:");
    display.drawString(0, 12, String(ounces, 2) + " units");
    display.drawString(0, 24, String(units, 2) + " oz");
    display.drawString(0, 36, "Threshold : " + String(threshold));
    display.drawString(0, 48, "Calibration : " + String(calibration_factor));

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

  if (millis() - lastSampleTime >= sampleInterval) {
    units = scale.get_units(1);
    ounces = abs(units * 0.035274 / 100);
    Serial.println(ounces);

    for (int i = window_size - 1; i > 0; i--) {
          window[i] = window[i - 1];
    }
    window[0] = ounces;

    lastSampleTime = millis();  // Update last sample time
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

  
  if (flag > 5){
    ledFlash();
    flag = 0;
  }
  
  if (Serial.available() > 0) {
    String inputString = Serial.readStringUntil('\n');
    inputString.trim();

    if (inputString == "S") {
      sampleInterval += 100;
    }
    else if (inputString == "D") {
      sampleInterval = sampleInterval - 100;
    }


    if (inputString.length() > 1) {
      char identifier = inputString.charAt(0);
      String valueString = inputString.substring(1);
      float receivedValue = valueString.toFloat();


      if (receivedValue != 0.0 || valueString == "0") {
        if (identifier == 'T') {
          threshold = receivedValue;
        } else if (identifier == 'C') {
          calibration_factor = receivedValue;
          scale.set_scale(calibration_factor);
        }
      }
    }
  }


  // Peak Detection Computation
  if (isPeak(1)) {
      sampleInterval = 0;
      peakCnt += 1;
      peakTimer = millis();  // Reset timer when peak is detected
      timerActive = true;  // Start the countdown

      Serial.print("p");
      Serial.print(peakCnt);
      Serial.println(window[1]);
  }

  // Timer logic
  if (timerActive) {
      unsigned long timeLeft = (countdownTime - (millis() - peakTimer)) / 1000;

      if (millis() - peakTimer >= countdownTime) {
          Serial.println("pz");
          sampleInterval = 500;
          peakCnt = 0;
          timerActive = false;
      } 
  }

  if (peakCnt == 3) {
    sampleInterval = 500;
    peakCnt = 0;  // Reset Peak Count  
    Serial.println("px");
    delay(2000); // Delay
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
