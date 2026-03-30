import yaml
from pathlib import Path


class gass_properties:
    def __init__(self):

        self.gamma = 1.4  # Specific heat ratio for air
        self.R = 287.0  # Specific gas constant for air in J/(kg *K)
        self.C_p = 1004  # Specific heat at constant pressure for air in kJ/(kg *K)
        self.H_PR = 43.0  # Heating value of the fuel in MJ/kg
        

class Atmosphere:
    def __init__(self, P_0, T_0, M_0, gas_properties=None):
        self.P_0 = P_0
        self.T_0 = T_0
        self.M = M_0
        self.gass_properties = gas_properties if gas_properties is not None else gass_properties()

    def calculate_tau_r(self):
        tau_r = 1 + (self.gass_properties.gamma - 1) / 2 * self.M ** 2
        T_t1 = self.T_0 * tau_r
        return tau_r, T_t1
    
    def calculate_phi_r(self):
        _, T_t1 = self.calculate_tau_r()
        phi_r = (T_t1 / self.T_0) ** (self.gass_properties.gamma / (self.gass_properties.gamma - 1))
        return phi_r
    

    def calculate_V_0(self):
        V_0 = self.M * (self.gass_properties.gamma * self.gass_properties.R * self.T_0) ** 0.5
        return V_0

    
    def getOutletConditions(self):
        _, T_t1 = self.calculate_tau_r()
        phi_r = self.calculate_phi_r()
        P_t1 = self.P_0 * phi_r
        return P_t1, T_t1
    

class Inlet:
    def __init__(self, inlet_conditions, ideal=True, tau_d=None, phi_d=None):
        self.inlet_conditions = inlet_conditions
        self.station_id = 2

        if ideal:
            self.tau_d = 1.0
            self.phi_d = 1.0
        else:
            if tau_d is None or phi_d is None:
                raise ValueError("tau_d and phi_d are required when ideal=False")
            self.tau_d = float(tau_d)
            self.phi_d = float(phi_d)

    def getOutletConditions(self):
        P_t1, T_t1 = self.inlet_conditions
        P_t2 = P_t1 * self.phi_d
        T_t2 = T_t1 * self.tau_d
        return P_t2, T_t2
    

class CombustionChamber:
    def __init__(self, inlet_conditions, nu_b, phi_b, T_t4, gas_properties=None):
        self.station_id = 4
        self.inlet_conditions = inlet_conditions #(P_t2, T_t2) from the nozzle
        self.nu_b = nu_b # Efisiensi (?) miu or smth
        self.phi_b = phi_b
        self.T_t4 = T_t4
        self.gass_properties = gas_properties if gas_properties is not None else gass_properties()

    

    def calculate_fuel_air_ratio(self):
        self.f = self.gass_properties.C_p*(self.T_t4-self.inlet_conditions[1])/self.gass_properties.H_PR
        return self.f


    def getOutletConditions(self):
        self.P_t4 = self.inlet_conditions[0] * self.phi_b
        return self.P_t4, self.T_t4

class NozzleExit:
    def __init__(self, inlet_conditions, ambient_pressure, gas_properties=None, ideal=True, tau_n=None, phi_n=None):
        self.station_id = 9
        self.inlet_conditions = inlet_conditions # (P_t4, T_t4) from the combustion chamber
        self.gass_properties = gas_properties if gas_properties is not None else gass_properties()

        if ideal:
            self.tau_n = 1.0
            self.phi_n = 1.0
        else:
            if tau_n is None or phi_n is None:
                raise ValueError("tau_n and phi_n are required when ideal=False")
            self.tau_n = float(tau_n)
            self.phi_n = float(phi_n)

        self.T_t9 = self.inlet_conditions[1] * self.tau_n
        self.P_t9 = self.inlet_conditions[0] * self.phi_n
        self.P_9 = ambient_pressure

    def calculate_T9(self):
        T9 = self.T_t9 * (self.P_9 / self.P_t9) ** ((self.gass_properties.gamma - 1) / self.gass_properties.gamma)
        print(f"T9: {T9:.2f} K")
        return T9
    

    def Calculate_exit_velocity(self):
        T9 = self.calculate_T9()
        print(f"T9: {T9:.2f} K")
        Cp = self.gass_properties.C_p
        
        V_e = (2 * Cp * (self.T_t9 -T9))**0.5 
        print(f"Exit Velocity (V_e): {V_e:.2f} m/s")
        return V_e

    def getOutletConditions(self):
        return self.P_t9, self.T_t9
    

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


def main():

    ## Load the YAML file
    config_path = Path(__file__).resolve().parent.parent / 'config' / 'config.yaml'
    with config_path.open('r') as file:
        config = yaml.safe_load(file)


    # ========================================#
    #            ATMOSPHERE
    # ========================================#
    P_0 = config['ambient_data']['ambient_pressure']
    T_0 = config['ambient_data']['ambient_temperature']
    M = config['ambient_data']['ambient_mach_number']
    atmosphere = Atmosphere(P_0, T_0, M)
    P_t1, T_t1 = atmosphere.getOutletConditions()


    # ========================================#
    #            NOZZLE
    # ========================================#
    Nozzle_inlet = (P_t1, T_t1)
    Nozzle_ideal_cycle = config['nozzle_data']['ideal_cycle']

    if Nozzle_ideal_cycle:
        nozzle = Inlet((P_t1, T_t1), ideal=True)
    else:
        nozzle_data = config['nozzle_data']
        nozzle = Inlet(
            (P_t1, T_t1),
            ideal=False,
            tau_d=nozzle_data.get('tau_diffuser'),
            phi_d=nozzle_data.get('phi_diffuser'),
        )

    P_t2, T_t2 = nozzle.getOutletConditions()

    # ========================================#
    #            Combustion Chamber
    # ========================================#
    combusion_chamber_inlet = (P_t2, T_t2)
    combusion_chamber_nu_b = config['combustion_chamber_data']['combustion_efficiency']
    combusion_chamber_phi_b = config['combustion_chamber_data']['combustion_pressure_loss']
    combusion_chamber_T_t4 = config['combustion_chamber_data']['combustion_temperature']

    combusion_chamber = CombustionChamber(combusion_chamber_inlet, nu_b=combusion_chamber_nu_b, phi_b=combusion_chamber_phi_b, T_t4=combusion_chamber_T_t4)

    P_t4, T_t4 = combusion_chamber.getOutletConditions()


    # =======================================#
    #            Nozzle Exit         
    # ========================================#
    nozzle_exit_inlet = (P_t4, T_t4)
    nozzle_exit_ideal_cycle = config['nozzle_exit_data']['ideal_cycle']
    if nozzle_exit_ideal_cycle:
        nozzle_exit = NozzleExit(nozzle_exit_inlet, ambient_pressure=P_0, ideal=True)
    else:
        nozzle_exit = NozzleExit(
            nozzle_exit_inlet,
            ambient_pressure=P_0,
            ideal=False,
            tau_n=config['nozzle_exit_data'].get('tau_nozzle'),
            phi_n=config['nozzle_exit_data'].get('phi_nozzle'),
        ) 

    P_t9, T_t9 = nozzle_exit.getOutletConditions()  



    # ========================================#
    #            ENGINE PARAMETERS
    # ========================================#
    Engine = EngineParameters(atmosphere=atmosphere, combustion_chamber=combusion_chamber, nozzle_exit=nozzle_exit)
    thrust = Engine.calculate_thrust()

    # ========================================#           
    #  STRUCTURED OUTPUT
    # ========================================#

    structured_output = {
        'outlet_conditions': {
            'P_t1': P_t1,
            'T_t1': T_t1,
            'P_t2': P_t2,
            'T_t2': T_t2,
            'P_t4': P_t4,
            'T_t4': T_t4,
            'P_t9': P_t9,
            'T_t9': T_t9,
            'Nozzle_ideal_cycle': Nozzle_ideal_cycle,


        }
    }

    print(structured_output)

    Engine_param ={
        'Engine_Parameters': {
            'Thrust': thrust,
        }
    }

    print(structured_output)

    print(Engine_param)




if __name__ == "__main__":
    main()


