from matplotlib.colors import Normalize
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize
from matplotlib import cm
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from matplotlib import pyplot as plt
from stixdcpy.quicklook import LightCurves
from seppy.tools import resample_df
from sunpy import timeseries as ts
from sunpy.net import Fido
from sunpy.net import attrs as a
import matplotlib.dates as mdates

def polarity_rtn(Br,Bt,Bn,r,lat,V=400,delta_angle=10):
    """
    Calculates the magnetic field polarity sector for magnetic field data (Br, Bt, Bn) 
    from a spacecraft at a (spherical) distance r (AU) and heliographic latitude lat (deg). 
    Uses the nominal Parker spiral geometry for solar wind speed V (default 400 km/s) for reference.
    delta_angle determines the uncertain angles around 90([90-delta_angle,90+delta_angle]) and 270 
    ([270-delta_angle,270+delta_angle]).
    """
    au = 1.495978707e8 #astronomical units (km)
    omega = 2*np.pi/(25.38*24*60*60) #solar rotation rate (rad/s)
    #Nominal Parker spiral angle at distance r (AU)
    phi_nominal = np.rad2deg(np.arctan(omega*r*au/V))
    #Calculating By and Bx from the data (heliographical coordinates, where meridian centered at sc)
    Bx = Br*np.cos(np.deg2rad(lat)) - Bn*np.sin(np.deg2rad(lat))
    By = Bt
    phi_fix = np.zeros(len(Bx))
    phi_fix[(Bx>0) & (By>0)] = 360.0
    phi_fix[(Bx<0)] = 180.0
    phi = np.rad2deg(np.arctan(-By/Bx)) + phi_fix
    #Turn the origin to the nominal Parker spiral direction
    phi_relative = phi - phi_nominal
    phi_relative[phi_relative>360] -= 360
    phi_relative[phi_relative<0] += 360
    pol = np.nan*np.zeros(len(Br))
    
    pol[((phi_relative>=0) & (phi_relative<=90.-delta_angle)) | ((phi_relative>=270.+delta_angle) & (phi_relative<=360))] = 1
    pol[(phi_relative>=90.+delta_angle) & (phi_relative<=270.-delta_angle)] = -1
    pol[((phi_relative>=90.-delta_angle) & (phi_relative<=90.+delta_angle)) | ((phi_relative>=270.-delta_angle) & (phi_relative<=270.+delta_angle))] = 0
    return pol, phi_relative

def polarity_colorwheel():
    # Generate a figure with a polar projection
    fg = plt.figure(figsize=(1,1))
    ax = fg.add_axes([0.1,0.1,0.8,0.8], projection='polar')

    n = 100  #the number of secants for the mesh
    norm = Normalize(0, np.pi) 
    t = np.linspace(0,np.pi,n)   #theta values
    r = np.linspace(.6,1,2)        #radius values change 0.6 to 0 for full circle
    rg, tg = np.meshgrid(r,t)      #create a r,theta meshgrid
    c = tg                         #define color values as theta value
    im = ax.pcolormesh(t, r, c.T,norm=norm,cmap="bwr")  #plot the colormesh on axis with colormap
    t = np.linspace(np.pi,2*np.pi,n)   #theta values
    r = np.linspace(.6,1,2)        #radius values change 0.6 to 0 for full circle
    rg, tg = np.meshgrid(r,t)      #create a r,theta meshgrid
    c = 2*np.pi-tg                         #define color values as theta value
    im = ax.pcolormesh(t, r, c.T,norm=norm,cmap="bwr")  #plot the colormesh on axis with colormap
    ax.set_yticklabels([])                   #turn of radial tick labels (yticks)
    ax.tick_params(pad=0,labelsize=8)      #cosmetic changes to tick labels
    ax.spines['polar'].set_visible(False)    #turn off the axis spine.
    ax.grid(False)

def polarity_panel(ax,datetimes,phi_relative,bbox_to_anchor=(0.,0.22,1,1.1)):
    pol_ax = inset_axes(ax, height="8%", width="100%", loc=9, bbox_to_anchor=bbox_to_anchor, bbox_transform=ax.transAxes) # center, you can check the different codes in plt.legend?
    pol_ax.get_xaxis().set_visible(False)
    pol_ax.get_yaxis().set_visible(False)
    pol_ax.set_ylim(0,1)
    pol_arr = np.zeros(len(phi_relative))+1
    timestamp = datetimes[2] - datetimes[1]
    norm = Normalize(vmin=0, vmax=180, clip=True)
    mapper = cm.ScalarMappable(norm=norm, cmap=cm.bwr)
    pol_ax.bar(datetimes[(phi_relative>=0) & (phi_relative<180)],pol_arr[(phi_relative>=0) & (phi_relative<180)],color=mapper.to_rgba(phi_relative[(phi_relative>=0) & (phi_relative<180)]),width=timestamp)
    pol_ax.bar(datetimes[(phi_relative>=180) & (phi_relative<360)],pol_arr[(phi_relative>=180) & (phi_relative<360)],color=mapper.to_rgba(np.abs(360-phi_relative[(phi_relative>=180) & (phi_relative<360)])),width=timestamp)
    return pol_ax

def mag_angles(B,Br,Bt,Bn):
    theta = np.arccos(Bn/B)
    alpha = 90-(180/np.pi*theta)

    r = np.sqrt(Br**2 + Bt**2 + Bn**2)
    phi = np.arccos(Br/np.sqrt(Br**2 + Bt**2))*180/np.pi

    sel = np.where(Bt < 0)
    count = len(sel[0])
    if count > 0:
        phi[sel] = 2*np.pi - phi[sel]
    sel = np.where(r <= 0)
    count = len(sel[0])
    if count > 0:
        phi[sel] = 0

    return alpha, phi

def load_solo_stix(start, end, ltc=True, resample=None):
    
    try:
        lc = LightCurves.from_sdc(start_utc=start, end_utc=end, ltc=ltc)
        df_stix = lc.to_pandas()

        if resample is not None:
            df_stix = resample_df(df_stix, resample=resample, pos_timestamp=None)

    except TypeError:
        print("Unable to load STIX data!")
        df_stix = []

    return df_stix

def plot_solo_stix(data, ax, ltc, legends_inside, font_ylabel):
    if isinstance(data, pd.DataFrame):
        for key in data.keys():
            ax.plot(data.index, data[key], ds="steps-mid", label=key)
    if ltc:
        title = 'SolO/STIX (light travel time corr.)'
    else:
        title = 'SolO/STIX'
    if legends_inside:
        ax.legend(loc='upper right', borderaxespad = 0., title=title, fontsize=10)
    else:
        # axs[i].legend(loc='upper right', title=title, bbox_to_anchor=(1, 0.5))
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad = 0., title=title, fontsize=10)
    ax.set_ylabel('Counts', fontsize=font_ylabel)
    ax.set_yscale('log')

def load_goes_xrs(start, end, pick_max=True, resample=None, path=None):
    """
    Load GOES high-cadence XRS data with Fido. Picks largest satellite number available, if none specified.

    Parameters
    ----------

    start : str or dt.datetime
      start date in a parse_time-compatible format
    end : str or dt.datetime
      end date in a parse_time-compatible format
    sat : int (optional)
      GOES satellite number

    Returns
    -------

    df_goes : pd.DataFrame
        data
    sat : int
        satellite number for which data was returned
    """
    try:
        if pick_max:
            result_goes = Fido.search(a.Time(start, end), a.Instrument("XRS"), a.Resolution("flx1s"))
            sat = max(result_goes["xrs"]["SatelliteNumber"])
            print(f"Fetching GOES-{sat} data for {start} - {end}")
            file_goes = Fido.fetch(result_goes["xrs"][result_goes["xrs", "SatelliteNumber"] == sat])

        else:
            result_goes = Fido.search(a.Time(start, end), a.Instrument("XRS"), a.Resolution("flx1s"))
            print(result_goes)
            sat = input("Choose preferred satellite number (integer):")
            print(f"Fetching GOES-{sat} data for {start} - {end}")
            file_goes = Fido.fetch(result_goes, path=path)

        goes = ts.TimeSeries(file_goes, concatenate=True)
        df_goes = goes.to_dataframe()
        
        # Filter data
        df_goes['xrsa'] = df_goes['xrsa'].mask((df_goes['xrsa_quality'] != 0), other=np.nan)   # mask non-zero quality flagged entries as NaN
        df_goes['xrsb'] = df_goes['xrsb'].mask((df_goes['xrsb_quality'] != 0), other=np.nan)  
        df_goes = df_goes[(df_goes['xrsa_quality'] == 0) | (df_goes['xrsb_quality'] == 0)]     # keep entries that have at least one good quality flag

        # Resampling
        if resample is not None:
            df_goes = resample_df(df_goes, resample=resample)

        return df_goes, sat
    except KeyError:
        print(f"No GOES/XRS data found for {start} - {end}!")
        df_goes = []
        sat = ''
        return df_goes, sat

def plot_goes_xrs(data, sat, ax, legends_inside, font_ylabel):
    
    if isinstance(data, pd.DataFrame):
        for channel, wavelength in zip(["xrsa", "xrsb"], ["0.5 - 4.0 Å", "1.0 - 8.0 Å"]):
            ax.plot(data.index, data[channel], ds="steps-mid", label=wavelength)
        title = f"GOES-{sat}/XRS"
        if legends_inside:
            ax.legend(loc="upper right", title=title, borderaxespad = 0., fontsize = 10)
        else:
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', title=title, borderaxespad = 0., fontsize=10)

    ax.set_yscale('log')
    ax.set_ylabel(r"Irradiance ($\mathrm{W/m^2}$)", fontsize=font_ylabel)

def make_fig_axs(options):

    plot_radio = options.radio.value
    #plot_pad = options.pad.value
    plot_mag = options.mag.value
    plot_mag_angles = options.mag_angles.value
    plot_Vsw = options.Vsw.value
    plot_N = options.N.value
    plot_T = options.T.value
    plot_Pdyn = options.p_dyn.value
    plot_stix = options.stix.value
    plot_goes = options.goes.value

    if options.plot_range is None:
        options.plot_start = options.startdt
        options.plot_end = options.enddt
    else:
        options.plot_start = options.plot_range.children[0].value[0]
        options.plot_end = options.plot_range.children[0].value[1]

    if options.spacecraft.value == "L1 (Wind/SOHO)":
        plot_wind_e = options.l1_wind_e.value
        plot_wind_p = options.l1_wind_p.value
        plot_ephin = options.l1_ephin.value
        plot_erne = options.l1_erne.value
        plot_electrons = plot_wind_e or plot_ephin
        plot_protons = plot_wind_p or plot_erne

    if options.spacecraft.value == "PSP":
        plot_epilo_e = options.psp_epilo_e.value
        plot_epihi_e = options.psp_epihi_e.value
        plot_epilo_p = options.psp_epilo_p.value
        plot_epihi_p = options.psp_epihi_p.value
        plot_electrons = plot_epilo_e or plot_epihi_e
        plot_protons = plot_epilo_p or plot_epihi_p

    if options.spacecraft.value == "SolO":
        plot_electrons = options.solo_electrons.value   # TODO separate instruments?
        plot_protons = options.solo_protons.value

    if options.spacecraft.value == "STEREO":
        plot_het_e = options.ster_het_e.value
        plot_het_p = options.ster_het_p.value
        plot_sept_e = options.ster_sept_e.value
        plot_sept_p = options.ster_sept_p.value
        plot_electrons = plot_het_e or plot_sept_e
        plot_protons = plot_het_p or plot_sept_p

    font_ylabel = 20
    font_legend = 10

    if options.spacecraft.value == "PSP":
        panels = 1*plot_radio + 1*plot_stix + 1*plot_goes + 1*plot_electrons + 1*plot_protons + 2*plot_mag_angles + 1*plot_mag + 1* plot_Vsw + 1* plot_N + 1* plot_T + 1*plot_Pdyn 
    elif options.spacecraft.value == "SolO":
        panels = 1*plot_stix + 1*plot_goes + 1*plot_electrons + 1*plot_protons + 2*plot_mag_angles + 1*plot_mag + 1* plot_Vsw + 1* plot_N + 1* plot_T
        
    else: 
        panels = 1*plot_radio + 1*plot_stix + 1*plot_goes + 1*plot_electrons + 1*plot_protons + 2*plot_mag_angles + 1*plot_mag + 1* plot_Vsw + 1* plot_N + 1* plot_T

    panel_ratios = list(np.zeros(panels)+1)

    if options.spacecraft.value == "SolO":      # TODO remove this once RPW is included
        # if plot_radio:
        #     panel_ratios[0] = 2
        if plot_electrons and plot_protons:
            panel_ratios[0 + 1*plot_stix + 1*plot_goes] = 2
            panel_ratios[1 + 1*plot_stix + 1*plot_goes] = 2
        if plot_electrons or plot_protons:    
            panel_ratios[0 + 1*plot_stix + 1*plot_goes] = 2

    else:
        if plot_radio:
            panel_ratios[0] = 2
        if plot_electrons and plot_protons:
            panel_ratios[0 + 1*plot_radio + 1*plot_stix + 1*plot_goes] = 2
            panel_ratios[1 + 1*plot_radio + 1*plot_stix + 1*plot_goes] = 2
        if plot_electrons or plot_protons:    
            panel_ratios[0 + 1*plot_radio + 1*plot_stix + 1*plot_goes] = 2
    
    if panels == 3:
        fig, axs = plt.subplots(nrows=panels, sharex=True, figsize=[12, 4*panels])#, gridspec_kw={'height_ratios': panel_ratios})# layout="constrained")
    else:
        fig, axs = plt.subplots(nrows=panels, sharex=True, figsize=[12, 3*panels], gridspec_kw={'height_ratios': panel_ratios})# layout="constrained")
        #fig, axs = plt.subplots(nrows=panels, sharex=True, dpi=100, figsize=[7, 1.5*panels], gridspec_kw={'height_ratios': panel_ratios})# layout="constrained")

    if panels == 1:
        axs = [axs]
    
    if panels == 0:
        print("No instruments chosen!")
        return (None, None)

    if options.spacecraft.value == "L1 (Wind/SOHO)":
        axs[0].set_title('Near-Earth spacecraft (Wind, SOHO)', fontsize=font_ylabel)
    elif options.spacecraft.value == "PSP":
        axs[0].set_title('Parker Solar Probe', fontsize=font_ylabel)
    elif options.spacecraft.value == "STEREO":
        axs[0].set_title(f'STEREO {options.ster_sc.value}', fontsize=font_ylabel)
    else:
        axs[0].set_title(f'Solar Orbiter', fontsize=font_ylabel)

    axs[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M\n%b %d'))
    axs[-1].xaxis.set_tick_params(rotation=0)
    axs[-1].set_xlabel(f"Time (UTC) / Date in {options.plot_start.year}", fontsize=15)
    axs[-1].set_xlim(options.plot_start, options.plot_end)
    fig.subplots_adjust(hspace=0.1)
    fig.patch.set_facecolor('white')
    fig.set_dpi(200)

    if options.spacecraft.value != "STEREO":
        print(f"Plotting {options.spacecraft.value} data for timerange {options.plot_start} - {options.plot_end}")
    else:
        print(f"Plotting STEREO {options.ster_sc.value} data for timerange {options.plot_start} - {options.plot_end}")

    return fig, axs