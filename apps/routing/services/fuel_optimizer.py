from haversine import haversine, Unit
from apps.fuel.models import FuelStation


MAX_RANGE = 500
MPG = 10
TANK_GALLONS = 50
ROUTE_BUFFER = 100  # miles

US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
    "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
    "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
    "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"
    }


def station_near_route(station, route_points):
    station_coord = (station["latitude"], station["longitude"])

    for point in route_points:
        route_coord = (point[0], point[1])

        if haversine(station_coord, route_coord, unit=Unit.MILES) <= ROUTE_BUFFER:
            return True

    return False

def station_distance_along_route(station, route_with_distance):

    station_coord = (station["latitude"], station["longitude"])

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

    # ------------------------------------------------
    # 1. Reduce route points 
    # ------------------------------------------------

    route_sampled = route_with_distance[::10]

    route_points = [(p[0], p[1]) for p in route_sampled]

    # ------------------------------------------------
    # 2. Bounding box filter 
    # ------------------------------------------------

    lats = [p[0] for p in route_points]
    lons = [p[1] for p in route_points]

    min_lat = min(lats) - 2
    max_lat = max(lats) + 2
    min_lon = min(lons) - 2
    max_lon = max(lons) + 2

    all_stations = FuelStation.objects.filter(
        latitude__gte=min_lat,
        latitude__lte=max_lat,
        longitude__gte=min_lon,
        longitude__lte=max_lon,
        state__in=US_STATES
    ).values(
        "name",
        "city",
        "state",
        "price",
        "latitude",
        "longitude"
    )
    print("Stations after bounding box:", len(all_stations))

    # ------------------------------------------------
    # 3. Route corridor filtering
    # ------------------------------------------------

    candidate_stations = [
        s for s in all_stations
        if station_near_route(s, route_points)
    ]

    if not candidate_stations:
        raise Exception("No fuel stations near route.")

    print("Stations near route:", len(candidate_stations))

    # ------------------------------------------------
    # 4. Compute distance along route
    # ------------------------------------------------

    station_positions = []

    for station in candidate_stations:

        mile = station_distance_along_route(station, route_with_distance)

        if mile is not None:
            station_positions.append((station, mile))

    station_positions.sort(key=lambda x: x[1])
    print("Stations with distance:", len(station_positions))

    # ------------------------------------------------
    # 5. Greedy fuel optimization
    # ------------------------------------------------

    while current_position < total_distance:

        if current_position + fuel_remaining >= total_distance:
            break

        reachable = [
            (s, mile)
            for s, mile in station_positions
            if current_position < mile <= current_position + fuel_remaining
        ]

        if not reachable:
            raise Exception("No reachable fuel station within range.")

        # Farthest reachable station
        farthest_mile = max(r[1] for r in reachable)

        candidates = [
            r for r in reachable
            if abs(r[1] - farthest_mile) < 0.01
        ]

        station, mile = min(candidates, key=lambda x: x[0]["price"])

        # Calculate fuel needed to reach this station
        miles_needed = mile - current_position
        gallons_needed = miles_needed / MPG

        # Cost of that fuel
        cost = gallons_needed * station["price"]

        fuel_stops.append({
            "name": station["name"],
            "city": station["city"],
            "state": station["state"],
            "price": station["price"],
            "gallons": round(gallons_needed, 2),
            "cost": round(cost, 2),
        })

        total_cost += cost

        # Update state
        fuel_remaining -= miles_needed
        fuel_remaining = MAX_RANGE
        current_position = mile

    return fuel_stops, round(total_cost, 2)

