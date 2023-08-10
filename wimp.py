import sys
import subprocess
import json
import re
import datetime
import pickle
import zoneinfo
from threading import Thread


def data_loader():
    """
    Load airport and airline data from pickled files.

    Returns:
        tuple: A tuple containing two dictionaries - airports and airlines.
    """
    # Load airport data from the 'airports.pkl' file
    with open('airports.pkl', 'rb') as f:
        airports = pickle.load(f)

    # Organize airport data into dictionaries based on different attributes
    airports = {'by_iata': {airport['iata']: airport for airport in airports},
                'by_icao': {airport['icao']: airport for airport in airports},
                'by_name': {airport['name']: airport for airport in airports},
                }

    # Load airline data from the 'airlines.pkl' file
    with open('airlines.pkl', 'rb') as f:
        airlines = pickle.load(f)

    # Organize airline data into dictionaries based on different attributes
    airlanes = {'by_icao': {airline['ICAO']: airline for airline in airlines},
                'by_name': {airline['Name']: airline for airline in airlines},
                'by_code': {airline['Code']: airline for airline in airlines if airline['Code']},
                }

    # Return the organized dictionaries for airports and airlines
    return airports, airlanes


def airlines_add_multi_prefix():
    """
    Create a dictionary of airlines with multiple prefixes based on their names.

    This function identifies airlines that share the same name but have different prefixes
    and creates a 'multi' dictionary to store these associations.

    Returns:
        None
    """
    multi = {}  # Initialize a dictionary to store airlines with multiple prefixes

    # Iterate through each airline name in the 'by_name' dictionary
    for name in airlines['by_name'].keys():
        for airline in airlines['by_name']:
            # Check if the current airline starts with the current name and is not the same as the name
            if airline.startswith(name) and airline != name:
                # If 'multi' dictionary doesn't have an entry for the name, create one
                if not multi.get(name):
                    multi[name] = [name, airline]  # Store the name and the first matching airline
                else:
                    multi[name].append(airline)  # Append additional matching airlines to the list

    airlines['multi'] = multi  # Update the 'multi' key in the 'airlines' dictionary


def get_api_data(query_type, query_args, from_api=False, timer=False):
    """
    Get data from an API using specified query type and arguments.

    Args:
        query_type (str): The type of query, e.g., 'flight' or 'aircraft'.
        query_args (str or list): The argument(s) for the query.
        from_api (bool): Flag indicating if data should be retrieved from the API.
        timer (bool): Flag indicating if timer should be enabled.

    Returns:
        dict or None: The query results or None if an error occurs.
    """

    def _api_query(my_node, my_path, my_args):
        """
        Execute API query using subprocess and parse the results.

        Args:
            my_node (str): Node executable path.
            my_path (str): API script path.
            my_args (str): API query argument.

        Returns:
            None
        """
        # Execute API query using subprocess and capture stdout
        p = subprocess.Popen([my_node, my_path, my_args], stdout=subprocess.PIPE)
        ret = p.stdout.read()

        # Extract query argument from args for result mapping
        _, query_arg = my_args.split('=')

        if ret:
            # Parse the API response as JSON and store in _return dictionary
            my_json = ret.decode('utf8').replace("'", '"')
            _return[query_arg] = json.loads(my_json)
        else:
            _return[query_arg] = None
        return

    _return = {}  # Initialize dictionary to store query results
    valid_query_types = {'flight', 'aircraft'}  # Valid query types

    # Ensure query_args is a list, if it's a string
    if query_args and isinstance(query_args, str):
        query_args = [query_args]

    if from_api and query_type in valid_query_types and query_args:

        # Determine the correct node and path based on the platform
        if sys.platform.startswith('win'):
            my_node = "node.exe"
            my_path = r"fr_scraper.js"
        else:
            my_node = "node"
            my_path = r"fr_scraper.js"

        threads = []  # Initialize a list to store thread objects
        for query_arg in query_args:
            my_args = f'{query_type}={query_arg.lower()}'
            t = Thread(target=_api_query, args=(my_node, my_path, my_args))
            threads.append(t)
            t.start()

        # Wait for all threads to finish
        for t in threads:
            t.join()

    # Filter out empty values from _return
    _return = {k: v for k, v in _return.items() if v}

    # If only one result, return it
    if len(_return) == 1:
        _found, = _return.keys()
        return _return

    # If multiple results, print mismatch and return None
    else:
        print('Some mismatch, found more than 1 flight:')
        print(_return)
    return None  # Return None if an error occurs


def data_validator(name, raw_data, short=True):
    """
    Validate and process raw data for different attributes like flight numbers and aircraft registration.

    Args:
        name (str): The name of the data attribute to be validated (e.g., 'flight_number' or 'aircraft_reg').
        raw_data (dict): Raw data containing the attribute details.
        short (bool): Flag indicating whether to trim the data for shorter results.

    Returns:
        list: A list of dictionaries containing validated and processed data.
    """

    if not raw_data:
        return None  # Return None if raw_data is empty

    _fn, = raw_data.keys()
    _data, = raw_data.values()

    if name == 'flight_number':
        _first = 'aircraft_reg'
    elif name == 'aircraft_reg':
        _first = 'flight_number'
    else:
        return None  # Return None if name is not recognized

    if isinstance(_data[0], str):
        _data = [_data]  # Convert a single string list to a list of lists

    _return = []  # Initialize a list to store validated data
    _offsets_table = {}  # Initialize a dictionary to store timezone offsets

    if short and name in {'flight_number', 'aircraft_reg'}:
        # Identify indexes for 'Scheduled' and 'Landed' statuses
        _scheduled_indexes = [i for i, el in enumerate([el[3] for el in _data]) if el.startswith('Scheduled')]
        _start_index = None if len(_scheduled_indexes) == 0 else _scheduled_indexes[-1]

        _landed_indexes = [i for i, el in enumerate([el[3] for el in _data]) if el.startswith('Landed')]
        _stop_index = None if len(_landed_indexes) == 0 else _landed_indexes[0] + 1

        _data = _data[slice(_start_index, _stop_index)]

    for _op in _data:
        if _op[3] == 'Unknown':
            continue  # Skip 'Unknown' status entries

        # Extract IATA codes for departure and arrival airports
        _from = re.search(r'(?<=\()([A-Z]{3})(?=\))', _op[15]).group(0)
        _from_timezone_offset = _offsets_table.get(_from)
        if not _from_timezone_offset:
            _from_timezone_offset = get_airport_timezone_offset(_from)
            _offsets_table[_from] = _from_timezone_offset

        if not _from_timezone_offset:
            print(f"Airport: '{_from}' not in database")
            continue

        _to = re.search(r'(?<=\()([A-Z]{3})(?=\))', _op[18]).group(0)
        _to_timezone_offset = _offsets_table.get(_to)
        if not _to_timezone_offset:
            _to_timezone_offset = get_airport_timezone_offset(_to)
            _offsets_table[_to] = _to_timezone_offset

        if not _to_timezone_offset:
            print(f"Airport: '{_to}' not in database")
            continue

        # Convert date and time strings to datetime objects with timezone info
        _std = datetime.datetime.strptime(f'{_op[1].strip()} {_op[6]}{_from_timezone_offset}', '%d %b %Y %H:%M%z')
        _sta = datetime.datetime.strptime(f'{_op[1].strip()} {_op[12]}{_to_timezone_offset}', '%d %b %Y %H:%M%z')

        try:
            _atd = datetime.datetime.strptime(f'{_op[1].strip()} {_op[9]}{_from_timezone_offset}', '%d %b %Y %H:%M%z')
        except ValueError:
            _atd = None

        _status, *_status_time = _op[3].split()
        _status = _op[3].split()

        # Extract status time and handle timezone offsets based on status
        _status_time = re.match(r'[0-9]{2}:[0-9]{2}', _status[-1])
        if _status_time:
            _status = ' '.join(_status[:-1])
            if _status in {'Landed', 'Estimated', 'Delayed'}:
                _status_time_offset = _to_timezone_offset

            elif _status in {'Estimated departure'}:
                _status_time_offset = _from_timezone_offset

            else:
                print(f'Unrecognized status: {_status}')

            _status_time = datetime.datetime.strptime(f'{_op[1].strip()} {_status_time.group(0)}{_status_time_offset}',
                                                      '%d %b %Y %H:%M%z')
        else:
            _status = ' '.join(_status)

        _now = datetime.datetime.now().astimezone(zoneinfo.ZoneInfo(get_airport_timezone_name(_from)))

        # Determine the timeline based on status time and current time
        if _status_time and _status_time < _now:
            _timeline = 'past'
        elif _std > _now:
            _timeline = 'future'
        else:
            _timeline = 'not past nor future'

        # Append validated and processed data to _return list
        _return.append({
            _first: _op[0].strip(),
            'std': _std,
            'atd': _atd,
            'sta': _sta,
            'status': _status,
            'status_time': _status_time,
            'from': _from,
            'to': _to,
            'timeline': _timeline,
        })

    return _return  # Return the list of validated and processed data


def get_aircraft_reg_from_flight(flight_history):
    """
    Extract aircraft registration from flight history.

    Args:
        flight_history (list): List of flight history data dictionaries.

    Returns:
        str or None: The aircraft registration or None if not found.
    """
    if not flight_history:
        return None  # Return None if flight_history is empty

    flights_filtered = []  # Initialize a list to store filtered flight data

    # Filter flights with multiple aircraft registrations until first 'Landed' status in past
    for _flight in flight_history:
        if len(_flight.get('aircraft_reg')) > 1:
            flights_filtered.append(_flight)
            if _flight.get('status') == 'Landed' and _flight.get('timeline') == 'past':
                break

    if len(flights_filtered) == 1:
        _aircraft_reg = flights_filtered[0].get('aircraft_reg')  # Get aircraft registration

    # If there are multiple filtered flights and the last one has 'Landed' status in the past
    elif \
            len(flights_filtered) > 1 \
            and flights_filtered[-1].get('status') == 'Landed' \
            and flights_filtered[-1].get('timeline') == 'past':

        _aircraft_reg = flights_filtered[-2].get('aircraft_reg')  # Get aircraft registration

    else:
        # Print a message if selecting one aircraft registration is not possible
        print(f"Couldn't select one aircraft - found: {len(flights_filtered)} - check 'flight' variable")
        print(flights_filtered)
        _aircraft_reg = None

    return _aircraft_reg  # Return the selected aircraft registration or None


def get_aircraft_location(aircraft_history):
    """
    Get aircraft location information from aircraft history.

    Args:
        aircraft_history (list): List of aircraft history data dictionaries.

    Returns:
        dict or None: A dictionary containing aircraft location information or None if not found.
    """
    if not aircraft_history:
        return None  # Return None if aircraft_history is empty

    _return = {}  # Initialize a dictionary to store aircraft location information
    i = 0
    while i < len(aircraft_history):
        # Check if the aircraft status is 'Landed'
        if aircraft_history[i].get('status') == 'Landed':
            _return['last_landed_location'] = aircraft_history[i].get('to')
            _return['last_landed_sta'] = aircraft_history[i].get('sta')
            _return['last_landed_ata'] = aircraft_history[i].get('status_time')
            break
        i += 1

    # If there was a landed status, extract information about the next flight
    if i > 0:
        _, _std, _atd, _sta, _status, _status_time, _from, _to, _ = aircraft_history[i - 1].values()
        _return['next_destination'] = _to
        _return['next_std'] = _std
        _return['next_atd'] = _atd
        _return['next_sta'] = _sta
        _return['next_status'] = _status
        _return['next_status_time'] = _status_time

    return _return  # Return the aircraft location information dictionary or None


def get_airport_timezone_name(airport_iata):
    """
    Get the timezone name of an airport based on its IATA code.

    Args:
        airport_iata (str): The IATA code of the airport.

    Returns:
        str or None: The timezone name of the airport or None if not found.
    """
    if not airport_iata:
        return None  # Return None if airport_iata is not provided

    # Get airport details based on the IATA code from the 'airports' dictionary
    _airport = airports['by_iata'].get(airport_iata.upper())

    if not _airport:
        return None  # Return None if airport details are not found
    elif _airport.get('tz_name'):
        return _airport.get('tz_name')  # Return timezone name if available
    else:
        return None  # Return None if timezone name is not available
        # TODO: not working bc TimezoneFinder versioning issue, disabled for now
        # return TimezoneFinder().timezone_at(lng=_airport.get('lon'), lat=_airport.get('lat'))


def get_airport_timezone_offset(airport_iata):
    if not airport_iata:
        return None

    # Get airport details based on the IATA code from the 'airports' dictionary
    _airport = airports['by_iata'].get(airport_iata.upper())

    if not _airport:
        return None  # Return None if airport details are not found
    elif _airport.get('tz_offset'):
        return _airport.get('tz_offset')  # Return timezone offset if available
    else:
        return None  # Return None if timezone offset is not available
        # Calculate and return timezone offset based on coordinates
        now = datetime.datetime.now()   # TODO: get timezone by airport coordinates - not working bc TimezoneFinder versioning issue, disabled for now
        tz_name = TimezoneFinder().timezone_at(lng=_airport.get('lon'), lat=_airport.get('lat'))
        _offset = now.astimezone(tz=zoneinfo.ZoneInfo(tz_name)).utcoffset().total_seconds()

        if _offset == 0:
            return f'+00:00'    # If the offset is 0, return UTC offset in proper format

        _sign = '+' if _offset > 0 else '-'     # Determine whether the offset is positive or negative

        _offset = abs(_offset)      # Get the absolute value of the offset

        _hours = f'{int(_offset // 3600)}'.zfill(2)     # Calculate hours and format with leading zeros
        _minutes = f'{int(_offset % 3600 // 60)}'.zfill(2)      # Calculate minutes and format with leading zeros

        return f'{_sign}{_hours}:{_minutes}'  # Return formatted timezone offset


def get_flight_history(flight_number):
    """
    Get variants of a flight number for historical tracking.

    Args:
        flight_number (str): The flight number to be processed.

    Returns:
        list: A list of possible flight number variants for tracking history.
    """
    if not flight_number or not isinstance(flight_number, str):
        return None  # Return None if flight_number is invalid or not provided

    flight_number = flight_number.upper()  # Convert flight_number to uppercase

    flight_number_variants = [flight_number]  # Initialize a list with the original flight_number

    # Split the flight number into letters and numbers using regex
    _letters, _numbers, _ = re.split(r'(\d+)', flight_number)
    # Note: The list of changes is not exhaustive in this comment

    # Try to replace airline ICAO ('EZY') with airline Code ('U2')
    # _icao = airlines_icao.get(_letters)
    _icao = airlines['by_icao'].get(_letters)

    if _icao and _icao.get('Code'):
        # Add the variant with the airline code and flight number
        flight_number_variants.append(f"{_icao.get('Code')}{_numbers}")

        # For easyJet ('EZY'), remove leading 0 from the flight number
        if _icao.get('Code') == 'U2' and _numbers.startswith('0'):
            flight_number_variants.append(f"{_icao.get('Code')}{_numbers.replace('0', '', 1)}")

    return flight_number_variants  # Return the list of flight number variants


def airlines_multi_codes(airline_name):
    """
    Get the airline codes for all variants of a multi-code airline name.

    Args:
        airline_name (str): The name of the multi-code airline.

    Returns:
        list or None: A list of airline codes or None if not found.
    """
    for i in range(1, len(airline_name.split()) + 1):
        # Get multi-code variants based on successive parts of the airline name
        multi = airlines['multi'].get(' '.join(airline_name.split()[0:i]))

        if multi:
            # Return a list of airline codes corresponding to the multi-code variants
            return [airlines['by_name'].get(name).get('Code') for name in multi]

    # Return None if no multi-code variants are found


def get_flight_number_resolved(flight_number):
    """
    Get resolved flight numbers for multi-code airlines.

    Args:
        flight_number (str): The flight number to be resolved.

    Returns:
        list or None: A list of resolved flight numbers or None if not found.
    """
    if not flight_number or not isinstance(flight_number, str):
        return None  # Return None if flight_number is not provided or not a string

    _return = []  # Initialize a list to store resolved flight numbers

    # Check if the flight number has mixed alphanumeric parts
    if (flight_number[0].isalpha() and flight_number[1].isdigit()) \
            or (flight_number[1].isalpha() and flight_number[0].isdigit()):
        _letters = flight_number[:2]  # Extract the first two characters as letters
        _numbers = flight_number[2:]  # Extract the remaining characters as numbers
    else:
        _letters, _numbers, _ = re.split(r'(\d+)', flight_number.upper())

    airline_by_code = airlines['by_code'].get(_letters)
    airline_by_icao = airlines['by_icao'].get(_letters)

    if airline_by_code:
        airline_name = airline_by_code.get('Name')
        airline_code = airline_by_code.get('Code')

        # Get alternative codes for 'sister' airlines if available
        multi_codes = airlines_multi_codes(airline_name)
        if multi_codes:
            for multi_code in multi_codes:
                if multi_code:
                    flight_number = f'{multi_code}{int(_numbers)}'
                    _return.append(flight_number)
        else:
            flight_number = f'{airline_code}{int(_numbers)}'
            _return.append(flight_number)

    elif airline_by_icao:
        airline_name = airline_by_icao.get('Name')
        airline_code = airline_by_icao.get('Code')

        # Get alternative codes for 'sister' airlines if available
        multi_codes = airlines_multi_codes(airline_name)
        if multi_codes:
            for multi_code in multi_codes:
                flight_number = f'{multi_code}{int(_numbers)}'
                _return.append(flight_number)
        else:
            flight_number = f'{airline_code}{int(_numbers)}'
            _return.append(flight_number)

    return _return  # Return the list of resolved flight numbers or None


def generate_output(d):
    """
    Generate formatted output based on the provided data dictionary.

    Args:
        d (dict): The data dictionary containing aircraft location and timing information.

    Returns:
        str or None: The formatted output string or None if data is not provided.
    """
    # Check if data dictionary is empty
    if not d:
        return None

    # Initialize location variables
    loc0 = loc1 = d.get('last_landed_location')
    loc2 = d.get('next_destination')

    # Extract time and delay information for last landed event
    time0 = f"{d.get('last_landed_ata').strftime('%H:%M')}"
    delay0 = int((d.get('last_landed_ata') - d.get('last_landed_sta')).total_seconds() / 60)
    sign0 = '+' if delay0 >= 0 else ''

    # Check if there are no further scheduled flights
    if not loc2:
        # Return a message for no further scheduled flights
        return f"\\_{loc0}_ {time0} ({sign0}{delay0}) | No further scheduled flights for: {aircraft_reg}"

    # Get next ATD (Actual Time of Departure) or calculate next status time
    next_atd = d.get('next_atd')
    if not next_atd:
        next_status_time = d.get('next_status_time')
        if not next_status_time:
            next_status_time = d.get('next_std')
        next_std = d.get('next_std')

        # Calculate time and delay information for the next status time
        time1 = f"~{next_status_time.strftime('%H:%M')}"
        delay1 = int((next_status_time - next_std).total_seconds() / 60)
        sign1 = '+' if delay1 >= 0 else ''

        # Calculate time and delay information for the next STA (Scheduled Time of Arrival)
        time2 = f"~{d.get('next_sta').strftime('%H:%M')}"
        delay2 = '--'  # Placeholder for delay since STA doesn't have delay info
        sign2 = ''

    # Calculate time and delay information for the next ATD and next status time
    else:
        time1 = f"{d.get('next_atd').strftime('%H:%M')}"
        delay1 = int((next_atd - d.get('next_std')).total_seconds() / 60)
        sign1 = '+' if delay1 >= 0 else ''

        time2 = f"~{d.get('next_status_time').strftime('%H:%M')}"
        delay2 = int((d.get('next_status_time') - d.get('next_sta')).total_seconds() / 60)
        sign2 = '+' if delay2 >= 0 else ''

    # Return the formatted output string
    return f"\\_{loc0}_ {time0} ({sign0}{delay0}) | _{loc1}_/ {time1} ({sign1}{delay1}) | \\_{loc2}_ {time2} ({sign2}{delay2})"


if __name__ == '__main__':

    if len(sys.argv) == 1:
        flight_number = input('flight number: ')
    else:
        flight_number, *_ = sys.argv[1:]

    airports, airlines = data_loader()
    airlines_add_multi_prefix()

    flight_number = get_flight_number_resolved(flight_number)
    flight_history_raw = get_api_data('flight', flight_number, from_api=True, timer=False)
    flight_history = data_validator('flight_number', flight_history_raw)

    aircraft_reg = get_aircraft_reg_from_flight(flight_history)
    aircraft_history_raw = get_api_data('aircraft', aircraft_reg, from_api=True, timer=False)
    aircraft_history = data_validator('aircraft_reg', aircraft_history_raw)
    aircraft_location = get_aircraft_location(aircraft_history)

    print(generate_output(aircraft_location))

# TODO: adjust datetime for day +1

# TODO: what if there is no aircraft reg even if flight is still on?
# TODO: - check if status changed from 'Scheduled' to 'Estimated departure' or 'Estimated'???
#
# TODO: change frames sorting!

# // flight_number ---> flights/[flight_no] ---> get registration ---> aircraft/[registration] --->
# //      ---> get timelines from flights:
# //           15:30 PIKd -> 19:06 BGYa -> 19.30 BGYd -> 21:10 KTWa -> 21:35 KTWd -> 23:20 BGYa
# //             - pick place according to time
# //             - scan area between airports to find exact location of the aircraft
# //             - check how far is from the destination
# //             - try to guess if it's gonna be on time or late (and how much)
