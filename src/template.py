from pathlib import Path
import sys


# Ensure project root is importable when this file is run directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from lib.EnginePart import Inlet, Compressor, NozzleExit
from lib.EnginePart import load_yaml_config, create_atmosphere_from_config


def print_component_outlets(components):
	for name, component in components:
		print("============================")
		print(f"{name}")
		print(component.outlet_conditions)

def main():
	config_path = PROJECT_ROOT / "config" / "config.yaml"
	config = load_yaml_config(config_path)

	#===========================================================================#
	# Import you parameter Here

	# Outside stream components: atmosphere, inlet, fan, nozzle_exit
	inlet_cfg = config.get("nozzleInlet") or config.get("inlet_data") or {}
	fan_cfg = config.get("Fan") or config.get("fan_data") or {}
	turbine_cfg = config.get("Turbine") or config.get("turbine_data") or {}
	nozzle_exit_cfg = config.get("nozzleOutlet") or config.get("nozzle_exit_data") or {}

	atmosphere = create_atmosphere_from_config(config)
	inlet = Inlet(
		atmosphere.outlet_conditions,
		ideal=inlet_cfg.get("ideal", True),
		tau_d=inlet_cfg.get("temperature_ratio", inlet_cfg.get("tau_diffuser")),
		phi_d=inlet_cfg.get("pressure_ratio", inlet_cfg.get("phi_diffuser")),
	)

	# ============================================================================#
	# Build your Engine here




	#===========================================================================#

	components = [
		("atmosphere", atmosphere),
		("inlet", inlet),
		("fan", fan),
		("nozzle_exit", nozzle_exit),
	]
	print_component_outlets(components)
	print("============================")
	print(f"fan_tau={fan.tau_c:.3f}, fan_power={fan.wdotc:.3f}")

if __name__ == "__main__":
	main()