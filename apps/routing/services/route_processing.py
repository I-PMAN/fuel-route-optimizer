from haversine import haversine, Unit


def compute_cumulative_distances(points):
    cumulative = 0
    result = []

    for i in range(len(points)):
        if i > 0:
            segment = haversine(
                points[i - 1],
                points[i],
                unit=Unit.MILES
            )
            cumulative += segment

        result.append((points[i][0], points[i][1], cumulative))

    return result