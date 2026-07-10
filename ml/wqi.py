"""Water Quality Index (WQI) Calculator.

Computes a deterministic WQI score (0-100) based on pH, TDS, and turbidity guidelines.
"""


def calculate_wqi(ph: float, tds: float, turbidity: float) -> float:
    """Calculates the Water Quality Index (WQI) on a scale of 0 to 100.

    100 represents perfect water quality, while lower values represent deterioration.
    Thresholds are aligned with dashboard limits:
      - pH: optimal 6.5 - 8.5
      - TDS: safe < 300 ppm
      - Turbidity: safe < 5 NTU
    """
    # 1. pH Sub-index (optimal: 6.5 to 8.5)
    if 6.5 <= ph <= 8.5:
        s_ph = 100.0
    elif ph < 6.5:
        # Deteriorates as it approaches 0.0
        s_ph = max(0.0, 100.0 - 150.0 * ((6.5 - ph) / 6.5))
    else:
        # Deteriorates as it approaches 14.0
        s_ph = max(0.0, 100.0 - 150.0 * ((ph - 8.5) / (14.0 - 8.5)))

    # 2. TDS Sub-index (safe: <= 300 ppm)
    if tds <= 300.0:
        s_tds = 100.0
    else:
        # Deteriorates as it approaches 1500 ppm
        s_tds = max(0.0, 100.0 - 100.0 * ((tds - 300.0) / (1500.0 - 300.0)))

    # 3. Turbidity Sub-index (safe: <= 5.0 NTU)
    if turbidity <= 5.0:
        s_turb = 100.0
    else:
        # Deteriorates as it approaches 100.0 NTU
        s_turb = max(0.0, 100.0 - 100.0 * ((turbidity - 5.0) / (100.0 - 5.0)))

    # 4. Weighted Aggregation
    # pH weight: 0.4, TDS weight: 0.3, Turbidity weight: 0.3
    wqi = 0.4 * s_ph + 0.3 * s_tds + 0.3 * s_turb

    return round(wqi, 2)
