import random
from math import comb


def fisher_two_sided(a, b, c, d):
    row1, row2, successes, total = a + b, c + d, a + c, a + b + c + d

    def probability(x):
        return comb(row1, x) * comb(row2, successes - x) / comb(total, successes)

    observed = probability(a)
    low, high = max(0, successes - row2), min(row1, successes)
    return min(1.0, sum(probability(x) for x in range(low, high + 1) if probability(x) <= observed * (1 + 1e-9)))


def sign_test(wins, losses):
    total = wins + losses
    if total == 0:
        return 1.0
    smaller = min(wins, losses)
    return min(1.0, 2 * sum(comb(total, i) for i in range(smaller + 1)) / 2 ** total)


def wilson(successes, total, z=1.96):
    if not total:
        return (float("nan"), float("nan"))
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    half = z * ((proportion * (1 - proportion) / total + z * z / (4 * total * total)) ** 0.5) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def bootstrap_difference(plain, comparison, seed, samples=10000):
    rng = random.Random(seed)
    differences = []
    for _ in range(samples):
        left = [rng.choice(plain) for _ in plain]
        right = [rng.choice(comparison) for _ in comparison]
        differences.append(sum(right) / len(right) - sum(left) / len(left))
    differences.sort()
    return differences[int(0.025 * samples)], differences[int(0.975 * samples)]
