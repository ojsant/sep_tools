#!/home/osant/conda/envs/sep_tools/bin/python3

# Usage instructions (14.11.2025): call signature is "bash weeklyplot.sh <spacecraft> <year> <week>",
# where spacecraft is either "l1", "sta", "psp" or "solo", year is the year you want plots for and week is the week
# number counted up from the Monday of the first week of the year (might be in December!). So if the whole thing
# crashes midway (which it will 100% at some point), then you can continue from where it crashed by looking at
# the printed week number.
# 
# The reason for the bash script workaround I believe was that the memory would get a bit clogged up using one
# Python interpreter. So for every week just throw the interpreter out and start a new one

import os
import sys
import datetime as dt
import multi_inst_plots as m
import matplotlib.pyplot as plt

m.options.resample.value = 60
m.options.resample_mag.value = 15
m.options.resample_stixgoes.value = 0
m.options.l1_av_erne.value = 60
m.options.l1_av_sep.value = 60
m.options.Vsw.value = True
m.options.T.value = True
m.options.N.value = True

# Weekly plot options
print(sys.argv)

if sys.argv[1] == "l1":
    
    m.options.spacecraft.value = "L1 (Wind/SOHO)"
    m.options.stix.value = False
    m.options.goes.value = True

elif sys.argv[1] == "sta":
    m.options.spacecraft.value = "STEREO"
    m.options.ster_sc.value = "A"
    m.options.stix.value = False
    m.options.goes.value = False

elif sys.argv[1] == "psp":
    m.options.spacecraft.value = "Parker Solar Probe"
    m.options.stix.value = False
    m.options.goes.value = False
    m.options.psp_epilo_p.value = False
    print(m.options.psp_epilo_p.value)

elif sys.argv[1] == "solo":
    m.options.spacecraft.value = "Solar Orbiter"
    m.options.stix.value = True
    m.options.goes.value = False

sc = sys.argv[1]
year = int(sys.argv[2])
week = int(sys.argv[3])
startdate = dt.date.fromisocalendar(year, week, 1)      # Monday of given week and year

fig_save_path = f"{os.getcwd()}{os.sep}plots/{sc}/{year}"
os.makedirs(fig_save_path, exist_ok=True)

m.options.startdate.value = startdate
m.options.enddate.value = startdate + dt.timedelta(days=6)

data, metadata = m.load_data()
fig, axs = m.make_plot(show=False)
fig.savefig(fig_save_path + f"/{sc}_{year}_w{week:02d}", bbox_inches="tight")
plt.close(fig)
print("Complete!")
