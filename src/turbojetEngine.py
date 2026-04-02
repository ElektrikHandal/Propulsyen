import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from lib.EnginePart import Inlet, Compressor, CombustionChamber, Turbine
from lib.EnginePart import load_yaml_config, create_atmosphere_from_config


def main():
	config_path = PROJECT_ROOT / "config" / "config.yaml"
	config = load_yaml_config(config_path)

	inlet_cfg = config.get("nozzleInlet") or config.get("inlet_data") or {}
	compressor_cfg = config.get("Compressor") or config.get("compressor_data") or {}
	combustor_cfg = config.get("CombustionChamber") or config.get("combustion_chamber_data") or {}
	turbine_cfg = config.get("Turbine") or config.get("turbine_data") or {}
	afterburner_cfg = config.get("afterburner") or {}

	atmosphere = create_atmosphere_from_config(config)
	inlet = Inlet(
		atmosphere.outlet_conditions,
		ideal=inlet_cfg.get("ideal", True),
		tau_d=inlet_cfg.get("temperature_ratio", inlet_cfg.get("tau_diffuser")),
		phi_d=inlet_cfg.get("pressure_ratio", inlet_cfg.get("phi_diffuser")),
	)


	compressor = Compressor(
		inlet.outlet_conditions,
		pressure_ratio=compressor_cfg.get("pressure_ratio"),
		efficiency=compressor_cfg.get("efficiency"),
	)

	combustor = CombustionChamber(
		compressor.outlet_conditions,
		effisiensi=combustor_cfg.get("efficiency", combustor_cfg.get("combustion_efficiency", 1.0)),
		pressure_ratio=combustor_cfg.get("pressure_ratio", combustor_cfg.get("combustion_pressure_loss", 1.0)),
		T_t4=combustor_cfg.get("outletTemperature_k", combustor_cfg.get("combustion_temperature", 1670.0)),
	)

	turbine = Turbine(
		combustor.outlet_conditions,
		efficiency=turbine_cfg.get("efficiency", 1.0),
		compressor=compressor,
	)

	afterburner = CombustionChamber(
		turbine.outlet_conditions,
		effisiensi=afterburner_cfg.get("efficiency", 1.0),
		pressure_ratio=afterburner_cfg.get("pressure_ratio", 1.0),
		T_t4=afterburner_cfg.get("outletTemperature_k", 2300.0),
	)

	print(f"Compressor Temperature Ratio (tau): {compressor.tau:.2f}")
	print(f"Compressor Power (wdotc): {compressor.wdotc:.2f} W")
	print(
		"Compressor Outlet Conditions (P_t3, T_t3): "
		f"{compressor.outlet_conditions[0]:.2f} Pa, {compressor.outlet_conditions[1]:.2f} K"
	)

	print(f"Fuel-to-Air Ratio (f): {combustor.f:.4f}")
	print(
		"Combustion Chamber Outlet Conditions (P_t4, T_t4): "
		f"{combustor.outlet_conditions[0]:.2f} Pa, {combustor.outlet_conditions[1]:.2f} K"
	)

	print(
		"Turbine Outlet Conditions (P_t5, T_t5): "
		f"{turbine.outlet_conditions[0]:.2f} Pa, {turbine.outlet_conditions[1]:.2f} K"
	)

	print(f"Afterburner Fuel-to-Air Ratio (f): {afterburner.f:.4f}")
	print(
		"Afterburner Outlet Conditions (P_t6, T_t6): "
		f"{afterburner.outlet_conditions[0]:.2f} Pa, {afterburner.outlet_conditions[1]:.2f} K"
	)


if __name__ == "__main__":
	main()