// flashAndLight.ino

#define flashPin 7
#define lightPin 6

void setup() {
	Serial.begin(9600);
	pinMode(flashPin, OUTPUT);
        setBright(100);
}

void loop() {
	cereals();
}

void cereals(){
	if(Serial.available()){
		int tmp = Serial.read();
		if(tmp == 255) flash();
		else setBright(tmp);
	}
}

void flash(){
	digitalWrite(flashPin, HIGH);
	delay(100);
	digitalWrite(flashPin, LOW);
}

void setBright(int b){
	analogWrite(lightPin, b);
}
