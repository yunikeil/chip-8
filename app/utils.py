

def byte_to_bits(b: int) -> list[int]:
    return [(b >> (7 - p) & 1) for p in range(8)]
