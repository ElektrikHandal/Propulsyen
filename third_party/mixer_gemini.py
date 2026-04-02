import numpy as np
from scipy.optimize import fsolve

def mixer_analysis_refined(pt5, tt5, pt15, tt15, alpha, m5, gamma=1.4, cp=1004.0):
    """
    Solves the Mixer Outlet (Station 6) using the exact cp-based formulas 
    from the MS Turbofan Cycle slides.
    """
    # 1. Normalized mass flows (Core m_dot = 1)
    mdot_core = 1.0
    mdot_bypass = alpha * mdot_core
    mdot_total = mdot_core + mdot_bypass # This is m_dot_0 in your slides
    
    # 2. Total Temperature at 6 (Energy Balance)
    tt6 = (alpha * tt15 + tt5) / (1 + alpha)
    
    # 3. Static Pressures (p5 and p15)
    # Assumption: p5 = p15 and M5 = M15 (given M5=0.5)
    m15 = m5
    p5 = pt5 * (1 + (gamma - 1)/2 * m5**2)**(-gamma / (gamma - 1))
    p15 = p5
    
    # 4. Areas A5 and A15 using the exact slide formula:
    # A = mdot * [ (p * M * gamma / sqrt(cp * (gamma-1) * Tt)) * sqrt(1 + (gamma-1)/2 * M^2) ]^-1
    def calculate_area(mdot, p, M, tt):
        denominator = (p * M * gamma) / np.sqrt(cp * (gamma - 1) * tt)
        correction = np.sqrt(1 + (gamma - 1)/2 * M**2)
        return mdot * (denominator * correction)**-1

    a5 = calculate_area(mdot_core, p5, m5, tt5)
    a15 = calculate_area(mdot_bypass, p15, m15, tt15)
    
    # 5. Mixer Geometry (Assumption: Constant Area Mixer)
    a6 = a5 + a15
    
    # 6. Momentum (Impulse) Balance to find M6
    # Impulse I = p * A * (1 + gamma * M^2)
    i5 = p5 * a5 * (1 + gamma * m5**2)
    i15 = p15 * a15 * (1 + gamma * m15**2)
    i_total = i5 + i15
    
    # We solve for M6 using the combined Continuity/Momentum relation from your slide:
    # p6 * M6 * sqrt(1 + (gamma-1)/2 * M6^2) = (mdot_0 * sqrt(cp * (gamma-1) * Tt6)) / (A6 * gamma)
    def objective_function(M6):
        # Calculate p6 based on momentum conservation at this Mach guess
        p6_guess = i_total / (a6 * (1 + gamma * M6**2))
        
        # Left Hand Side (LHS) of the slide equation
        lhs = p6_guess * M6 * np.sqrt(1 + (gamma - 1)/2 * M6**2)
        
        # Right Hand Side (RHS) of the slide equation
        rhs = (mdot_total * np.sqrt(cp * (gamma - 1) * tt6)) / (a6 * gamma)
        
        return lhs - rhs

    m6_final = fsolve(objective_function, m5)[0]
    
    # 7. Final Output Pressures
    p6_final = i_total / (a6 * (1 + gamma * m6_final**2))
    pt6_final = p6_final * (1 + (gamma - 1)/2 * m6_final**2)**(gamma / (gamma - 1))
    
    return {
        "M6": round(m6_final, 4),
        "p6 [Pa]": round(p6_final, 1),
        "Tt6 [K]": round(tt6, 2),
        "pt6 [Pa]": round(pt6_final, 1)
    }

# --- Verification with Example Data ---
data = {
    "pt5": 63424, "tt5": 864.97, 
    "pt15": 63424, "tt15": 306.95, 
    "alpha": 8.417, "m5": 0.5, "cp": 1004.0
}

res = mixer_analysis_refined(**data)
print(f"Results: {res}")