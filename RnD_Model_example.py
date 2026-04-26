# R&D Model Example for SOA Modeling Bootcamp 2026
# Written by Igor Nikitin, ASA in April 2025

# To run this script you will need:
#  - installation of Python 3.10 or higher (download from https://www.python.org/downloads/)
#  - installation of the matplotlib library for plotting
#       Open Command Prompt and run: pip install matplotlib

#  Once Python and matplotlib are installed, you can run this script from command prompt, vs code, or any other Python IDE.

#  To run from Command Prompt:
#  - navigate to the directory where this file is located (e.g., cd C:\Users\nikit\Desktop\Modeling Bootcamp)
#  - run the command: python RnD_Model_example.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import matplotlib.pyplot as plt
import time

# =========
# 1. Inputs
# =========

Valuation_Date = date(2024, 12, 31)
Last_Projection_Year = 2085

@dataclass(frozen=True)
class PolicyRecord:
    Policy: int
    YOB: int
    Gender: str
    Annual_Benefit: int

Data = [
    PolicyRecord(Policy=1, YOB=1951, Gender="M", Annual_Benefit=20000),
    PolicyRecord(Policy=2, YOB=1950, Gender="M", Annual_Benefit=98000),
    PolicyRecord(Policy=3, YOB=1954, Gender="F", Annual_Benefit=65000),
    PolicyRecord(Policy=4, YOB=1950, Gender="F", Annual_Benefit=49000),
    PolicyRecord(Policy=5, YOB=1955, Gender="M", Annual_Benefit=39000),
    PolicyRecord(Policy=6, YOB=1947, Gender="F", Annual_Benefit=78000),
    PolicyRecord(Policy=7, YOB=1957, Gender="M", Annual_Benefit=28000),
    PolicyRecord(Policy=8, YOB=1945, Gender="M", Annual_Benefit=50000),
    PolicyRecord(Policy=9, YOB=1960, Gender="F", Annual_Benefit=22000),
    PolicyRecord(Policy=10, YOB=1957, Gender="F", Annual_Benefit=96000),
]

Mortality_Rates = {
    "Male": [
        0.001783, 0.000446, 0.000306, 0.000254, 0.000193, 0.000186, 0.000184,
        0.000177, 0.000159, 0.000143, 0.000126, 0.000123, 0.000147, 0.000188,
        0.000236, 0.000282, 0.000325, 0.000364, 0.000399, 0.00043, 0.000459,
        0.000492, 0.000526, 0.000569, 0.000616, 0.000669, 0.000728, 0.000764,
        0.000789, 0.000808, 0.000824, 0.000834, 0.000838, 0.000828, 0.000808,
        0.000789, 0.000783, 0.0008, 0.000837, 0.000889, 0.000955, 0.001029,
        0.00111, 0.001188, 0.001268, 0.001355, 0.001464, 0.001615, 0.001808,
        0.002032, 0.002285, 0.002557, 0.002828, 0.003088, 0.003345, 0.003616,
        0.003922, 0.004272, 0.004681, 0.005146, 0.005662, 0.006237, 0.006854,
        0.00751, 0.00822, 0.009007, 0.009497, 0.010085, 0.010787, 0.011625,
        0.012619, 0.013798, 0.015195, 0.016834, 0.018733, 0.020905, 0.023367,
        0.026155, 0.029306, 0.032858, 0.036927, 0.041703, 0.046957, 0.052713,
        0.059148, 0.066505, 0.075015, 0.084823, 0.095987, 0.108482, 0.122214,
        0.136799, 0.152409, 0.169078, 0.186882, 0.205844, 0.219247, 0.238612,
        0.258341, 0.278219, 0.298452, 0.32361, 0.344191, 0.364633, 0.384783,
        0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4,
        0.4, 0.4, 0.4, 1.0,
    ],
    "Female": [
        0.001801, 0.00045, 0.000287, 0.000199, 0.000152, 0.000139, 0.00013,
        0.000122, 0.000105, 0.000098, 0.000094, 0.000096, 0.000105, 0.00012,
        0.000146, 0.000174, 0.000199, 0.00022, 0.000234, 0.000245, 0.000253,
        0.00026, 0.000266, 0.000272, 0.000275, 0.000277, 0.000284, 0.00029,
        0.0003, 0.000313, 0.000333, 0.000357, 0.000375, 0.00039, 0.000405,
        0.000424, 0.000447, 0.000476, 0.000514, 0.00056, 0.000613, 0.000667,
        0.000723, 0.000774, 0.000823, 0.000866, 0.000917, 0.000983, 0.001072,
        0.001168, 0.00129, 0.001453, 0.001622, 0.001792, 0.001972, 0.002166,
        0.002393, 0.002666, 0.003, 0.003393, 0.003844, 0.004352, 0.004899,
        0.005482, 0.006118, 0.006829, 0.007279, 0.007821, 0.008475, 0.009234,
        0.010083, 0.011011, 0.01203, 0.013154, 0.014415, 0.015869, 0.017555,
        0.0195, 0.021758, 0.024412, 0.027579, 0.031501, 0.036122, 0.041477,
        0.047589, 0.054441, 0.061972, 0.070155, 0.078963, 0.088336, 0.098197,
        0.108323, 0.119188, 0.131334, 0.145521, 0.162722, 0.18212, 0.199661,
        0.217946, 0.236834, 0.256357, 0.283802, 0.304716, 0.325819, 0.346936,
        0.367898, 0.387607, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4,
        0.4, 0.4, 0.4, 0.4, 0.4, 1.0,
    ],
}

Projection_Scale = {
    "Male": [
        0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
        0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
        0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
        0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
        0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
        0.011, 0.011, 0.012, 0.012, 0.013, 0.013, 0.014, 0.014, 0.015, 0.015,
        0.015, 0.015, 0.015, 0.015, 0.015, 0.015, 0.015, 0.015, 0.015, 0.015,
        0.015, 0.015, 0.015, 0.015, 0.015, 0.015, 0.015, 0.015, 0.015, 0.015,
        0.014, 0.013, 0.013, 0.012, 0.011, 0.010, 0.009, 0.009, 0.008, 0.007,
        0.007, 0.006, 0.005, 0.005, 0.004, 0.004, 0.003, 0.003, 0.002, 0.002,
        0.002, 0.001, 0.001, 0.000, 0.000, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0
    ],
    "Female": [
        0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
        0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
        0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
        0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
        0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
        0.01, 0.011, 0.011, 0.011, 0.012, 0.012, 0.012, 0.012, 0.013, 0.013,
        0.013, 0.013, 0.013, 0.013, 0.013, 0.013, 0.013, 0.013, 0.013, 0.013,
        0.013, 0.013, 0.013, 0.013, 0.013, 0.013, 0.013, 0.013, 0.013, 0.013,
        0.012, 0.012, 0.011, 0.010, 0.010, 0.009, 0.008, 0.007, 0.007, 0.006,
        0.006, 0.005, 0.005, 0.004, 0.004, 0.004, 0.003, 0.003, 0.002, 0.002,
        0.002, 0.001, 0.001, 0.000, 0.000, 0, 0, 0, 0, 0,
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0
    ],
}

Random_Numbers = [
    [0.208694776842403, 0.076240032391483, 0.470187205497306, 0.122354274331137, 0.797149903933119, 0.0905320874228277, 0.636212957723396, 0.43801162482321, 0.952139008161835, 0.213028712218303],
    [0.566386459794194, 0.732717232666628, 0.155052395501478, 0.0413595218921514, 0.151649891736026, 0.502741809584208, 0.929635590218535, 0.961085883691624, 0.215606576275289, 0.755307350278393],
    [0.419354114887959, 0.207503906091799, 0.660916683294792, 0.91645913741118, 0.303119080886062, 0.495815689400318, 0.806237190373427, 0.832865597014608, 0.631478900031955, 0.199411248261385],
    [0.53624302170377, 0.325473798531388, 0.983322494822471, 0.376148687919294, 0.466322899863752, 0.6766555223508, 0.620054072402618, 0.861212541702073, 0.875849135574853, 0.199944144501515],
    [0.624941598737948, 0.482082561363773, 0.264876985573646, 0.0334780452863043, 0.993804921197255, 0.445240932725998, 0.311522893445393, 0.467658603332511, 0.955850133073146, 0.878668289211926],
    [0.876720658053207, 0.702339077042697, 0.912563110613544, 0.250803936766412, 0.0947008930752049, 0.972592215704034, 0.589902076892909, 0.262975550013865, 0.201382644751752, 0.0805964532396152],
    [0.203726290777222, 0.910230384202934, 0.596826287944902, 0.887332734307709, 0.254468303206184, 0.723946200714078, 0.757935420438482, 0.190600993138723, 0.666676754603982, 0.0931722142404472],
    [0.105335558055445, 0.49460077585316, 0.364177667903058, 0.207895677479219, 0.634466121555774, 0.210834749212038, 0.371706752304998, 0.515245389065886, 0.672976113791922, 0.573477367855844],
    [0.763589638988726, 0.361368239078531, 0.148210316814755, 0.359789480443886, 0.207004131744993, 0.21409947589712, 0.891996804770191, 0.606356163344291, 0.098363561563124, 0.18688519106378],
    [0.539224446887732, 0.741578613888829, 0.655365463442053, 0.483599760085372, 0.687976301763336, 0.349477775230676, 0.499653989860209, 0.587675726135353, 0.591678665853831, 0.167987729520154],
    [0.353154191063099, 0.127277588803046, 0.192484021544824, 0.293459774668804, 0.393919259383486, 0.466206462612292, 0.0456560524715162, 0.313844483914523, 0.907978524835833, 0.492783691635247],
    [0.793661154073148, 0.160284195141592, 0.101042285783443, 0.595551701932622, 0.857889624281817, 0.898526947974653, 0.132892215894039, 0.57701333912668, 0.56698375899075, 0.152804370285309],
    [0.643712695948719, 0.633797946743023, 0.933472164523003, 0.346806921074699, 0.596397329164103, 0.75093428397214, 0.43280103528369, 0.561043015037863, 0.724624382834039, 0.215663631767871],
    [0.700183146220633, 0.367621487001678, 0.405965252408115, 0.715100923310323, 0.728822384872921, 0.385468874019805, 0.610806801492568, 0.839262284378078, 0.257546372306644, 0.320638954923339],
    [0.739287762925182, 0.0373870927074503, 0.528395648404713, 0.197594311283153, 0.910766800207414, 0.662579495069482, 0.0834986219270443, 0.714828174052012, 0.35704332490305, 0.468987991672794],
    [0.737096005381903, 0.379857400101237, 0.390649478515722, 0.122137350438713, 0.0296447655625073, 0.94801898956972, 0.554756956684148, 0.733294770685605, 0.172286526676883, 0.435582069821073],
    [0.0706917051622445, 0.553945570773022, 0.179729209061965, 0.89403471995157, 0.224552370750384, 0.922681852386028, 0.86623939171601, 0.147096554849494, 0.00140136141623082, 0.505651987285738],
    [0.964025284709025, 0.340066517459034, 0.317075567697411, 0.126814624867775, 0.364493204533823, 0.942316046442508, 0.0108547398942496, 0.814588345657762, 0.845557167663178, 0.612210752886939],
    [0.217944513536205, 0.293970837030776, 0.59236766018332, 0.224627480868757, 0.313680721717773, 0.175228065843567, 0.422190869813166, 0.826543412376072, 0.595875693937, 0.825590865578606],
    [0.169831217971725, 0.241514054704681, 0.796589303622577, 0.537231691080086, 0.652655776106836, 0.749250187815687, 0.644967632797415, 0.0779095850380255, 0.39603384551275, 0.000363266663660378],
    [0.20536014231346, 0.0343070569429277, 0.84328822268481, 0.614050465491644, 0.32241436980192, 0.956273710757009, 0.0990623657993952, 0.677936342938438, 0.725525875643576, 0.557067656680706],
    [0.657525140393701, 0.741512224445486, 0.8170451411204, 0.1577396664925, 0.604405730411993, 0.530750133689353, 0.474452542489737, 0.142998831246915, 0.771885576940304, 0.513839788273021],
    [0.171671616279812, 0.651280250574361, 0.460485022992191, 0.684598298018338, 0.120278725431099, 0.602455665676705, 0.291884761898702, 0.0573806163612479, 0.665153596429701, 0.702184624883104],
    [0.922765535518044, 0.971339912305307, 0.957476079318088, 0.60141687387804, 0.641309698006765, 0.0737697385606598, 0.535471307872435, 0.911340962986253, 0.84452885138863, 0.420148799556553],
    [0.867917060287797, 0.981533033370114, 0.892048855157788, 0.307685650561608, 0.56129846088571, 0.510052371473698, 0.542992791190919, 0.999872022965401, 0.713653265125221, 0.0321716017173875],
]

# ==============================================================================
# 2. Policy calculations for a given Scenario (Calculations tab in the workbook)
# ==============================================================================

def calculate_policy(policy_number: int, scenario_number: int) -> list[dict[str, int]]:
    policy = Data[policy_number - 1]
    random_number = Random_Numbers[scenario_number - 1][policy_number - 1]
    if policy.Gender == "M":
        base_qx_table = Mortality_Rates["Male"]
        improvement_table = Projection_Scale["Male"]
    if policy.Gender == "F":
        base_qx_table = Mortality_Rates["Female"]
        improvement_table = Projection_Scale["Female"]
    policy_results = []
    cumulative_probability_of_survival_tPx = 1.0
    first_projection_year = Valuation_Date.year + 1
    projection_years = list(range(first_projection_year, Last_Projection_Year + 1))

    for projection_year in projection_years:
        age = projection_year - policy.YOB
        if age >= len(base_qx_table):
            base_qx = 1.0
            improvement = 1.0
        else:               
            base_qx = base_qx_table[age]
            improvement = (1- improvement_table[age]) ** (projection_year - 2012)
        improved_qx = base_qx * improvement
        px = 1 - improved_qx
        cumulative_probability_of_survival_tPx *= px
        cumulative_probability_of_death_1_minus_tPx = 1 - cumulative_probability_of_survival_tPx
        survive_1_dead_0 = int(random_number > cumulative_probability_of_death_1_minus_tPx)
        cash_flow = policy.Annual_Benefit * survive_1_dead_0

        policy_results.append({
            "Year": projection_year,
            "Age": age,
            "Base_Qx": base_qx,
            "Improvement": improvement,
            "Improved_Qx": improved_qx,
            "Px": px,
            "Cumulative_Probability_of_Survival_tPx": cumulative_probability_of_survival_tPx,
            "Cumulative_Probability_of_Death_1_minus_tPx": cumulative_probability_of_death_1_minus_tPx,
            "Survive_1_Dead_0": survive_1_dead_0,
            "Total_Cash_Flow": cash_flow,
        })

    return policy_results

# =============================================
# Print results for a given policy and scenario
# =============================================

def print_policy_results(policy_number: int, scenario_number: int) -> None:
    policy_results = calculate_policy(policy_number, scenario_number)
    headers = list(policy_results[0].keys())
    print("\nPolicy Results for Policy Number:", policy_number, "and Scenario Number:", scenario_number)
    print("\t".join(headers))
    for row in policy_results:
        print("\t".join(str(row[header]) for header in headers))

# ==============================================
# 3. Calculate Scenario Results for all policies
# ==============================================

def calculate_scenario_cash_flows(
    scenario_number: int, number_of_policies: int
) -> list[dict[str, int]]:

    cash_flows_by_policy = {
        policy_number: calculate_policy(policy_number, scenario_number)
        for policy_number in range(1, number_of_policies + 1)
    }

    scenario_total_cash_flows = []

    for projection_year in range(len(list(cash_flows_by_policy.values())[0])):
        total_cash_flow_in_a_given_year = sum(
            cash_flows_by_policy[policy_number][projection_year]["Total_Cash_Flow"]
            for policy_number in range(1, number_of_policies + 1)
        )
        scenario_total_cash_flows.append(total_cash_flow_in_a_given_year)

    scenario_results = []
    first_projection_year = Valuation_Date.year + 1
    for projection_year in range(len(scenario_total_cash_flows)):
        year = first_projection_year + projection_year
        cash_flows_for_year = {
            f"Policy_{policy_number}": cash_flows_by_policy[policy_number][projection_year]["Total_Cash_Flow"]
            for policy_number in range(1, number_of_policies + 1)
        }
        total_cash_flow_for_year = scenario_total_cash_flows[projection_year]
        scenario_results.append({"Year": year, **cash_flows_for_year, "Total": total_cash_flow_for_year})
    
    return scenario_results

# =======================================
# Print scenario results for all policies
# =======================================

def print_scenario_results(
    scenario_number: int, number_of_policies: int
) -> None:
    
    scenario_results = calculate_scenario_cash_flows(scenario_number, number_of_policies)

    headers = ["Year"] + [
        f"Policy_{policy_number}"
        for policy_number in range(1, number_of_policies + 1)
    ] + ["Total"]
    print("\nScenario Results for Scenario Number:", scenario_number)
    print("\t".join(headers))
    for row in scenario_results:
        print("\t".join(str(row[header]) for header in headers))

# ==========================================
# Plot scenario results for all policies
# ==========================================

def plot_scenario_results(scenario_number: int, number_of_policies: int) -> None:
    scenario_results = calculate_scenario_cash_flows(scenario_number, number_of_policies)
    years = [row["Year"] for row in scenario_results]
    policy_cash_flows = {
        f"Policy_{policy_number}": [row[f"Policy_{policy_number}"] for row in scenario_results]
        for policy_number in range(1, number_of_policies + 1)
    }
    total_cash_flows = [row["Total"] for row in scenario_results]

    bottom = [0] * len(years)
    for policy_number in range(1, number_of_policies + 1):
        policy_label = f"Policy_{policy_number}"
        plt.bar(years, policy_cash_flows[policy_label], bottom=bottom, label=policy_label)
        bottom = [bottom[i] + policy_cash_flows[policy_label][i] for i in range(len(bottom))]

    plt.plot(years, total_cash_flows, color="black", marker="o", linestyle="--", label="Total")
    plt.xlabel("Year")
    plt.ylabel("Cash Flow")
    plt.title(f"Scenario {scenario_number} Cash Flows by Policy")
    plt.legend()
    plt.show()

# ======================================
# 4. Calculate Total Results by Scenario
# ======================================

def calculate_total_results_by_scenario(number_of_scenarios: int, number_of_policies: int) -> list[dict[str, int]]:
    total_results_by_scenario = []
    first_projection_year = Valuation_Date.year + 1
    for projection_year in range(Last_Projection_Year - Valuation_Date.year):
        year = first_projection_year + projection_year
        total_cash_flows_for_year = {
            f"Scenario_{scenario_number}": calculate_scenario_cash_flows(scenario_number, number_of_policies)[projection_year]["Total"]
            for scenario_number in range(1, number_of_scenarios + 1)
        }
        total_results_by_scenario.append({"Year": year, **total_cash_flows_for_year})
    
    return total_results_by_scenario

# ==============================
# Print results across scenarios
# ==============================

def print_results_across_scenarios(number_of_scenarios: int, number_of_policies: int) -> None:
    total_results_by_scenario = calculate_total_results_by_scenario(number_of_scenarios, number_of_policies)

    headers = ["Year"] + [
        f"Scenario_{scenario_number}"
        for scenario_number in range(1, number_of_scenarios + 1)
    ]
    print("\nResults Across Scenarios:")
    print("\t".join(headers))
    for row in total_results_by_scenario:
        print("\t".join(str(row[header]) for header in headers))

# ===========================
# Plot cash flows by scenario
# ===========================
def plot_cash_flows_by_scenario(number_of_scenarios: int, number_of_policies: int) -> None:
    cash_flows_by_scenario = calculate_total_results_by_scenario(number_of_scenarios, number_of_policies)
    years = [row["Year"] for row in cash_flows_by_scenario]
    for scenario_number in range(1, number_of_scenarios + 1):
        pv_cash_flows = [row[f"Scenario_{scenario_number}"] for row in cash_flows_by_scenario]
        plt.plot(years, pv_cash_flows, label=f"Scenario_{scenario_number}")
    plt.xlabel("Year")
    plt.ylabel("PV Cash Flow")
    plt.title("Cash Flow Projection by Scenario")
    plt.legend()
    plt.show()

# ======================================
# 5. Calculate PV Cash Flows by Scenario
# ======================================

def calculate_pv_cash_flows_by_scenario(number_of_scenarios: int, number_of_policies: int, discount_rate: float) -> dict[int]:
    total_results_by_scenario = calculate_total_results_by_scenario(number_of_scenarios, number_of_policies)
    pv_cash_flows_by_scenario = {}
    valuation_year = Valuation_Date.year

    for scenario_number in range(1, number_of_scenarios + 1):
        cash_flows = [row[f"Scenario_{scenario_number}"] for row in total_results_by_scenario]
        pv_cash_flows = 0
        for i, cash_flow in enumerate(cash_flows):
            year = valuation_year + 1 + i
            pv_cash_flows += cash_flow / (1 + discount_rate) ** (year - valuation_year)
        pv_cash_flows_by_scenario[scenario_number] = pv_cash_flows
    return pv_cash_flows_by_scenario

# ===============================
# Print PV cash flows by scenario
# ===============================

def print_pv_cash_flows_by_scenario(number_of_scenarios: int, number_of_policies: int, discount_rate: float) -> None:
    pv_cash_flows_by_scenario = calculate_pv_cash_flows_by_scenario(number_of_scenarios, number_of_policies, discount_rate)
    print("\nPV of Cash Flows by Scenario:")
    print("Scenario\tPV_Cash_Flow")
    for scenario_number, pv_cash_flow in pv_cash_flows_by_scenario.items():
        print(f"Scenario_{scenario_number}\t{pv_cash_flow:.2f}")

# ================================================
# Calculate the dashboard results across scenarios
# ================================================

def calculate_dashboard_results_by_scenario(number_of_scenarios: int, number_of_policies: int, discount_rate: float) -> dict[str, float]:
    pv_cash_flows_by_scenario = calculate_pv_cash_flows_by_scenario(number_of_scenarios, number_of_policies, discount_rate)
    pv_cash_flow_values = list(pv_cash_flows_by_scenario.values())
    mean_pv_cash_flow = sum(pv_cash_flow_values) / len(pv_cash_flow_values)
    median_pv_cash_flow = sorted(pv_cash_flow_values)[len(pv_cash_flow_values) // 2]
    std_dev_pv_cash_flow = (sum((x - mean_pv_cash_flow) ** 2 for x in pv_cash_flow_values) / len(pv_cash_flow_values)) ** 0.5
    min_pv_cash_flow = min(pv_cash_flow_values)
    max_pv_cash_flow = max(pv_cash_flow_values)

    return {
        "Mean_PV_Cash_Flow": mean_pv_cash_flow,
        "Median_PV_Cash_Flow": median_pv_cash_flow,
        "Std_Dev_PV_Cash_Flow": std_dev_pv_cash_flow,
        "Min_PV_Cash_Flow": min_pv_cash_flow,
        "Max_PV_Cash_Flow": max_pv_cash_flow,
    }

#=========================================
# Print dashboard results across scenarios
#=========================================

def print_dashboard_results_by_scenario(number_of_scenarios: int, number_of_policies: int, discount_rate: float) -> None:
    dashboard_results = calculate_dashboard_results_by_scenario(number_of_scenarios, number_of_policies, discount_rate)
    print("\nDashboard Results:")
    for key, value in dashboard_results.items():
        print(f"{key}: {value:.2f}")

# ==========================================================
# Main execution function to run the model and print results
# ==========================================================

if __name__ == "__main__":

    start_time = time.time()

    policy_number = 10
    scenario_number = 25
    print_policy_results(policy_number,scenario_number)

    number_of_scenarios = 25
    number_of_policies = 10
    discount_rate = 0.04
    print_scenario_results(scenario_number, number_of_policies)
    plot_scenario_results(scenario_number, number_of_policies)
    print_results_across_scenarios(number_of_scenarios, number_of_policies)
    print_pv_cash_flows_by_scenario(number_of_scenarios, number_of_policies, discount_rate)
    print_dashboard_results_by_scenario(number_of_scenarios, number_of_policies, discount_rate)
    plot_cash_flows_by_scenario(number_of_scenarios, number_of_policies)
    
    end_time = time.time()
    print(f"\nTotal runtime: {end_time - start_time:.2f} seconds")

