"""
parametric_cycle.py
===================
Design-point parametric cycle analysis for a single-spool turbojet engine.

Methodology:
    Mattingly, J.D., "Elements of Propulsion: Gas Turbines and Rockets",
    2nd ed., AIAA Education Series, 2006.

Usage:
    python parametric_cycle.py [--config PATH]

    Defaults to  config/engine_config.yaml  when no path is given.
"""

import argparse
import math
import sys

import yaml


# ---------------------------------------------------------------------------
# Configuration loader
# ---------------------------------------------------------------------------

def load_config(path: str) -> dict:
    """Load and return the YAML engine configuration."""
    with open(path, "r") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Turbojet parametric cycle analysis
# ---------------------------------------------------------------------------

def turbojet_parametric_cycle(config: dict) -> dict:
    """
    Perform a design-point parametric cycle analysis for a turbojet engine.

    Parameters
    ----------
    config : dict
        Engine configuration loaded from the YAML file.

    Returns
    -------
    dict
        Station temperatures, pressures, velocities and overall performance
        metrics.
    """

    # ── Unpack inputs ────────────────────────────────────────────────────────
    M0   = config["ambient"]["mach_number"]
    T0   = config["ambient"]["temperature_K"]
    P0   = config["ambient"]["pressure_kPa"] * 1_000.0   # → Pa

    gamma_c = config["gas_properties"]["gamma_cold"]
    cp_c    = config["gas_properties"]["cp_cold_J_per_kgK"]
    gamma_t = config["gas_properties"]["gamma_hot"]
    cp_t    = config["gas_properties"]["cp_hot_J_per_kgK"]

    eta_inlet = config["efficiencies"]["inlet"]
    eta_c     = config["efficiencies"]["compressor"]
    eta_b     = config["efficiencies"]["burner"]
    eta_t     = config["efficiencies"]["turbine"]
    eta_n     = config["efficiencies"]["nozzle"]

    pi_c  = config["design"]["compressor_pressure_ratio"]
    T_t4  = config["design"]["turbine_inlet_temperature_K"]
    pi_b  = config["design"]["burner_pressure_ratio"]
    h_PR  = config["fuel"]["heating_value_J_per_kg"]

    # Derived gas constants
    R_c = cp_c * (gamma_c - 1.0) / gamma_c   # [J/(kg·K)]
    R_t = cp_t * (gamma_t - 1.0) / gamma_t   # [J/(kg·K)]

    # ── Station 0 – Free-stream ──────────────────────────────────────────────
    a0  = math.sqrt(gamma_c * R_c * T0)      # Speed of sound  [m/s]
    V0  = M0 * a0                             # Flight velocity [m/s]

    tau_r  = 1.0 + (gamma_c - 1.0) / 2.0 * M0 ** 2   # Ram temperature ratio
    pi_r   = tau_r ** (gamma_c / (gamma_c - 1.0))      # Ideal ram pressure ratio

    T_t0 = T0 * tau_r
    P_t0 = P0 * pi_r

    # ── Station 2 – Inlet exit / Compressor inlet ────────────────────────────
    # Max isentropic inlet pressure ratio (MIL-E-5007D approximation for M0 ≤ 1)
    if M0 <= 1.0:
        pi_d_max = 1.0
    elif M0 <= 5.0:
        pi_d_max = 1.0 - 0.075 * (M0 - 1.0) ** 1.35
    else:
        pi_d_max = 800.0 / (M0 ** 4 + 935.0)

    pi_d  = pi_d_max * eta_inlet
    T_t2  = T_t0                  # Adiabatic inlet → no temperature loss
    P_t2  = P_t0 * pi_d

    # ── Station 3 – Compressor exit ──────────────────────────────────────────
    # Actual temperature ratio including isentropic efficiency
    tau_c = 1.0 + (pi_c ** ((gamma_c - 1.0) / gamma_c) - 1.0) / eta_c

    T_t3 = T_t2 * tau_c
    P_t3 = P_t2 * pi_c

    # Specific compressor work [J/kg_air]
    w_c = cp_c * (T_t3 - T_t2)

    # ── Station 4 – Turbine inlet (burner exit) ──────────────────────────────
    # Energy balance across burner:
    #   cp_c * T_t3 + f * eta_b * h_PR = (1 + f) * cp_t * T_t4
    # Solving for fuel-to-air ratio f:
    f = (cp_t * T_t4 - cp_c * T_t3) / (eta_b * h_PR - cp_t * T_t4)

    P_t4 = P_t3 * pi_b

    # ── Station 5 – Turbine exit ─────────────────────────────────────────────
    # Turbine drives the compressor; shaft mechanical efficiency assumed = 1
    # (1 + f) * cp_t * (T_t4 - T_t5) = cp_c * (T_t3 - T_t2)
    tau_t = 1.0 - (cp_c * T_t2 * (tau_c - 1.0)) / ((1.0 + f) * cp_t * T_t4)

    T_t5 = T_t4 * tau_t

    # Turbine pressure ratio from isentropic efficiency definition
    pi_t = (1.0 - (1.0 - tau_t) / eta_t) ** (gamma_t / (gamma_t - 1.0))

    P_t5 = P_t4 * pi_t

    # ── Station 9 – Nozzle exit ──────────────────────────────────────────────
    # Check for a choked nozzle
    pr_crit = ((gamma_t + 1.0) / 2.0) ** (gamma_t / (gamma_t - 1.0))
    nozzle_choked = (P_t5 / P0) >= pr_crit

    if nozzle_choked:
        T9 = T_t5 * 2.0 / (gamma_t + 1.0)
        V9 = math.sqrt(gamma_t * R_t * T9)
        P9 = P_t5 / pr_crit
    else:
        # Unchoked – isentropic expansion to P0 corrected for eta_n
        T9_ideal = T_t5 * (P0 / P_t5) ** ((gamma_t - 1.0) / gamma_t)
        T9 = T_t5 - eta_n * (T_t5 - T9_ideal)
        V9 = math.sqrt(2.0 * cp_t * (T_t5 - T9))
        P9 = P0

    # ── Performance metrics ──────────────────────────────────────────────────
    # Pressure-area (momentum) thrust term for choked nozzle
    if nozzle_choked:
        # A9 / m_dot_0 = (1+f) * R_t * T9 / (P9 * V9)
        A9_specific = (1.0 + f) * R_t * T9 / (P9 * V9)   # [m²/(kg/s)]
    else:
        A9_specific = 0.0  # P9 = P0 → pressure term vanishes

    # Specific thrust  F / m_dot_0   [N/(kg/s)]
    specific_thrust = ((1.0 + f) * V9 - V0
                       + (P9 - P0) * A9_specific)

    if specific_thrust <= 0.0:
        raise ValueError(
            "Specific thrust is non-positive – check input parameters."
        )

    # Thrust specific fuel consumption  [kg_fuel / (N·s)]
    TSFC   = f / specific_thrust
    TSFC_h = TSFC * 3_600.0          # [kg_fuel / (N·h)]

    # ── Efficiency calculations using the fully-expanded exit velocity ────────
    # When the nozzle is choked (P9 > P0), using the actual nozzle-exit velocity
    # V9 to compute delta_ke understates the jet power and yields η_p > 1.
    # The standard fix is to use the fully-expanded (isentropic to P0) exit
    # velocity V9e for efficiency calculations, while keeping V9 for thrust.
    T9e_ideal = T_t5 * (P0 / P_t5) ** ((gamma_t - 1.0) / gamma_t)
    T9e = T_t5 - eta_n * (T_t5 - T9e_ideal)
    V9e = math.sqrt(2.0 * cp_t * (T_t5 - T9e))   # Fully expanded exit velocity

    delta_ke = 0.5 * ((1.0 + f) * V9e ** 2 - V0 ** 2)   # [J/kg_air]
    if f * h_PR > 0.0:
        eta_th = delta_ke / (f * h_PR)
    else:
        eta_th = 0.0

    if delta_ke > 0.0:
        eta_p = specific_thrust * V0 / delta_ke
    else:
        eta_p = 0.0

    eta_o = eta_th * eta_p   # = F * V0 / (f * h_PR)

    # ── Collect results ──────────────────────────────────────────────────────
    return {
        # Inputs (echoed)
        "M0": M0,
        "T0_K": T0,
        "P0_kPa": P0 / 1_000.0,
        "pi_c": pi_c,
        "T_t4_K": T_t4,
        # Station temperatures [K]
        "T_t2_K": T_t2,
        "T_t3_K": T_t3,
        "T_t4_K_check": T_t4,
        "T_t5_K": T_t5,
        "T9_K": T9,
        # Station total pressures [kPa]
        "P_t2_kPa": P_t2 / 1_000.0,
        "P_t3_kPa": P_t3 / 1_000.0,
        "P_t4_kPa": P_t4 / 1_000.0,
        "P_t5_kPa": P_t5 / 1_000.0,
        "P9_kPa": P9 / 1_000.0,
        # Component ratios / intermediate
        "tau_r": tau_r,
        "tau_c": tau_c,
        "tau_t": tau_t,
        "pi_t": pi_t,
        "f": f,
        "nozzle_choked": nozzle_choked,
        # Velocities [m/s]
        "V0_m_per_s": V0,
        "V9_m_per_s": V9,
        "V9e_m_per_s": V9e,
        # Performance
        "specific_thrust_N_per_kg_s": specific_thrust,
        "TSFC_kg_per_N_h": TSFC_h,
        "eta_thermal": eta_th,
        "eta_propulsive": eta_p,
        "eta_overall": eta_o,
    }


# ---------------------------------------------------------------------------
# Results printer
# ---------------------------------------------------------------------------

def print_results(res: dict) -> None:
    """Print the cycle analysis results in a formatted table."""
    sep = "=" * 60

    print(sep)
    print("  TURBOJET PARAMETRIC CYCLE ANALYSIS – RESULTS")
    print(sep)

    print("\n[ Flight Conditions ]")
    print(f"  Mach number (M0)            : {res['M0']:.4f}")
    print(f"  Ambient temperature (T0)    : {res['T0_K']:.2f} K")
    print(f"  Ambient pressure (P0)       : {res['P0_kPa']:.3f} kPa")
    print(f"  Flight velocity (V0)        : {res['V0_m_per_s']:.2f} m/s")

    print("\n[ Design Choices ]")
    print(f"  Compressor pressure ratio   : {res['pi_c']:.1f}")
    print(f"  Turbine inlet temp (T_t4)   : {res['T_t4_K']:.1f} K")

    print("\n[ Station Temperatures ]")
    print(f"  T_t2  (inlet exit)          : {res['T_t2_K']:.2f} K")
    print(f"  T_t3  (compressor exit)     : {res['T_t3_K']:.2f} K")
    print(f"  T_t4  (turbine inlet)       : {res['T_t4_K_check']:.2f} K")
    print(f"  T_t5  (turbine exit)        : {res['T_t5_K']:.2f} K")
    print(f"  T9    (nozzle exit)         : {res['T9_K']:.2f} K")

    print("\n[ Station Total Pressures ]")
    print(f"  P_t2  (inlet exit)          : {res['P_t2_kPa']:.3f} kPa")
    print(f"  P_t3  (compressor exit)     : {res['P_t3_kPa']:.3f} kPa")
    print(f"  P_t4  (turbine inlet)       : {res['P_t4_kPa']:.3f} kPa")
    print(f"  P_t5  (turbine exit)        : {res['P_t5_kPa']:.3f} kPa")
    print(f"  P9    (nozzle exit)         : {res['P9_kPa']:.3f} kPa")

    print("\n[ Component / Cycle Parameters ]")
    print(f"  Ram temperature ratio (τ_r) : {res['tau_r']:.4f}")
    print(f"  Compressor temp ratio (τ_c) : {res['tau_c']:.4f}")
    print(f"  Turbine temp ratio    (τ_t) : {res['tau_t']:.4f}")
    print(f"  Turbine pressure ratio(π_t) : {res['pi_t']:.4f}")
    print(f"  Fuel-to-air ratio     (f)   : {res['f']:.5f}")
    print(f"  Nozzle exit velocity  (V9)  : {res['V9_m_per_s']:.2f} m/s")
    print(f"  Fully-expanded vel (V9e)    : {res['V9e_m_per_s']:.2f} m/s")
    choked_str = "YES" if res["nozzle_choked"] else "NO"
    print(f"  Nozzle choked               : {choked_str}")

    print("\n[ Performance Metrics ]")
    print(f"  Specific thrust (F/ṁ₀)     : "
          f"{res['specific_thrust_N_per_kg_s']:.2f} N/(kg/s)")
    print(f"  TSFC                        : "
          f"{res['TSFC_kg_per_N_h']:.5f} kg/(N·h)")
    print(f"  Thermal efficiency (η_th)   : "
          f"{res['eta_thermal'] * 100:.2f} %")
    print(f"  Propulsive efficiency (η_p) : "
          f"{res['eta_propulsive'] * 100:.2f} %")
    print(f"  Overall efficiency  (η_o)   : "
          f"{res['eta_overall'] * 100:.2f} %")

    print("\n" + sep)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Design-point parametric cycle analysis for a turbojet engine."
    )
    parser.add_argument(
        "--config",
        default="config/engine_config.yaml",
        metavar="PATH",
        help="Path to the YAML engine configuration file "
             "(default: config/engine_config.yaml)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    results = turbojet_parametric_cycle(config)
    print_results(results)


if __name__ == "__main__":
    main()
