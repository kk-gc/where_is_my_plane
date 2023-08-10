# where_is_my_plane
Flight number to delay converter ;)


## Description

Ever wondered how much your flight is going to be delayed? Worry no more, WIMP is here.
Check exactly where your aircraft is and how much of a delay it picked up so far.

Example:

Q: Flight number: FR6092 ==>
A: \_BGY_ 19:42 (+32) | _BGY_/ 20:31 (+56) | \_BRS_ ~21:20 (+40) 

FR6092 - it is a Ryanair flight from Milan (BGY) to Bristol (BRS)
\_BGY_ 19:42 (+32) => aircraft landed at 19:42 local time in Milan (BGY) 32 minutes late
_BGY_/ 20:31 (+56) => took off at 20:31 from Milan (BGY) 56 minutes behind the schedule
\_BRS_ ~21:20 (+40) => and is estimated (~) in Bristol (BRS) at 21:20 delayed 40 minutes

All times local


## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)


## Installation

1. Clone the repository: `git clone https://github.com/kk-gc/where_is_my_plane.git`
2. Navigate to the project directory: `cd where_is_my_plane`
3. Optional for Linux: `chmod +x *sh && sed -i -e 's/\r$//' *sh`
4. Build docker container: `./build.sh` or `.\bulid.bat`
5. Start the application: `./start.sh` or `.\start.bat`
6. Navigate your web browser to: `localhost:5000`
7. Alternatively: `curl http://localhost:5000/?flight_number=XXXXXX` 


## Usage

Navigate your web browser to: `localhost:5000`
Alternatively: `curl http://localhost:5000/?flight_number=XXXXXX` where XXXXX is your flight number


## Contributing

TBA

## License

TBA

## Contact

TBA
