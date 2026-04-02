from pathlib import Path
import sys


# Ensure project root is importable when this file is run directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from lib.EnginePart import Inlet, CombustionChamber,NozzleExit
from lib.EnginePart	import load_yaml_config, create_atmosphere_from_config

# Ramjet Engine Part:
# Inlet
# Combustion Chamber
# Exit Nozzle


def print_component_outlets(components):
	for name, component in components:
		print("============================")
		print(f"{name}")
		print(component.outlet_conditions)



def main():
	config_path = PROJECT_ROOT / "config" / "config.yaml"
	config = load_yaml_config(config_path)
	inlet_cfg = config.get("nozzleInlet") or config.get("inlet_data") or {}
	combustor_cfg = config.get("CombustionChamber") or config.get("combustion_chamber_data") or {}
	nozzle_exit_cfg = config.get("nozzleOutlet") or config.get("nozzle_exit_data") or {}

	atmosphere = create_atmosphere_from_config(config)
	inlet = Inlet(
		atmosphere.outlet_conditions,
		ideal=inlet_cfg.get("ideal", True),
		tau_d=inlet_cfg.get("temperature_ratio", inlet_cfg.get("tau_diffuser")),
		phi_d=inlet_cfg.get("pressure_ratio", inlet_cfg.get("phi_diffuser")),
	)
	combustor = CombustionChamber(
		inlet.outlet_conditions,
		effisiensi=combustor_cfg.get("efficiency", combustor_cfg.get("combustion_efficiency", 1.0)),
		pressure_ratio=combustor_cfg.get("pressure_ratio", combustor_cfg.get("combustion_pressure_loss", 1.0)),
		T_t4=combustor_cfg.get("outletTemperature_k", combustor_cfg.get("combustion_temperature")),
	)
	nozzle_exit = NozzleExit(
		combustor.outlet_conditions,
		ambient_pressure=atmosphere.P_0,
		ideal=nozzle_exit_cfg.get("ideal", True),
		tau_n=nozzle_exit_cfg.get("temperature_ratio", nozzle_exit_cfg.get("tau_nozzle")),
		phi_n=nozzle_exit_cfg.get("pressure_ratio", nozzle_exit_cfg.get("phi_nozzle")),
	)

	components = [
		("atmosphere", atmosphere),
		("inlet", inlet),
		("combustion_chamber", combustor),
		("nozzle_exit", nozzle_exit),
	]
	print_component_outlets(components)

	


if __name__ == "__main__":
	main()
