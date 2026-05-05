Hello!

This project was made as a final for my ME100 class.

Alarm clocks today suck. It's too easy to hit snooze and if you have to setup a million to wake up you know its not working.
The problem is that our brains cant stay awake as soon as were woken up from the alarm. To combat this we need something to exercise
our brain and make sure we are awake. 

Our Smart Puzzle Clock is just the cure. It uses LEDs and an LCD screen to showcase two puzzles back to back. The first is a LED 
pattern game which forces users to repeat the pattern the LEDs flashed in to advance in turning off the alarm. The next challenge
is to solve a math problem and after completing both challenges the alarm will finally turn off.

The alarm logic is as follows: 
Upon running main.py, three concurrent threads are created. These threads are, 'The Clock Thread', 'The Flask Thread', and 'The Alarm Checker Thread'. These threads each have their own responsibilities but work together to create a seamless product. 

The Clock Thread loops every 0.2 seconds and checks the internal time and external weather data which it then flashes to the LCD Screen. We could have made the refresh rate for the clock thread to be larger, for example every minute, but the 0.2 seconds makes it feel professional by updating almost instantaneously with actual time.

The Flask thread is the backbone between the pi and user communication. It sits and waits for any requests from the client (webapp) which it then completes. The webapp is HTTP (hypertext transfer protocol) based and sends three types of requests: GET (get data), POST (heres some data), DELETE (delete some data). It sends these HTTP requests in the form of json files which is then stored in files on the pi. If an alarm is created it would be sent via these json files which are stored on the device. If power is lost, the pi can always go back to check the files it has saved, this provides persistence. 

The Alarm Checker Thread loops every minute and compares the current time to alarm times on file, if a match is found, it will start a new 'Worker Thread' that begins the actual alarm. This thread which we will call the Alarm Run. At this point the Alarm Run Thread will establish a mutex (mutual exclusion) lock that stops the clock thread from writing at the same time as its thread to the LCD, otherwise it would conflict and create gibberish on the screen. The Alarm Run thread will then check a dictionary of "Modes" to see which level difficulty the user selected and then go through that sequence of puzzles. For each puzzle it will enter into a while True loop and will not break until users correctly answer the puzzle. After all puzzles are completed the Worker Thread will terminate and the clock thread is released from the mutex lock. 

If there is no input for five minutes the alarm will turn off and retry again in five minutes. It will do this three times total upon which if no user input is found it will turn off the alarm for good. This is a way so that if users are on vacation or something should happen where they arent physically there to turn off the alarm, the pi isnt just contininig on mindlessly.

If you would like to understand the puzzle logic please read below: 

There are three possible puzzles: the LED Sequence, Math Problems, and the Proximity Challenge. 
In the LED Sequence puzzle the pi will choose 5 (or 7 for the boss mode) random selections of the 3 possible LED colors and put them in a list, it will then flash the LEDs for 0.5s each color and then await user input. Users select each color they think using the cooresponding color buttons which use polling to get data and then puts all of the colors into an empty list. After 5 or 7 inputs have been made it compares the two lists and if the list is correct it breaks the while True loop, otherwise it restarts from the user input stage.

In the math problems puzzle, the pi will choose randomly from addition, subtraction or multiplication and then choose two numbers at random(following contraints). Users will first input the tens digit of the answer using the buttons (red is increasing interval, yellow is decreasing interval, green is confirm choice), and then the users will input the ones digit of the answer. The pi will do some simple math: Answer = (tens x 10) + ones and compare those two answers. If the user answer is correct it breaks the while True loop otherwise it restarts. 

In the proximity challenge, it asks the user to hold their hand from 5-15cm for about 3s. It will use the standard distance sensing logic and start a timer once the distance is within the interval, if the timer count down gets to zero the puzzle is completed and the while True loop breaks.




The alarm itself consists of a Raspberry Pi 3, several LEDs, several buttons, an LCD screen, a buzzer(which was later swapped for a speaker), (possibly in later iterations) a RTC clock
and a LiPo battery. The LEDs, buttons, LCD screen, and buzzer are all for the puzzle and alarm capabilities. The RTC clock and LiPo battery
are what make our alarm clock state of the art. In the unfortunate case that while sleeping there may occur a power outage our alarm clock
will not fail you. The RTC clock constantly keeps time on board the Raspi while the LiPo battery acts as a back up battery pack to continue
letting the Raspi operate its normal programs. 

Future iterations of the Smart Puzzle alarm clock also comes with the capability in the webapp where users can add upload music to be played upon 
the ringing of the alarm. The webapp would allows .mp3, .wav, and other audio files.

The whole project cost under 40$ to make(assuming ownership of several components) and is relatively easy to build.

We designed and assembled the packaging, which is a 3D printed case and uses some 2mm screws. 



BOM below

1x Raspberry Pi 3 Model B ~ 25$

3x LEDs (red, yellow, and green) ~ 50center

3x buttons (red, yellow and green) ~ 4$ (for package of 15)

1x LCD screen ~ 5$

1x RTC clock AdiFruit ~ 6$

1x Buzzer/Speaker

1x Ultrasonic Distance Sensor

1x Buffer OpAmp


Thinking about incorporating Backup Battey option which would include:
1x 3.7V LiPo Battery

1x Buck Boost Converter 5V 


