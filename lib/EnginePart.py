import yaml
from pathlib import Path
import numpy as np
from scipy.optimize import fsolve

class gass_properties:
    def __init__(self, gamma=1.4, R=287.0, C_p=1004.0, H_PR=43e6):

        self.gamma = float(gamma)  # Specific heat ratio for air
        self.R = float(R)  # Specific gas constant for air in J/(kg *K)
        self.C_p = float(C_p)  # Specific heat at constant pressure for air in J/(kg *K)
        self.H_PR = float(H_PR)  # Heating value of the fuel in J/kg


class EngineComponent:
    def __init__(
        self,
        station_id,
        inlet_id=None,
        outlet_id=None,
        inlet_conditions=None,
        gas_properties=None,
    ):
        self.station_id = station_id
        self.inlet_id = inlet_id
        self.outlet_id = outlet_id
        self.inlet_conditions = inlet_conditions
        self.gass_properties = gas_properties if gas_properties is not None else gass_properties()
        self.outlet_conditions = None

    def getOutletConditions(self):
        raise NotImplementedError("Subclasses must implement getOutletConditions")
        

class Atmosphere(EngineComponent):
    def __init__(self, P_0, T_0, M_0, gas_properties=None):
        super().__init__(
            station_id=0,
            inlet_id=None,
            outlet_id=0,
            inlet_conditions=None,
            gas_properties=gas_properties,
        )

        self.P_0 = P_0
        self.T_0 = T_0
        self.M = M_0
        self.V = None
        self.outlet_conditions = self.getOutletConditions()

    def calculate_tau_r(self):
        tau_r = 1 + (self.gass_properties.gamma - 1) / 2 * self.M ** 2
        T_t1 = self.T_0 * tau_r
        return tau_r, T_t1
    
    def calculate_phi_r(self):
        _, T_t1 = self.calculate_tau_r()
        phi_r = (T_t1 / self.T_0) ** (self.gass_properties.gamma / (self.gass_properties.gamma - 1))
        return phi_r
    

    def calculate_V_0(self):
        self.V = self.M * (self.gass_properties.gamma * self.gass_properties.R * self.T_0) ** 0.5
        return self.V

    
    def getOutletConditions(self):
        _, T_t1 = self.calculate_tau_r()
        phi_r = self.calculate_phi_r()
        P_t1 = self.P_0 * phi_r
        self.outlet_conditions = (P_t1, T_t1)
        return self.outlet_conditions
    

class Inlet(EngineComponent):
    def __init__(self, inlet_conditions, ideal=True, temperature_ratio=None, pressure_ratio =None):
        super().__init__(
            station_id=2,
            inlet_id=1,
            outlet_id=2,
            inlet_conditions=inlet_conditions,
        )

        if ideal:
            self.tau = 1.0
            self.phi = 1.0
        else:
            if temperature_ratio is None or pressure_ratio is None:
                raise ValueError("temperature_ratio and pressure_ratio are required when ideal=False")
            self.tau = float(temperature_ratio)
            self.phi = float(pressure_ratio)

        self.outlet_conditions = self.getOutletConditions()

    def getOutletConditions(self):
        self.P_tin, self.T_tin = self.inlet_conditions
        self.P_tex = self.P_tin * self.phi
        self.T_tex = self.T_tin * self.tau
        self.outlet_conditions = (self.P_tex, self.T_tex)
        return self.outlet_conditions
    
    

    
    

class CombustionChamber(EngineComponent):
    def __init__(self, inlet_conditions, efficiency, pressure_ratio, T_t4,case = None, bypassratio = None, gas_properties=None):
        super().__init__(
            station_id=4,
            inlet_id=3,
            outlet_id=4,
            inlet_conditions=inlet_conditions,
            gas_properties=gas_properties,
        )

        self.nu = efficiency # Efisiensi (?) miu or smth
        self.phi = pressure_ratio
        self.T_t4 = T_t4
        self.case = case
        self.bypassratio = bypassratio
        if self.case == "turboJet" or self.case is None:
            self.f  = self.calculate_fuel_air_ratio()
        elif self.case == "turbofanSS":
            if self.bypassratio is None:
                raise ValueError("Bypass ratio is required for turbofan calculations")  
            self.f  = self.calculate_fuel_air_ratio()/(1+self.bypassratio) # For turbofan, fuel is added to both the core and bypass streams, so we divide by (1 + bypass ratio) to get the effective fuel-to-air ratio for the core stream.
        elif self.case == "MSturbofan":
            self.f = self.calculate_fuel_air_ratio()

    
        self.outlet_conditions = self.getOutletConditions()


    def calculate_fuel_air_ratio(self):
        self.f = self.gass_properties.C_p*(self.T_t4-self.inlet_conditions[1])/self.gass_properties.H_PR
        return self.f


    def getOutletConditions(self):
        self.P_t4 = self.inlet_conditions[0] * self.phi
        self.outlet_conditions = self.P_t4, self.T_t4
        return self.outlet_conditions

class NozzleExit(EngineComponent):
    def __init__(self, inlet_conditions, ambient_pressure, gas_properties=None, ideal=True, temperature_ratio=None, pressure_ratio=None):
        super().__init__(
            station_id=9,
            inlet_id=7,
            outlet_id=9,
            inlet_conditions=inlet_conditions,
            gas_properties=gas_properties,
        )

        # (P_t4, T_t4) from the combustion chamber

        if ideal:
            self.tau = 1.0
            self.phi = 1.0
        else:
            if temperature_ratio is None or pressure_ratio is None:
                raise ValueError("temperature_ratio and pressure_ratio are required when ideal=False")
            self.tau = float(temperature_ratio)
            self.phi = float(pressure_ratio)

        self.T_t9 = self.inlet_conditions[1] * self.tau
        self.P_t9 = self.inlet_conditions[0] * self.phi
        self.P_9 = ambient_pressure

        self.T9 = self.calculate_T9()
        self.V_e = self.Calculate_exit_velocity()
        self.outlet_conditions = self.P_9, self.T9

    def calculate_T9(self):
        self.T9 = self.T_t9 * (self.P_9 / self.P_t9) ** ((self.gass_properties.gamma - 1) / self.gass_properties.gamma)
        print(f"T9: {self.T9:.2f} K")
        return self.T9
    

    def Calculate_exit_velocity(self):
        T9 = self.calculate_T9()
        print(f"T9: {T9:.2f} K")
        Cp = self.gass_properties.C_p
        self.V_e = (2 * Cp * (self.T_t9 -T9))**0.5 
        print(f"Exit Velocity (V_e): {self.V_e:.2f} m/s")
        return self.V_e
    

class Compressor(EngineComponent):
    def __init__(self, inlet_conditions, pressure_ratio, efficiency, bypassratio=None, case=None, fan = None):
        super().__init__(
            station_id=3,
            inlet_id=2,
            outlet_id=3,
            inlet_conditions=inlet_conditions,
        )

        self.case = case
        # (P_t2, T_t2) from the inlet
        self.phi = pressure_ratio
        self.nu = efficiency
        self.bypassratio = bypassratio
        
        # Calculate tau_c first
        self.tau = self.calculate_tau_c()

        # Input conditions from the inlet
        self.P_tin = self.inlet_conditions[0] 
        self.T_tin = self.inlet_conditions[1]
        
        # Output conditions for the compressor
        self.T_tex = self.T_tin * self.tau
        self.P_tex= self.P_tin * self.phi
        self.fan = fan

        
        self.outlet_conditions = self.P_tex, self.T_tex

        # Calculate work after all conditions are set
        if self.case == "turboJet" or self.case is None:
            self.wdotc = self.calculate_w_dotc()
        elif self.case == "turbofanSS":
            if self.fan is None:
                raise ValueError("Fan instance is required for turbofan compressor calculations")
            self.wdotc = self.calculate_w_dotc_turbofanSS(self.fan)  # For turbofan, work is calculated in the turbine based on the fan and compressor conditions

    def calculate_w_dotc(self):
        self.wdotc = self.gass_properties.C_p * self.T_tin * (self.tau - 1) 
        return self.wdotc
    
    def calculate_w_dotc_turbofanSS(self, fan):
        self.wdotc = self.gass_properties.C_p * self.T_tin/(1+self.bypassratio) * (self.bypassratio*(self.fan.tau - 1)+self.tau - 1) 
        return self.wdotc

    def calculate_tau_c(self):
        self.tau = self.phi**((self.gass_properties.gamma - 1) / self.gass_properties.gamma)
        return self.tau
    
class Turbine(EngineComponent):
    def __init__(self, inlet_conditions, efficiency, case=None, fan=None, compressor=None, combustion_chamber=None, fan_duct=None, bypassratioMS=None):
        super().__init__(
            station_id=5,
            inlet_id=4,
            outlet_id=5,
            inlet_conditions=inlet_conditions,
        )

        # (P_t4, T_t) from the combustion chamber
        self.nu_m = efficiency
        self.compressor = compressor  # type: Compressor
        self.fan = fan  # class: Compressor
        # inlet conditions from the combustion chamber
        self.P_tin = self.inlet_conditions[0] 
        self.T_tin = self.inlet_conditions[1]
        self.bypassratioMS = bypassratioMS
        self.case = case

        self.combustion_chamber = combustion_chamber
        self.fan_duct = fan_duct
        
        # Calculate tau and phi before using them
        if case == "turboJet" or case is None:
            self.tau = self.calculate_tau_turboJet()
            self.phi = self.calculate_phi_turboJet()
        
        if case == "turbofanSS":
            self.tau = self.calculate_tau_turboFanSS()
            self.phi = self.calculate_phi_turboFanSS()

        if case == "MSturbofan":
            if self.compressor is None:
                raise ValueError("Compressor instance is required for MS turbofan turbine calculations")
            if self.fan is None:
                raise ValueError("Fan instance is required for MS turbofan turbine calculations")
            if self.combustion_chamber is None:
                raise ValueError("Combustion chamber instance is required for MS turbofan turbine calculations")
            if self.fan_duct is None:
                raise ValueError("Fan duct instance is required for MS turbofan turbine calculations")
            self.phi = self.calculate_phi_MSturbofan()
            self.tau = self.calculate_tau_MSturbofan()
            self.bypassratio = self.calculate_bypassratio_MSturbofan()

        # Output conditions for the turbine
        self.T_tex = self.T_tin * self.tau
        self.P_tex = self.P_tin * self.phi

        
        self.outlet_conditions = self.P_tex, self.T_tex

    # Case: turbojet
    def calculate_tau_turboJet(self):
        if self.compressor is None:
            raise ValueError("Compressor instance required for turbine calculations")
        self.tau = 1 - (self.compressor.T_tin/self.T_tin)*(self.compressor.tau - 1)
        return self.tau
    def calculate_phi_turboJet(self):
        self.phi = self.tau**(self.gass_properties.gamma/(self.gass_properties.gamma-1))
        return self.phi
    
    # Case: turbofanSS
    def calculate_tau_turboFanSS(self):
        if self.compressor is None:
            raise ValueError("Compressor instance required for turbofan turbine calculations")
        if self.compressor.bypassratio is None:
            raise ValueError("Compressor Bypass ratio required for turbine calculations")
        if self.fan is None:
            raise ValueError("Fan instance required for turbofan turbine calculations")
        self.tau = 1 - (self.compressor.T_tin/self.T_tin)*(self.bypassratioMS*(self.fan.tau - 1)+(self.compressor.tau-1))
        return self.tau

    def calculate_phi_turboFanSS(self):
        self.phi = self.tau**(self.gass_properties.gamma/(self.gass_properties.gamma-1))
        return self.phi

    # Case: MS turbofan

    def calculate_phi_MSturbofan(self):
        self.phi_f = self.fan.phi
        self.phi_fd = self.fan_duct.phi
        self.phi_c = self.compressor.phi
        self.phi_b = self.combustion_chamber.phi
        self.phi = (self.phi_f * self.phi_fd)/(self.phi_c * self.phi_b)

        return self.phi
    

    def calculate_tau_MSturbofan(self):
        self.tau = self.phi**((self.gass_properties.gamma - 1) / self.gass_properties.gamma)
        return self.tau
    
    def calculate_bypassratio_MSturbofan(self):
        self.bypassratio = (
            (self.T_tin * (1 - self.tau)) - (self.compressor.T_tin * (self.compressor.tau - 1))
        ) / (self.compressor.T_tin * (self.fan.tau - 1))
        return self.bypassratio
    

class Mixer(EngineComponent):
    def __init__(self, ideal=True, temperature_ratio=None, pressure_ratio=None, turbine=None, fanduct=None
                 ,Mach_in = None):
        super().__init__(
            station_id=6,
            inlet_id=5,
            outlet_id=6,
            inlet_conditions=None,
        )

        if turbine is None:
            raise ValueError("turbine instance is required")
        if fanduct is None:
            raise ValueError("fanduct instance is required")
        if Mach_in is None:
            raise ValueError("Mach_in is required")

        # Inlet conditions from the turbine and fan duct
        self.turbine = turbine  # type: Turbine
        self.bypassratio = self.turbine.bypassratio 
        self.T_t5 = self.turbine.T_tex
        self.P_t5 = self.turbine.P_tex 
        
        self.fan_duct = fanduct  # type: Inlet
        self.T_t15 = self.fan_duct.T_tex
        self.P_t15 = self.fan_duct.P_tex
        
        self.Mach_in = float(Mach_in)

        if ideal:
            self.tau = 1.0
            self.phi = 1.0
        else:
            if temperature_ratio is None or pressure_ratio is None:
                raise ValueError("temperature_ratio and pressure_ratio are required when ideal=False")
            self.tau = float(temperature_ratio)
            self.phi = float(pressure_ratio)

        self.mix_result = self.mixer_analysis_refined(
            self.P_t5,
            self.T_t5,
            self.P_t15,
            self.T_t15,
            self.bypassratio,
            self.Mach_in,
            gamma=self.gass_properties.gamma,
            cp=self.gass_properties.C_p,
        )

        self.M6 = self.mix_result["M6"]
        self.T_tex = self.calculate_T_tex()
        self.P_tex = self.mix_result["pt6 [Pa]"] 
        self.outlet_conditions = self.P_tex, self.T_tex

    def mixer_analysis_refined(self, pt5, tt5, pt15, tt15, alpha, m5, gamma=1.4, cp=1004.0):
        """
        Solves the Mixer Outlet (Station 6) using cp-based formulas
        from the MS Turbofan Cycle slides.
        """
        # 1. Normalized mass flows (Core m_dot = 1)
        mdot_core = 1.0
        mdot_bypass = alpha * mdot_core
        mdot_total = mdot_core + mdot_bypass

        # 2. Total Temperature at 6 (Energy Balance)
        tt6 = (alpha * tt15 + tt5) / (1 + alpha)

        # 3. Static Pressures (p5 and p15)
        m15 = m5
        p5 = pt5 * (1 + (gamma - 1) / 2 * m5**2) ** (-gamma / (gamma - 1))
        p15 = p5

        # 4. Areas A5 and A15
        def calculate_area(mdot, p, mach, tt):
            denominator = (p * mach * gamma) / np.sqrt(cp * (gamma - 1) * tt)
            correction = np.sqrt(1 + (gamma - 1) / 2 * mach**2)
            return mdot * (denominator * correction) ** -1

        a5 = calculate_area(mdot_core, p5, m5, tt5)
        a15 = calculate_area(mdot_bypass, p15, m15, tt15)

        # 5. Mixer Geometry (Assumption: Constant Area Mixer)
        a6 = a5 + a15

        # 6. Momentum Balance to find M6
        i5 = p5 * a5 * (1 + gamma * m5**2)
        i15 = p15 * a15 * (1 + gamma * m15**2)
        i_total = i5 + i15

        def objective_function(m6_value):
            p6_guess = i_total / (a6 * (1 + gamma * m6_value**2))
            lhs = p6_guess * m6_value * np.sqrt(1 + (gamma - 1) / 2 * m6_value**2)
            rhs = (mdot_total * np.sqrt(cp * (gamma - 1) * tt6)) / (a6 * gamma)
            return lhs - rhs

        m6_final = fsolve(objective_function, m5)[0]

        # 7. Final Output Pressures
        p6_final = i_total / (a6 * (1 + gamma * m6_final**2))
        pt6_final = p6_final * (1 + (gamma - 1) / 2 * m6_final**2) ** (gamma / (gamma - 1))

        return {
            "M6": round(float(m6_final), 4),
            "p6 [Pa]": round(float(p6_final), 1),
            "Tt6 [K]": round(float(tt6), 2),
            "pt6 [Pa]": round(float(pt6_final), 1),
        }

    def calculate_T_tex(self):
        self.T_tex = (self.bypassratio * self.T_t15 + self.T_t5) / (1 + self.bypassratio)
        return self.T_tex


class EngineParameters:
    def __init__(self, atmosphere=None, combustion_chamber=None, nozzle_exit=None):
        self.atmosphere = atmosphere
        self.combustion_chamber = combustion_chamber
        self.nozzle_exit = nozzle_exit
      
    def calculate_thrust(self):
        if self.atmosphere is None:
            raise ValueError("atmosphere instance is required")
        if self.nozzle_exit is None:
            raise ValueError("nozzle_exit instance is required")
        
        V_e = self.nozzle_exit.Calculate_exit_velocity()
        print(f"Exit Velocity (V_e): {V_e:.2f} m/s")
        V_0 = self.atmosphere.calculate_V_0()
        thrust = V_e-V_0   
        return thrust





def load_yaml_config(config_path):
    with Path(config_path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def create_gas_properties_from_config(config):
    gas_cfg = config.get("gas") or config.get("gas_data") or {}

    return gass_properties(
        gamma=gas_cfg.get("gamma", 1.4),
        R=gas_cfg.get("r_j_per_kgk", gas_cfg.get("R", 287.0)),
        C_p=gas_cfg.get("cp_j_per_kgk", gas_cfg.get("C_p", 1004.0)),
        H_PR=gas_cfg.get("hpr_j_per_kg", gas_cfg.get("H_PR", 43e6)),
    )


def create_atmosphere_from_config(config, gas_properties=None):
    atm_cfg = config.get("atmosphere") or config.get("ambient_data") or {}

    if not atm_cfg:
        raise ValueError("Missing atmosphere/ambient_data section in config")

    P_0 = atm_cfg.get("pressure_pa", atm_cfg.get("ambient_pressure"))
    T_0 = atm_cfg.get("temperature_k", atm_cfg.get("ambient_temperature"))
    M_0 = atm_cfg.get("mach", atm_cfg.get("ambient_mach_number"))

    if P_0 is None or T_0 is None or M_0 is None:
        raise ValueError("Atmosphere config must define pressure, temperature, and mach")

    gas = gas_properties if gas_properties is not None else create_gas_properties_from_config(config)

    return Atmosphere(P_0=float(P_0), T_0=float(T_0), M_0=float(M_0), gas_properties=gas)