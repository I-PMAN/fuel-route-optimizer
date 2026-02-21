from haversine import haversine, Unit
from apps.fuel.models import FuelStation


MAX_RANGE = 500
MPG = 10
TANK_GALLONS = 50
ROUTE_BUFFER = 50  # miles


def station_near_route(station, route_points):
    station_coord = (station.latitude, station.longitude)

    for point in route_points:
        route_coord = (point[0], point[1])
        if haversine(station_coord, route_coord, unit=Unit.MILES) <= ROUTE_BUFFER:
            return True

    return False

def station_distance_along_route(station, route_with_distance):
    station_coord = (station.latitude, station.longitude)

    closest_mile = None
    min_distance = float("inf")

    for point in route_with_distance:
        route_coord = (point[0], point[1])
        distance = haversine(station_coord, route_coord, unit=Unit.MILES)

        if distance < min_distance:
            min_distance = distance
            closest_mile = point[2]

    return closest_mile

def station_distance_along_route(station, route_with_distance):
    station_coord = (station.latitude, station.longitude)

    closest_mile = None
    min_distance = float("inf")

    for point in route_with_distance:
        route_coord = (point[0], point[1])
        distance = haversine(station_coord, route_coord, unit=Unit.MILES)

        if distance < min_distance:
            min_distance = distance
            closest_mile = point[2]

    return closest_mile

def select_fuel_stops(route_with_distance):
    total_distance = route_with_distance[-1][2]
    fuel_remaining = MAX_RANGE
    current_position = 0
    total_cost = 0
    fuel_stops = []
    
    US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
    "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
    "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
    "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"
    }

    # 1️⃣ Filter stations near route
    all_stations = FuelStation.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
        state__in=US_STATES
    )


    route_points = [(p[0], p[1]) for p in route_with_distance]

    candidate_stations = [
        s for s in all_stations
        if station_near_route(s, route_points)
    ]

    if not candidate_stations:
        raise Exception("No fuel stations near route.")

    # 2️⃣ Compute distance along route once
    station_positions = []

    for station in candidate_stations:
        mile = station_distance_along_route(station, route_with_distance)
        if mile is not None:
            station_positions.append((station, mile))

    # 3️⃣ Greedy loop
    while current_position < total_distance:

        
        # Find stations ahead within fuel range
        reachable = [
            (s, mile)
            for s, mile in station_positions
            if current_position < mile <= current_position + fuel_remaining
        ]

        # If we can reach destination without refueling, break
        if current_position + fuel_remaining >= total_distance:
            break

        if not reachable:
            print("Current position:", current_position)
            print("Fuel remaining:", fuel_remaining)
            print("Reachable count:", len(reachable))
            raise Exception("No reachable fuel station within range.")

        # Sort reachable by mile (distance along route)
        reachable.sort(key=lambda x: x[1])

        # Take the farthest reachable mile
        farthest_mile = reachable[-1][1]

        # Among stations at that mile, choose cheapest
        candidates = [r for r in reachable if r[1] == farthest_mile]

        station, mile = min(candidates, key=lambda x: x[0].price)

        # Fuel needed to reach next full 500-mile capacity
        gallons = MAX_RANGE / MPG
        cost = gallons * station.price

        fuel_stops.append({
            "name": station.name,
            "city": station.city,
            "state": station.state,
            "price": station.price,
            "gallons": round(gallons, 2),
            "cost": round(cost, 2),
        })

        total_cost += cost

        # Move to station
        fuel_used = mile - current_position
        fuel_remaining -= fuel_used

        # Refill tank
        fuel_remaining = MAX_RANGE
        current_position = mile

    return fuel_stops, round(total_cost, 2)

