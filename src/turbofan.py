from pathlib import Path
import sys


# Ensure project root is importable when this file is run directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from lib.EnginePart import CombustionChamber, Inlet, Compressor, NozzleExit, Turbine
from lib.EnginePart import load_yaml_config, create_atmosphere_from_config


def print_component_outlets(components):
	for name, component in components:
		print("============================")
		print(f"{name}")
		print(component.outlet_conditions)

def main():
	config_path = PROJECT_ROOT / "config" / "config.yaml"
	config = load_yaml_config(config_path)

	engineCase = config.get("Engine_case")
	print(f"Engine Case: {engineCase}")
	#===========================================================================#
	# Outside stream

	# Outside stream components: atmosphere, inlet, fan, nozzle_exit
	inlet_cfg = config.get("nozzleInlet") or config.get("inlet_data") or {}
	fan_cfg = config.get("Fan") or config.get("fan_data") or {}
	turbine_cfg = config.get("Turbine") or config.get("turbine_data") or {}
	outer_nozzle_exit_cfg = config.get("fan_nozzleOutlet") or config.get("fan_nozzle_exit_data") or {}

	atmosphere = create_atmosphere_from_config(config)
	inlet = Inlet(
		atmosphere.outlet_conditions,
		ideal=inlet_cfg.get("ideal", True),
		temperature_ratio=inlet_cfg.get("temperature_ratio", inlet_cfg.get("tau_diffuser")),
		pressure_ratio=inlet_cfg.get("pressure_ratio", inlet_cfg.get("phi_diffuser")),
	)

	# Turbofan fan stream approximation: use compressor model as fan.

	fan = Compressor(
		inlet.outlet_conditions, 
		pressure_ratio=fan_cfg.get("pressure_ratio"),
		efficiency=fan_cfg.get("efficiency")
	)

	outer_nozzle_exit = NozzleExit(
		fan.outlet_conditions,
		ambient_pressure=atmosphere.P_0,
		ideal=outer_nozzle_exit_cfg.get("ideal", True),
		temperature_ratio=outer_nozzle_exit_cfg.get("temperature_ratio", outer_nozzle_exit_cfg.get("tau_nozzle")),
		pressure_ratio=outer_nozzle_exit_cfg.get("pressure_ratio", outer_nozzle_exit_cfg.get("phi_nozzle")),
	)

	V_19 = outer_nozzle_exit.V_e

	
	#================================================================================================#
	# core Stream
	Compressor_cfg = config.get("Compressor") or config.get("compressor_data") or {}
	Combustion_chamber_cfg = config.get("CombustionChamber") or config.get("combustion_chamber_data") or {}
	turbine_cfg = config.get("Turbine") or config.get("turbine_data") or {}
	core_nozzle_exit_cfg = config.get("nozzleOutlet") or config.get("nozzleOutlet_data") or {}
	bypass_ratio = Compressor_cfg.get("bypass_ratio", 0.0)
	print(f"Bypass Ratio: {bypass_ratio}")

	compressor = Compressor(
		inlet.outlet_conditions,
		pressure_ratio=Compressor_cfg.get("pressure_ratio"),
		efficiency=Compressor_cfg.get("efficiency"),
		bypassratio=bypass_ratio,
		case= engineCase,
		fan = fan
	)
	print(f"Compressor Wdotc: {compressor.wdotc} W")

	combustion_chamber = CombustionChamber(
		compressor.outlet_conditions,
		effisiensi=Combustion_chamber_cfg.get("efficiency"),
		pressure_ratio=Combustion_chamber_cfg.get("pressure_ratio"),
		T_t4=Combustion_chamber_cfg.get("outletTemperature_k"),
		case= engineCase,
		bypassratio=bypass_ratio
	)

	turbine = Turbine(
		combustion_chamber.outlet_conditions,
		efficiency=turbine_cfg.get("efficiency"),
		case= engineCase,
		bypassratio=bypass_ratio,
		fan = fan,
		compressor = compressor
	)

	print(f"Turbine Wdott: {compressor.wdotc} W")

	coreNozzle = NozzleExit(
		turbine.outlet_conditions,
		ambient_pressure=atmosphere.P_0,
		ideal=core_nozzle_exit_cfg.get("ideal", True),
		temperature_ratio=core_nozzle_exit_cfg.get("temperature_ratio"),
		pressure_ratio=core_nozzle_exit_cfg.get("pressure_ratio")
	)




	components = [
		("atmosphere", atmosphere),
		("inlet", inlet),
		("fan", fan),
		("outer_nozzle_exit", outer_nozzle_exit),
		("compressor", compressor),
		("combustion_chamber", combustion_chamber),
		("core_nozzle_exit", coreNozzle),
	]
	print_component_outlets(components)
	print("============================")
	print(f"Outer Fan Exit_Speed={outer_nozzle_exit.V_e:.3f}")
	print(f"Core Nozzle Exit_Speed={coreNozzle.V_e:.3f}")
	print (f"Work Balance: WdotC = Wdott  = {compressor.wdotc:.3f} W")

if __name__ == "__main__":
	main()