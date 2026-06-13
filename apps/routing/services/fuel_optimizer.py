from haversine import haversine, Unit
from apps.fuel.models import FuelStation
import logging

logger = logging.getLogger(__name__)

MAX_RANGE = 500
MPG = 10
TANK_GALLONS = 50
ROUTE_BUFFER = 15  # miles

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
    logger.info(f"Stations after bounding box:, {len(all_stations)}")

    # ------------------------------------------------
    # 3. Route corridor filtering
    # ------------------------------------------------

    candidate_stations = [
        s for s in all_stations
        if station_near_route(s, route_points)
    ]

    if not candidate_stations:
        raise Exception("No fuel stations near route.")

    logger.info(f"Stations near route:, {len(candidate_stations)}")

    # ------------------------------------------------
    # 4. Compute distance along route
    # ------------------------------------------------

    station_positions = []

    for station in candidate_stations:

        mile = station_distance_along_route(station, route_sampled)

        if mile is not None:
            station_positions.append((station, mile))

    station_positions.sort(key=lambda x: x[1])
    logger.info(f"Stations with distance: {len(station_positions)}")

    # ------------------------------------------------
    # 5. Cost-minimizing greedy fuel optimization
    # ------------------------------------------------
    #
    # Classic "gas station" greedy. At each refuel point we look ahead at
    # every station reachable on the current tank:
    #   * If a cheaper station is reachable, buy only enough fuel to get
    #     there (no point paying more here than we have to).
    #   * Otherwise this is the cheapest option in range, so fill up enough
    #     to push as far as possible before the next mandatory stop.
    # This minimizes total spend while respecting the MAX_RANGE constraint.

    # Fuel is tracked as "miles of range in the tank" (capacity == MAX_RANGE).
    # The vehicle starts with a full tank, which is treated as already paid for
    # (cost only accrues for fuel purchased at stops along the route).
    #
    # Classic cost-minimizing "gas station" greedy, now respecting tank
    # capacity. At each refuel point:
    #   * If a strictly cheaper station is reachable within a full tank, buy
    #     only enough to reach it (don't overpay here).
    #   * Otherwise top up toward the destination, but never beyond what the
    #     tank can physically hold.
    EPS = 1e-9

    current_position = 0.0
    fuel_remaining = float(MAX_RANGE)  # miles of range in the tank; start full
    total_cost = 0.0
    fuel_stops = []

    while current_position + fuel_remaining < total_distance - EPS:
        # Stations ahead of us and reachable on the current tank.
        reachable = [
            (s, mile)
            for s, mile in station_positions
            if current_position < mile <= current_position + fuel_remaining + EPS
        ]

        if not reachable:
            raise Exception("No reachable fuel station within range.")

        # Cheapest station we can actually reach right now (nearest breaks ties).
        station, mile = min(reachable, key=lambda x: (x[0]["price"], x[1]))
        here_price = station["price"]

        # Fuel left in the tank when we arrive at this station.
        arrival_fuel = fuel_remaining - (mile - current_position)

        # Is there a strictly cheaper station reachable within a full tank from
        # here? If so, we only need enough fuel to get there.
        cheaper_ahead = [
            (s, m) for s, m in station_positions
            if mile < m <= mile + MAX_RANGE and s["price"] < here_price
        ]

        if cheaper_ahead:
            target_mile = min(cheaper_ahead, key=lambda x: x[1])[1]
            need = target_mile - mile
        else:
            # No cheaper option ahead: top up toward the destination.
            need = min(MAX_RANGE, total_distance - mile)

        # Buy only the deficit, and never more than the tank can hold.
        miles_to_buy = max(0.0, need - arrival_fuel)
        miles_to_buy = min(miles_to_buy, MAX_RANGE - arrival_fuel)

        if miles_to_buy > EPS:
            gallons = miles_to_buy / MPG
            cost = gallons * here_price
            total_cost += cost
            fuel_stops.append({
                "name": station["name"],
                "city": station["city"],
                "state": station["state"],
                "latitude": station["latitude"],
                "longitude": station["longitude"],
                "price": round(here_price, 4),
                "gallons": round(gallons, 2),
                "cost": round(cost, 2),
            })

        # Advance to this station; the tank now holds the arrival fuel plus
        # whatever we just bought.
        fuel_remaining = arrival_fuel + miles_to_buy
        current_position = mile

    return fuel_stops, round(total_cost, 2)