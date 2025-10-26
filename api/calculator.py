emission_factors = {
    "steel": 1.9,
    "cement": 0.9,
    "textile": 0.5,
    "chemical": 1.2,
    "other": 0.7
}

energy_sources = {
    "coal": 1.0,
    "oil": 0.8,
    "natural_gas": 0.6,
    "renewable": 0.1,
    "nuclear": 0.05,
    "mixed": 1.1
}

def calculate_emission(industry: str, production_value: float, years: float = 1.0, energy_source: str = "coal") -> float:
    factor = emission_factors.get((industry or "").lower(), emission_factors["other"])
    multiplier = energy_sources.get((energy_source or "").lower(), energy_sources["coal"])
    emission = production_value * factor * years * multiplier
    return float(emission)