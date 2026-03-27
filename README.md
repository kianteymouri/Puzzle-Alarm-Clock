Hello!

This project was made as a final for our ME100 class.
Team members included me and Chun Lin.

Alarm clocks today suck. It's too easy to hit snooze and if you have to setup a million to wake up you know its not working.
The problem is that our brains cant stay awake as soon as were woken up from the alarm. To combat this we need something to exercise
our brain and make sure we are awake. 

Our Smart Puzzle Clock is just the cure. It uses LEDs and an LCD screen to showcase two puzzles back to back. The first is a LED 
pattern game which forces users to repeat the pattern the LEDs flashed in to advance in turning off the alarm. The next challenge
is to solve a math problem and after completing both challenges the alarm will finally turn off.

The alarm itself consists of a Raspberry Pi 3, several LEDs, several buttons, an LCD screen, a buzzer(which was later swapped for a speaker), a RTC clock
and a LiPo battery. The LEDs, buttons, LCD screen, and buzzer are all for the puzzle and alarm capabilities. The RTC clock and LiPo battery
are what make our alarm clock state of the art. In the unfortunate case that while sleeping there may occur a power outage our alarm clock
will not fail you. The RTC clock constantly keeps time on board the Raspi while the LiPo battery acts as a back up battery pack to continue
letting the Raspi operate its normal programs. 

This Smart Puzzle alarm clock also comes with a webapp where users can add their alarm times and also upload music to be played upon 
the ringing of the alarm. The webapp allows .mp3, .wav, and other audio files.

The whole project cost under 40$ to make(assuming ownership of several components) and is relatively difficult to build.

We designed and assembled the packaging, which is a 3D printed case and user some 2mm screws. 



BOM below

1x Raspberry Pi 3 Model B ~ 25$

3x LEDs (red, yellow, and green) ~ 50center

3x buttons (red, yellow and green) ~ 4$ (for package of 15)

1x LCD screen ~ 5$

1x RTC clock AdiFruit ~ 6$

1x Buzzer/Speaker

1x Buffer OpAmp

1x 3.7V LiPo Battery

1x Buck Boost Converter 5V 


