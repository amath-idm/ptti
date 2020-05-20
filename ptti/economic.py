import yaml
from math import ceil, exp
from ptti.economic_data import econ_inputs

def calcEconOutputs(model_outputs, scenario):

    locals().update(econ_inputs['Shutdown'])
    locals().update(econ_inputs['Test'])
    locals().update(econ_inputs['Trace'])

    Output = dict()
    Output['policy'] = scenario
    Output['model_output'] = model_outputs
    Output['timesteps'] = Output['model_output'][0]
    Days = len(model_outputs[0])  # Total number of days modeled
    Output['compartments'] = model_outputs[1]

    Costs = 0

    Output['Economic'] = dict()
    Output['parameters'] = dict()
    Output['variables'] = dict()
    # GEt parameter values, which can change over time due to interventions.
    for var in scenario['parameters'].keys():
        Output['variables'][var] = [float(scenario['parameters'][var]) for d in range(Days)] # Initial value.
    for intervention in scenario['interventions']:
        for var in intervention['parameters']:
            if var in Output['variables'].keys():
                Output['variables'][var][intervention['time']:] = [float(intervention['parameters'][var]) for i in range(Days-int(intervention['time']))]

    Output['I'] = [float(a + b) for a, b in zip(Output['compartments'][:, 4], Output['compartments'][:,5])]

    Output['Economic']['trace'] = [0 for d in range(Days)] # Number of people that must be traced.
    for d in range(Days):
        if Output['variables']['theta'][d] > 0:
            Output['Economic']['trace'][d] = Output['variables']['c'][d] * Output['variables']['theta'][d] / (
                Output['variables']['gamma'][d] + Output['variables']['theta'][d] *
                (1 + Output['variables']['eta'][d] * Output['variables']['chi'][d]) ) *\
                                         float(Output['compartments'][d, 6]) #IU
    # if True: #policy['Trace']: # Currently, we always assumes we pay to trace,

    To_Trace = Output['Economic']['trace']

    # Now we need to find the number of tracers needed in each window.
    Tracers_Needed_Per_Hiring_Window = []
    Period_Lengths = []
    Period_Starts = []
    Period_Ends = []
    Period_Start = 0
    # Two ways to do periods for hiring; per policy period, or per window. We can do both.

    for p in Output['policy']['interventions']:
        Period_End = p['time']
        Period_Starts.append(Period_Start)
        Period_Ends.append(Period_End)
        Period_Lengths.append(Period_End - Period_Start)
        Tracers_This_Period = max(To_Trace[Period_Start:Period_End]) * econ_inputs['Trace']['Time_to_Trace_Contact']
        Tracers_Needed_Per_Hiring_Window.append(Tracers_This_Period)
        Period_Start = Period_End # For next period.
    # Last Period:
    if Days > Period_Start:
        Period_Starts.append(Period_Start)
        Period_Ends.append(Days)
        Period_Lengths.append(Days - Period_Start)
        Tracers_Needed_Per_Hiring_Window.append(max(To_Trace[Period_Start:Days]) * econ_inputs['Trace']['Time_to_Trace_Contact'])

    # We assume that each day, all people whose contacts can be traced have all contacts traced by a team.
    # This means to keep tracing on a one-day lag, i.e. by end of the next day,  we need enough people to trace
    # the maximum expected number in any one day during that period.
    Max_Tracers = max(Tracers_Needed_Per_Hiring_Window)

    # We assume we need supervisors full time, regardless of number of tracers at the time.
    Number_of_Tracing_Supervisors = Max_Tracers / econ_inputs['Trace']['Tracers_Per_Supervisor']
    # The above now does a bunch of checking to get the numbers for tracers needed. Now we take the sum.
    Total_Max_Tracing_Workers = Number_of_Tracing_Supervisors + econ_inputs['Trace']['Number_of_Tracing_Team_Leads'] + Max_Tracers
    Recruitment_Costs = econ_inputs['Trace']['Hiring_Cost'] * Total_Max_Tracing_Workers

    Tracers_fixed_cost = (Number_of_Tracing_Supervisors * (econ_inputs['Trace']['Tracing_Supervisor_Salary'] + econ_inputs['Trace']['Phone_Credit_Costs']) * Days) + \
                         (econ_inputs['Trace']['Number_of_Tracing_Team_Leads'] * (econ_inputs['Trace']['Team_Lead_Salary'] + econ_inputs['Trace']['Phone_Credit_Costs']) * Days) + \
                         Recruitment_Costs + econ_inputs['Trace']['Tracer_Training_Course_Cost'] + \
                         econ_inputs['Trace']['Cost_Per_Extra_Phones_for_Tracers'] * Total_Max_Tracing_Workers

    Costs += Tracers_fixed_cost

    Supervisor_Travel_costs = econ_inputs['Trace']['Daily_Travel_Cost'] * (Number_of_Tracing_Supervisors + econ_inputs['Trace']['Number_of_Tracing_Team_Leads']) * \
        sum(Period_Lengths)

    Tracer_Days_Needed = sum([(a * b) for a, b in zip(Tracers_Needed_Per_Hiring_Window, Period_Lengths)])
    econ_inputs['Trace']['Tracing_Worker_Travel_Costs'] = econ_inputs['Trace']['Daily_Travel_Cost'] * econ_inputs['Trace']['Rural_Pct']  # Rural Tracers Travel Costs
    #Cost Per Tracer includes PHone credits.
    Tracers_cost = (econ_inputs['Trace']['Tracer_Salary'] + econ_inputs['Trace']['Phone_Credit_Costs'] + econ_inputs['Trace']['Tracing_Worker_Travel_Costs']) * \
                    Tracer_Days_Needed + Supervisor_Travel_costs

    Costs += Tracers_cost

    Costs += econ_inputs['Trace']['Tracing_Daily_Public_Communications_Costs'] * Days

    # That is all costs from the original cost spreadsheet for Tracing.

    Trace_Outputs=dict()
    Trace_Outputs['Tracers_Needed_Per_Hiring_Window'] = Tracers_Needed_Per_Hiring_Window
    Trace_Outputs['Period_Lengths'] = Period_Lengths
    Trace_Outputs['Tracers_fixed_cost'] = Tracers_fixed_cost
    Trace_Outputs['Tracers_cost'] = Tracers_cost

    #Testing Level is now set by Theta, as such:.
    # theta: 100000 / N
    Test_Outputs = dict()

    Testing_Costs = 0 # We will add to this.

    Output['Economic']['tests'] = [0 for d in range(Days)] # Number of people tested.
    for d in range(Days):
        if Output['variables']['theta'][d] > 0:
            Output['Economic']['tests'][d] = Output['policy']['initial']['N'] * Output['variables']['theta'][d]

    Daily_tests = Output['Economic']['tests']  # Test needs over time.


    Max_Tests_In_Hiring_Window = []  # This determines how many lab techs we need per period.
    Labs_Per_Window = []
    Maximum_tests = max(Daily_tests)

    for i in range(0, len(Period_Lengths)):
        Window_Tests_max = max(Daily_tests[Period_Starts[i]: Period_Ends[i]])
        Max_Tests_In_Hiring_Window.append(Window_Tests_max)
        Machines_Needed_In_Window = Window_Tests_max / econ_inputs['Test']['Tests_per_Machine_per_Day']
        Labs_Per_Window.append(Machines_Needed_In_Window / econ_inputs['Test']['PCR_Machines_Per_Lab']) # Others can be shut down.

    # Fixed Testing Costs:
    Total_Required_PCR_Machines = max(Max_Tests_In_Hiring_Window) / (econ_inputs['Test']['Tests_per_Machine_per_Day'])
    Max_Lab_Staff = Total_Required_PCR_Machines / econ_inputs['Test']['PCR_Machines_Per_Lab']  # 1 Supervisor per lab.
    Max_Lab_Staff += Total_Required_PCR_Machines / (econ_inputs['Test']['Shifts_per_Day'] * econ_inputs['Test']['Lab_Techs_Per_Machine_Per_Shift'])
    Testing_Costs += Total_Required_PCR_Machines*econ_inputs['Test']['PCR_Machines_Cost'] # Buy Machines
    Testing_Costs += Max_Lab_Staff * econ_inputs['Trace']['Hiring_Cost'] # Hire Staff. One Time Cost.

    Total_Required_Tests = sum(Daily_tests)
    Testing_Costs += Total_Required_Tests * econ_inputs['Test']['Cost_Per_PCR_Test']

    for p in range(0, len(Period_Lengths)):
        Machines_In_Window = Max_Tests_In_Hiring_Window[p] / econ_inputs['Test']['Tests_per_Machine_per_Day']
        Labs_In_Window = Machines_In_Window / econ_inputs['Test']['PCR_Machines_Per_Lab']
        Curr_Period_Days = Period_Lengths[p]
        Testing_Costs += econ_inputs['Test']['Lab_Overhead_Cost_Daily'] * Curr_Period_Days
        # Labs in use are all fully staffed.
        # Staff Costs
        Supervisors = Labs_In_Window  # 1 Supervisor per lab.
        Testing_Costs += Supervisors * econ_inputs['Test']['Lab_Supervisor_Salary'] * Curr_Period_Days
        Daily_Lab_Workers = Labs_In_Window * econ_inputs['Test']['PCR_Machines_Per_Lab'] * econ_inputs['Test']['Shifts_per_Day'] * \
                            econ_inputs['Test']['Lab_Techs_Per_Machine_Per_Shift']
        Testing_Costs += Daily_Lab_Workers * econ_inputs['Test']['Lab_Tech_Salary']
        Testing_Costs += econ_inputs['Test']['Staff_Training_Cost'] * (Daily_Lab_Workers + Supervisors) # Once Per Period

        Testing_Costs += Machines_In_Window * Curr_Period_Days * econ_inputs['Test']['PCR_Machine_Daily_Maintenance']

    Testing_Costs += sum(Daily_tests)*econ_inputs['Test']['Cost_Per_PCR_Test'] # Cost for the actual tests.


    Test_Outputs = dict()
    Test_Outputs['Max_Labs'] = Total_Required_PCR_Machines / econ_inputs['Test']['PCR_Machines_Per_Lab']
    Test_Outputs['Max_Total_Staff'] = Max_Lab_Staff
    Test_Outputs['Total_Tests'] = sum(Daily_tests)

    Costs += Testing_Costs

    ## Medical Outcomes
    # Because the R compartment is cumulative, we can take the final value as the total number of cases.
    Total_Resolved_Cases = Output['compartments'][-1,6] + Output['compartments'][-1,7] # RU + RD
    locals().update(econ_inputs['Medical']) #Retreive local variables
    Medical_Outcomes = dict()
    Medical_Outcomes['Cases'] = Total_Resolved_Cases
    Medical_Outcomes['Deaths'] = Total_Resolved_Cases * econ_inputs['Medical']['IFR']

    In_Hospital_Deaths = econ_inputs['Medical']['Hospitalized_Pct_Deaths'] * Medical_Outcomes['Deaths']

    # We work out number of hospitalizations backwards from data.
    # econ_inputs['Medical']['ICU_Pct'] of patients go to the ICU, and the fatality rate for those cases is econ_inputs['Medical']['ICU_Fatality'].
    # econ_inputs['Medical']['ICU_Pct'] * Hospital_Cases * econ_inputs['Medical']['ICU_Fatality'] + (1-econ_inputs['Medical']['ICU_Pct']) * Hospital_Cases * Non_econ_inputs['Medical']['ICU_Fatality'] = In_Hospital_Deaths.
    # Hospital_Cases = In_Hospital_Deaths / econ_inputs['Medical']['ICU_Pct'] * econ_inputs['Medical']['ICU_Fatality'] + (1-econ_inputs['Medical']['ICU_Pct']) * Non_econ_inputs['Medical']['ICU_Fatality']

    Medical_Outcomes['Hospital_Cases'] = In_Hospital_Deaths / (econ_inputs['Medical']['ICU_Pct']*econ_inputs['Medical']['ICU_Fatality'] + \
                                                               (1-econ_inputs['Medical']['ICU_Pct']) * econ_inputs['Medical']['Non_ICU_Fatality'])
    Medical_Outcomes['ICU_Cases'] = Medical_Outcomes['Hospital_Cases'] * econ_inputs['Medical']['ICU_Pct']

    Medical_Outcomes['NHS_Costs'] = Medical_Outcomes['Deaths'] * econ_inputs['Medical']['NHS_Death_Cost'] + \
                                    Medical_Outcomes['ICU_Cases'] * econ_inputs['Medical']['NHS_ICU_Cost'] + \
                                    Medical_Outcomes['Hospital_Cases'] * econ_inputs['Medical']['NHS_Hospital_Cost']

    Medical_Outcomes['Productivity_Loss'] = Medical_Outcomes['Deaths'] * econ_inputs['Medical']['Productivity_Death_Cost'] + \
                                            Medical_Outcomes['ICU_Cases'] * econ_inputs['Medical']['Productivity_ICU_Cost'] + \
                                            Medical_Outcomes['Hospital_Cases'] * econ_inputs['Medical']['Productivity_Hospital_Cost'] + \
                                            Medical_Outcomes['Cases'] * econ_inputs['Medical']['Productivity_Symptomatic_Cost'] * econ_inputs['Medical']['Pct_Symptomatic']

    Output['Medical'] = Medical_Outcomes

    ### Now, calculate fraction of economy open.

    # Economy Scales with Output['variables']['c'].
    # Economy minimum is: econ_inputs['Shutdown']['UK_Shutdown_GDP_Penalty'], with econ_inputs['Shutdown']['UK_Shutdown_Contacts']
    # Full strength is 0 penalty at econ_inputs['Shutdown']['UK_Open_Contacts']
    Daily_GDP = []
    Economy_Fraction_Daily = []
    Daily_GDP_Base = econ_inputs['Shutdown']['UK_GDP_Monthly'] / 30
    for d in range(Days):
        Shutdown_Fraction = (Output['variables']['c'][d] - econ_inputs['Shutdown']['UK_Shutdown_Contacts']) / (econ_inputs['Shutdown']['UK_Open_Contacts'] - econ_inputs['Shutdown']['UK_Shutdown_Contacts'])
        Economy_Fraction_Daily.append(1-Shutdown_Fraction)
        Daily_GDP.append((1-Shutdown_Fraction*econ_inputs['Shutdown']['UK_Shutdown_GDP_Penalty'])*Daily_GDP_Base)

    Overall_Period_GDP = sum(Daily_GDP)
    Full_Shutdown_GDP = Days * Daily_GDP_Base * (1-econ_inputs['Shutdown']['UK_Shutdown_GDP_Penalty'])
    No_Pandemic_GDP = Days * Daily_GDP_Base

    Output['Economic']['GDP'] = dict()
    Output['Economic']['GDP']['Projected'] = Overall_Period_GDP
    Output['Economic']['GDP']['Reduction_from_Baseline'] = 1-(Overall_Period_GDP/No_Pandemic_GDP)
    Output['Economic']['GDP']['Benefit_over_Shutdown'] = Overall_Period_GDP - Full_Shutdown_GDP
    Output['Economic']['Total_Costs'] = float(Costs)
    Output['Trace_Outputs'] = Trace_Outputs
    Output['Test_Outputs'] = Test_Outputs

    return Output  # What else is useful to graph / etc?