from pathlib import Path
import sys


# Ensure project root is importable when this file is run directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from lib.EnginePart import Inlet, Compressor, Inlet, CombustionChamber, Turbine, Mixer, NozzleExit
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

	engineCase = config.get("Engine_case")
	print(f"Engine case: {engineCase}")

	# Fan stream components: atmosphere, inlet, fan, fan_duct
	inlet_cfg = config.get("nozzleInlet") or config.get("inlet_data") or {}
	fan_cfg = config.get("Fan") or config.get("fan_data") or {}
	fan_duct_cfg = config.get("Fan_duct") or config.get("fan_duct_data") or {}
	
	atmosphere = create_atmosphere_from_config(config)
	inlet = Inlet(
		atmosphere.outlet_conditions,
		ideal=inlet_cfg.get("ideal", True),
		temperature_ratio=inlet_cfg.get("temperature_ratio", inlet_cfg.get("tau_diffuser")),
		pressure_ratio=inlet_cfg.get("pressure_ratio", inlet_cfg.get("phi_diffuser")),
	)
	
	fan = Compressor(
		inlet.outlet_conditions,
		pressure_ratio=fan_cfg.get("pressure_ratio"),
		efficiency=fan_cfg.get("efficiency")
	)
	print(f"fan work = {fan.wdotc} W")

	fan_duct = Inlet(
		fan.outlet_conditions,
		ideal=fan_duct_cfg.get("ideal", True),
		temperature_ratio=fan_duct_cfg.get("temperature_ratio", fan_duct_cfg.get("tau_nozzle")),
		pressure_ratio=fan_duct_cfg.get("pressure_ratio", fan_duct_cfg.get("phi_nozzle")),
	)
	


	# ============================================================================#
	# Core Stream components: compressor, combustion chamber, turbine, Mixer, exitNozzle
	comppressor_cfg = config.get("Compressor") or config.get("compressor_data") or {}
	combustion_chamber_cfg = config.get("CombustionChamber") or config.get("combustion_chamber_data") or {}
	turbine_cfg = config.get("Turbine") or config.get("turbine_data") or {}
	mixer_cfg = config.get("Mixer") or config.get("mixer_data") or {}
	core_nozzle_exit_cfg = config.get("core_nozzleOutlet") or config.get("core_nozzle_exit_data") or {}
	
	engineCompressor = Compressor(
		inlet.outlet_conditions,
		pressure_ratio=comppressor_cfg.get("pressure_ratio"),
		efficiency=comppressor_cfg.get("efficiency"),
	)
	
    
	engineCombustionChamber = CombustionChamber(
		engineCompressor.outlet_conditions,
		efficiency=combustion_chamber_cfg.get("efficiency"),
		pressure_ratio=combustion_chamber_cfg.get("pressure_ratio"),
		T_t4=combustion_chamber_cfg.get("outletTemperature_k"),
		case=engineCase,
	)
	print(f"Combustion chamber fuel-to-air ratio: {engineCombustionChamber.f:.4f}")

	engineTurbine = Turbine(
		engineCombustionChamber.outlet_conditions,
		efficiency=turbine_cfg.get("efficiency"),
		combustion_chamber=engineCombustionChamber,
		fan_duct=fan_duct,

		compressor=engineCompressor,
		case = engineCase,
		fan=fan

	)

	engineMixer = Mixer(
		turbine=engineTurbine,
		fanduct=fan_duct,
		
		Mach_in=mixer_cfg.get("Mach_in"),
	)
	print(f"Engine Mixer output: {engineMixer.outlet_conditions}")



	#===========================================================================#

	components = [
		("Inlet", inlet),
		("Fan", fan),
		("Fan Duct", fan_duct),
		("Compressor", engineCompressor),
		("Combustion Chamber", engineCombustionChamber),
		("Turbine", engineTurbine),
		("Mixer", engineMixer)
	]
	print_component_outlets(components)
	print("============================")
	print(f"fan_tau={fan.tau:.3f}, fan_power={fan.wdotc:.3f}")

if __name__ == "__main__":
	main()