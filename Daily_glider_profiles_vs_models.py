#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 8 2019

@author: aristizabal
"""

#%% User input
# lat and lon bounds
lon_lim = [-110.0,-10.0]
lat_lim = [15.0,45.0]

# urls
url_glider = 'https://data.ioos.us/gliders/erddap'
url_GOFS = 'http://tds.hycom.org/thredds/dodsC/GLBy0.08/expt_93.0/ts3z'
#url_GOFS = 'https://tds.hycom.org/thredds/dodsC/GLBy0.08/latest'
#url_RTOFS = 'https://nomads.ncep.noaa.gov:9090/dods/rtofs/rtofs_global'

# FTP server RTOFS
ftp_RTOFS = 'ftp.ncep.noaa.gov'

nc_files_RTOFS = ['rtofs_glo_3dz_f006_6hrly_hvr_US_east.nc',\
                  'rtofs_glo_3dz_f012_6hrly_hvr_US_east.nc',\
                  'rtofs_glo_3dz_f018_6hrly_hvr_US_east.nc',\
                  'rtofs_glo_3dz_f024_6hrly_hvr_US_east.nc']

# COPERNICUS MARINE ENVIRONMENT MONITORING SERVICE (CMEMS)
url_cmems = 'http://nrt.cmems-du.eu/motu-web/Motu'
service_id = 'GLOBAL_ANALYSIS_FORECAST_PHY_001_024-TDS'
product_id = 'global-analysis-forecast-phy-001-024'
depth_min = '0.493'
out_dir = '/home/aristizabal/crontab_jobs'
ncCOP_global = '/home/aristizabal/Copernicus/global-analysis-forecast-phy-001-024_1565877333169.nc'

# Bathymetry file
bath_file = '/home/aristizabal/bathymetry_files/GEBCO_2014_2D_-100.0_0.0_-10.0_70.0.nc'

#%%
from erddapy import ERDDAP
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as patches
from datetime import datetime, timedelta
import numpy as np
import xarray as xr
from ftplib import FTP
import netCDF4
import os
import os.path
import cmocean

# Do not produce figures on screen
plt.switch_backend('agg')

# Increase fontsize of labels globally
plt.rc('xtick',labelsize=14)
plt.rc('ytick',labelsize=14)
plt.rc('legend',fontsize=14)

#%% Get time bounds for the current day
#ti = datetime.today() 
ti = datetime.today() - timedelta(hours=6)
tini = datetime(ti.year,ti.month,ti.day)
te = ti + timedelta(1)
tend = datetime(te.year,te.month,te.day)

folder = '/www/web/rucool/hurricane/Hurricane_season_' + ti.strftime('%Y') + '/' + ti.strftime('%b-%d') + '/'
os.system('mkdir ' + folder)

#%% Look for datasets in IOOS glider dac
print('Looking for glider data sets')
e = ERDDAP(server = url_glider)

# Grab every dataset available
datasets = pd.read_csv(e.get_search_url(response='csv', search_for='all'))

# Search constraints
kw = {
    'min_lon': lon_lim[0],
    'max_lon': lon_lim[1],
    'min_lat': lat_lim[0],
    'max_lat': lat_lim[1],
    'min_time': tini.strftime('%Y-%m-%dT%H:%M:%SZ'),
    'max_time': tend.strftime('%Y-%m-%dT%H:%M:%SZ'),
}

search_url = e.get_search_url(response='csv', **kw)
#print(search_url)

# Grab the results
search = pd.read_csv(search_url)

# Extract the IDs
gliders = search['Dataset ID'].values

msg = 'Found {} Glider Datasets:\n\n{}'.format
print(msg(len(gliders), '\n'.join(gliders)))

# Setting constraints
constraints = {
        'time>=': str(tini),
        'time<=': str(tend),
        'latitude>=': lat_lim[0],
        'latitude<=': lat_lim[1],
        'longitude>=': lon_lim[0],
        'longitude<=': lon_lim[1],
        }

variables = [
        'depth',
        'latitude',
        'longitude',
        'time',
        'temperature',
        'salinity'
        ]

e = ERDDAP(
        server=url_glider,
        protocol='tabledap',
        response='nc'
        )

#%% Read GOFS 3.1 output
print('Retrieving coordinates from GOFS 3.1')
try:
    GOFS31 = xr.open_dataset(url_GOFS,decode_times=False)
    
    latGOFS = GOFS31.lat[:]
    lonGOFS = GOFS31.lon[:]
    depthGOFS = GOFS31.depth[:]
    ttGOFS = GOFS31.time
    tGOFS = netCDF4.num2date(ttGOFS[:],ttGOFS.units)
except Exception as err:
    latGOFS = np.nan
    lonGOFS = np.nan
    depthGOFS = np.nan
    tGOFS = np.nan 

#%% load RTOFS nc files
print('Loading 6 hourly RTOFS nc files from FTP server')
for t in np.arange(len(nc_files_RTOFS)):
    #file = out_dir + '/' + nc_files_RTOFS[t]
    file = nc_files_RTOFS[t]

    # Login to ftp file
    ftp = FTP('ftp.ncep.noaa.gov')
    ftp.login()
    ftp.cwd('pub/data/nccf/com/rtofs/prod/')

    if tini.month < 10:
        if tini.day < 10:
            ftp.cwd('rtofs.' + str(tini.year) + '0' + str(tini.month) + '0' + str(tini.day))
        else:
            ftp.cwd('rtofs.' + str(tini.year) + '0' + str(tini.month) + str(tini.day))
    else:
        if tini.day < 10:
            ftp.cwd('rtofs.' + str(tini.year) + str(tini.month) + '0' + str(tini.day))
        else:
            ftp.cwd('rtofs.' + str(tini.year) + str(tini.month) + str(tini.day))

    # Download nc files
    print('loading ' + file)
    ftp.retrbinary('RETR '+file, open(file,'wb').write)

#%% Read RTOFS grid and time
print('Retrieving coordinates from RTOFS')
ncRTOFS = xr.open_dataset(nc_files_RTOFS[0])
latRTOFS = ncRTOFS.Latitude[:]
lonRTOFS = ncRTOFS.Longitude[:]
depthRTOFS = ncRTOFS.Depth[:]

tRTOFS = []
for t in np.arange(len(nc_files_RTOFS)):
    ncRTOFS = xr.open_dataset(nc_files_RTOFS[t])
    tRTOFS.append(np.asarray(ncRTOFS.MT[:])[0])

tRTOFS = np.asarray([mdates.num2date(mdates.date2num(tRTOFS[t])) \
          for t in np.arange(len(nc_files_RTOFS))])

#%% Downloading and reading Copernicus grid
COP_grid = xr.open_dataset(ncCOP_global)

latCOP_glob = COP_grid.latitude[:]
lonCOP_glob = COP_grid.longitude[:]
depthCOP_glob = COP_grid.depth[:]

#%% Reading bathymetry data
ncbath = xr.open_dataset(bath_file)
bath_lat = ncbath.variables['lat'][:]
bath_lon = ncbath.variables['lon'][:]
bath_elev = ncbath.variables['elevation'][:]

#%% Looping through all gliders found
for id in gliders:
    print('Reading ' + id )
    e.dataset_id = id
    e.constraints = constraints
    e.variables = variables

    # checking data frame is not empty
    df = e.to_pandas()
    if np.logical_and(len(df.dropna()) != 0,df.columns[0] != 'Error {'):

        # Converting glider data to data frame
        
        df = e.to_pandas(
                index_col='time (UTC)',
                parse_dates=True,
                skiprows=(1,)  # units information can be dropped.
                ).dropna()
        
        # Coverting glider vectors into arrays
        timeg, ind = np.unique(df.index.values,return_index=True)
        latg = df['latitude (degrees_north)'].values[ind]
        long = df['longitude (degrees_east)'].values[ind]

        dg = df['depth (m)'].values
        #vg = df['temperature (degree_Celsius)'].values
        tg = df[df.columns[3]].values
        sg = df[df.columns[4]].values

        delta_z = 0.3
        zn = np.int(np.round(np.nanmax(dg)/delta_z))

        depthg = np.empty((zn,len(timeg)))
        depthg[:] = np.nan
        tempg = np.empty((zn,len(timeg)))
        tempg[:] = np.nan
        saltg = np.empty((zn,len(timeg)))
        saltg[:] = np.nan

        # Grid variables
        depthg_gridded = np.arange(0,np.nanmax(dg),delta_z)
        tempg_gridded = np.empty((len(depthg_gridded),len(timeg)))
        tempg_gridded[:] = np.nan
        saltg_gridded = np.empty((len(depthg_gridded),len(timeg)))
        saltg_gridded[:] = np.nan

        for i,ii in enumerate(ind):
            if i < len(timeg)-1:
                depthg[0:len(dg[ind[i]:ind[i+1]]),i] = dg[ind[i]:ind[i+1]]
                tempg[0:len(tg[ind[i]:ind[i+1]]),i] = tg[ind[i]:ind[i+1]]
                saltg[0:len(sg[ind[i]:ind[i+1]]),i] = sg[ind[i]:ind[i+1]]
            else:
                depthg[0:len(dg[ind[i]:len(dg)]),i] = dg[ind[i]:len(dg)]
                tempg[0:len(tg[ind[i]:len(tg)]),i] = tg[ind[i]:len(tg)]
                saltg[0:len(sg[ind[i]:len(sg)]),i] = sg[ind[i]:len(sg)]

        for t,tt in enumerate(timeg):
            depthu,oku = np.unique(depthg[:,t],return_index=True)
            tempu = tempg[oku,t]
            saltu = saltg[oku,t]
            okdd = np.isfinite(depthu)
            depthf = depthu[okdd]
            tempf = tempu[okdd]
            saltf = saltu[okdd]

            okt = np.isfinite(tempf)
            if np.sum(okt) < 3:
                tempg_gridded[:,t] = np.nan
            else:
                okd = np.logical_and(depthg_gridded >= np.min(depthf[okt]),\
                                     depthg_gridded < np.max(depthf[okt]))
                tempg_gridded[okd,t] = np.interp(depthg_gridded[okd],depthf[okt],tempf[okt])

            oks = np.isfinite(saltf)
            if np.sum(oks) < 3:
                saltg_gridded[:,t] = np.nan
            else:
                okd = np.logical_and(depthg_gridded >= np.min(depthf[oks]),\
                                     depthg_gridded < np.max(depthf[oks]))
                saltg_gridded[okd,t] = np.interp(depthg_gridded[okd],depthf[oks],saltf[oks])

        # Conversion from glider longitude and latitude to GOFS convention
        target_lonGOFS = np.empty((len(long),))
        target_lonGOFS[:] = np.nan
        for i,ii in enumerate(long):
            if ii < 0:
                target_lonGOFS[i] = 360 + ii
            else:
                target_lonGOFS[i] = ii
        target_latGOFS = latg

        # Conversion from glider longitude and latitude to RTOFS convention
        target_lonRTOFS = long
        target_latRTOFS = latg

        # Changing times to timestamp
        tstamp_glider = [mdates.date2num(timeg[i]) for i in np.arange(len(timeg))]
        if isinstance(GOFS31,float):
            tstampGOFS = np.nan
        else:
            ttGOFS = np.asarray([datetime(tGOFS[i].year,tGOFS[i].month,tGOFS[i].day,\
                    tGOFS[i].hour) for i in np.arange(len(tGOFS))])
            tstamp_GOFS = [mdates.date2num(ttGOFS[i]) for i in np.arange(len(ttGOFS))]
        tstamp_RTOFS = [mdates.date2num(tRTOFS[i]) for i in np.arange(len(tRTOFS))]

        # Narrowing time window of GOFS 3.1 to coincide with glider time window
        if isinstance(GOFS31,float): 
            oktimeGOFS = np.nan
            timeGOFS = np.nan
        else:
            #oktimeGOFS = np.where(np.logical_and(tGOFS >= tmin,tGOFS <= tmax))
            oktimeGOFS = np.unique(np.round(np.interp(tstamp_glider,tstamp_GOFS,np.arange(len(tstamp_GOFS)))).astype(int))
            timeGOFS = ttGOFS[oktimeGOFS]

        # Narrowing time window of RTOFS to coincide with glider time window
        oktimeRTOFS = np.unique(np.round(np.interp(tstamp_glider,tstamp_RTOFS,np.arange(len(tstamp_RTOFS)))).astype(int)) 
        timeRTOFS = mdates.num2date(mdates.date2num(tRTOFS[oktimeRTOFS]))

        # interpolating glider lon and lat to lat and lon on GOFS 3.1 time
        sublonGOFS=np.interp(tstamp_GOFS,tstamp_glider,target_lonGOFS)
        sublatGOFS=np.interp(tstamp_GOFS,tstamp_glider,target_latGOFS)

        # getting the model grid positions for sublonm and sublatm
        oklonGOFS=np.round(np.interp(sublonGOFS,lonGOFS,np.arange(len(lonGOFS)))).astype(int)
        oklatGOFS=np.round(np.interp(sublatGOFS,latGOFS,np.arange(len(latGOFS)))).astype(int)

        # Getting glider transect from GOFS 3.1
        print('Getting glider transect from GOFS 3.1')
        if len(oktimeGOFS) == 0:
            target_tempGOFS = np.empty((len(depthRTOFS),1))
            target_tempGOFS[:] = np.nan
            target_saltGOFS = np.empty((len(depthRTOFS),1))
            target_saltGOFS[:] = np.nan
        else:
            target_tempGOFS = np.empty((len(depthGOFS),len(oktimeGOFS)))
            target_tempGOFS[:] = np.nan
            for i in range(len(oktimeGOFS)):
                print(len(oktimeGOFS),' ',i)
                target_tempGOFS[:,i] = GOFS31.variables['water_temp'][oktimeGOFS[i],:,oklatGOFS[i],oklonGOFS[i]]

            target_saltGOFS = np.empty((len(depthGOFS),len(oktimeGOFS)))
            target_saltGOFS[:] = np.nan
            for i in range(len(oktimeGOFS)):
                print(len(oktimeGOFS),' ',i)
                target_saltGOFS[:,i] = GOFS31.variables['salinity'][oktimeGOFS[i],:,oklatGOFS[i],oklonGOFS[i]]

        # interpolating glider lon and lat to lat and lon on RTOFS time
        sublonRTOFS = np.interp(tstamp_RTOFS,tstamp_glider,target_lonRTOFS)
        sublatRTOFS = np.interp(tstamp_RTOFS,tstamp_glider,target_latRTOFS)

        # getting the model grid positions for sublonm and sublatm
        oklonRTOFS = np.round(np.interp(sublonRTOFS,lonRTOFS[0,:],np.arange(len(lonRTOFS[0,:])))).astype(int)
        oklatRTOFS = np.round(np.interp(sublatRTOFS,latRTOFS[:,0],np.arange(len(latRTOFS[:,0])))).astype(int)

        # Getting glider transect from RTOFS
        print('Getting glider transect from RTOFS')
        if len(oktimeRTOFS) == 0:
            target_tempRTOFS = np.empty((len(depthRTOFS),1))
            target_tempRTOFS[:] = np.nan
            target_saltRTOFS = np.empty((len(depthRTOFS),1))
            target_saltRTOFS[:] = np.nan
        else:
            target_tempRTOFS = np.empty((len(depthRTOFS),len(oktimeRTOFS)))
            target_tempRTOFS[:] = np.nan
            for i in range(len(oktimeRTOFS)):
                print(len(oktimeRTOFS),' ',i)
                nc_file = nc_files_RTOFS[i]
                ncRTOFS = xr.open_dataset(nc_file)
                target_tempRTOFS[:,i] = ncRTOFS.variables['temperature'][0,:,oklatRTOFS[i],oklonRTOFS[i]]

            target_saltRTOFS = np.empty((len(depthRTOFS),len(oktimeRTOFS)))
            target_saltRTOFS[:] = np.nan
            for i in range(len(oktimeRTOFS)):
                print(len(oktimeRTOFS),' ',i)
                nc_file = nc_files_RTOFS[i]
                ncRTOFS = xr.open_dataset(nc_file)
                target_saltRTOFS[:,i] = ncRTOFS.variables['salinity'][0,:,oklatRTOFS[i],oklonRTOFS[i]]

        #os.system('rm ' + out_dir + '/' + '*.nc')

        # Downloading and reading Copernicus output
        motuc = 'python -m motuclient --motu ' + url_cmems + \
        ' --service-id ' + service_id + \
        ' --product-id ' + product_id + \
        ' --longitude-min ' + str(np.min(long)-2/12) + \
        ' --longitude-max ' + str(np.max(long)+2/12) + \
        ' --latitude-min ' + str(np.min(latg)-2/12) + \
        ' --latitude-max ' + str(np.max(latg)+2/12) + \
        ' --date-min ' + '"' + str(tini-timedelta(0.5)) + '"' + \
        ' --date-max ' + '"' + str(tend+timedelta(0.5)) + '"' + \
        ' --depth-min ' + depth_min + \
        ' --depth-max ' + str(np.nanmax(depthg)) + \
        ' --variable ' + 'thetao' + ' ' + \
        ' --variable ' + 'so'  + ' ' + \
        ' --out-dir ' + out_dir + \
        ' --out-name ' + id + '.nc' + ' ' + \
        ' --user ' + 'maristizabalvar' + ' ' + \
        ' --pwd ' +  'MariaCMEMS2018'

        os.system(motuc)
        # Check if file was downloaded
        aa = os.system

        COP_file = out_dir + '/' + id + '.nc'
        # Check if file was downloaded
        resp = os.system('ls ' + out_dir +'/' + id + '.nc')
        if resp == 0:
            COP = xr.open_dataset(COP_file)

            latCOP = COP.latitude[:]
            lonCOP = COP.longitude[:]
            depthCOP = COP.depth[:]
            tCOP = np.asarray(mdates.num2date(mdates.date2num(COP.time[:])))
        else:
            latCOP = np.empty(depthCOP_glob.shape[0])
            latCOP[:] = np.nan
            lonCOP = np.empty(depthCOP_glob.shape[0])
            lonCOP[:] = np.nan
            tCOP = np.empty(depthCOP_glob.shape[0])
            tCOP[:] = np.nan

        tmin = tini
        tmax = tend

        #oktimeCOP = np.where(np.logical_and(mdates.date2num(tCOP) >= mdates.date2num(tmin),\
        #                                mdates.date2num(tCOP) <= mdates.date2num(tmax)))
        tstampCOP = mdates.date2num(tCOP)
        oktimeCOP = np.unique(np.round(np.interp(tstamp_glider,tstampCOP,np.arange(len(tstampCOP)))).astype(int))
        timeCOP = tCOP[oktimeCOP]

        # Changing times to timestamp
        tstamp_glider = [mdates.date2num(timeg[i]) for i in np.arange(len(timeg))]
        tstamp_COP = [mdates.date2num(timeCOP[i]) for i in np.arange(len(timeCOP))]

        # interpolating glider lon and lat to lat and lon on Copernicus time
        sublonCOP = np.interp(tstamp_COP,tstamp_glider,long)
        sublatCOP = np.interp(tstamp_COP,tstamp_glider,latg)

        # getting the model grid positions for sublonm and sublatm
        oklonCOP = np.round(np.interp(sublonCOP,lonCOP,np.arange(len(lonCOP)))).astype(int)
        oklatCOP = np.round(np.interp(sublatCOP,latCOP,np.arange(len(latCOP)))).astype(int)

        # getting the model global grid positions for sublonm and sublatm
        oklonCOP_glob = np.round(np.interp(sublonCOP,lonCOP_glob,np.arange(len(lonCOP_glob)))).astype(int)
        oklatCOP_glob = np.round(np.interp(sublatCOP,latCOP_glob,np.arange(len(latCOP_glob)))).astype(int)

        # Getting glider transect from Copernicus model
        print('Getting glider transect from Copernicus model')
        if len(oktimeCOP) == 0:
            target_tempCOP = np.empty((len(depthCOP),1))
            target_tempCOP[:] = np.nan
            target_saltCOP = np.empty((len(depthCOP),1))
            target_saltCOP[:] = np.nan
        else:
            target_tempCOP = np.empty((len(depthCOP),len(oktimeCOP)))
            target_tempCOP[:] = np.nan
            for i in range(len(oktimeCOP)):
                print(len(oktimeCOP),' ',i)
                target_tempCOP[:,i] = COP.variables['thetao'][oktimeCOP[i],:,oklatCOP[i],oklonCOP[i]]

            target_saltCOP = np.empty((len(depthCOP),len(oktimeCOP)))
            target_saltCOP[:] = np.nan
            for i in range(len(oktimeCOP)):
                print(len(oktimeCOP),' ',i)
                target_saltCOP[:,i] = COP.variables['so'][oktimeCOP[i],:,oklatCOP[i],oklonCOP[i]]

        os.system('rm ' + out_dir + '/' + id + '.nc')

        # Convertion from GOFS to glider convention
        lonGOFSg = np.empty((len(lonGOFS),))
        lonGOFSg[:] = np.nan
        for i,ii in enumerate(lonGOFS):
            if ii >= 180.0:
                lonGOFSg[i] = ii - 360
            else:
                lonGOFSg[i] = ii
        latGOFSg = latGOFS

        # Convertion from RTOFS to glider convention
        lonRTOFSg = lonRTOFS[0,:]
        latRTOFSg = latRTOFS[:,0]

        meshlonGOFSg = np.meshgrid(lonGOFSg,latGOFSg)
        meshlatGOFSg = np.meshgrid(latGOFSg,lonGOFSg)

        meshlonRTOFSg = np.meshgrid(lonRTOFSg,latRTOFSg)
        meshlatRTOFSg = np.meshgrid(latRTOFSg,lonRTOFSg)

        meshlonCOP = np.meshgrid(lonCOP,latCOP)
        meshlatCOP = np.meshgrid(latCOP,lonCOP)

        # min and max values for plotting
        min_temp = np.floor(np.nanmin([np.nanmin(df[df.columns[3]]),np.nanmin(target_tempGOFS),np.nanmin(target_tempRTOFS),np.nanmin(target_tempCOP)]))
        max_temp = np.ceil(np.nanmax([np.nanmax(df[df.columns[3]]),np.nanmax(target_tempGOFS),np.nanmax(target_tempRTOFS),np.nanmax(target_tempCOP)]))

        min_salt = np.floor(np.nanmin([np.nanmin(df[df.columns[4]]),np.nanmin(target_saltGOFS),np.nanmin(target_saltRTOFS),np.nanmin(target_saltCOP)]))
        max_salt = np.ceil(np.nanmax([np.nanmax(df[df.columns[4]]),np.nanmax(target_saltGOFS),np.nanmax(target_saltRTOFS),np.nanmax(target_saltCOP)]))

        # Temperature profile
        fig, ax = plt.subplots(figsize=(14, 12))
        grid = plt.GridSpec(5, 2, wspace=0.4, hspace=0.3)

        ax = plt.subplot(grid[:,0])
        plt.plot(tempg,-depthg,'.',color='cyan',label='_nolegend_')
        plt.plot(np.nanmean(tempg_gridded,axis=1),-depthg_gridded,'.-b',\
             label=id[:-14]+' '+str(timeg[0])[0:4]+' '+'['+str(timeg[0])[5:19]+','+str(timeg[-1])[5:19]+']')

        plt.plot(target_tempGOFS,-depthGOFS,'.-',color='lightcoral',label='_nolegend_')
        if len(oktimeGOFS) != 0:
            plt.plot(np.nanmean(target_tempGOFS,axis=1),-depthGOFS,'.-r',markersize=12,linewidth=2,\
                label='GOFS 3.1'+' '+str(timeGOFS[0].year)+' '+'['+str(timeGOFS[0])[5:13]+','+str(timeGOFS[-1])[5:13]+']')
        plt.plot(target_tempRTOFS,-depthRTOFS,'.-',color='mediumseagreen',label='_nolegend_')
        if len(oktimeRTOFS) != 0:
            plt.plot(np.nanmean(target_tempRTOFS,axis=1),-depthRTOFS,'.-g',markersize=12,linewidth=2,\
                label='RTOFS'+' '+str(timeRTOFS[0].year)+' '+'['+str(timeRTOFS[0])[5:13]+','+str(timeRTOFS[-1])[5:13]+']')
        plt.plot(target_tempCOP,-depthCOP,'.-',color='plum',label='_nolegend_')
        if len(oktimeCOP) != 0:
            plt.plot(np.nanmean(target_tempCOP,axis=1),-depthCOP,'.-',color='darkorchid',markersize=12,linewidth=2,\
                label='Copernicus'+' '+str(timeCOP[0].year)+' '+'['+str(timeCOP[0])[5:13]+','+str(timeCOP[-1])[5:13]+']')
        plt.ylabel('Depth (m)',fontsize=20)
        plt.xlabel('Temperature ($^oC$)',fontsize=20)
        plt.title('Temperature Profile ' + id,fontsize=20)
        if np.nanmax(depthg) <= 100:
            plt.ylim([-np.nanmax(depthg)-30,0.1])
        else:
            plt.ylim([-np.nanmax(depthg)-100,0.1])
        plt.legend(loc='lower left',bbox_to_anchor=(-0.2,0.0),fontsize=14)
        plt.grid('on')

        # lat and lon bounds of box to draw
        if len(oklatRTOFS) != 0:
            minlonRTOFS = np.min(meshlonRTOFSg[0][oklatRTOFS.min()-2:oklatRTOFS.max()+2,oklonRTOFS.min()-2:oklonRTOFS.max()+2])
            maxlonRTOFS = np.max(meshlonRTOFSg[0][oklatRTOFS.min()-2:oklatRTOFS.max()+2,oklonRTOFS.min()-2:oklonRTOFS.max()+2])
            minlatRTOFS = np.min(meshlatRTOFSg[0][oklonRTOFS.min()-2:oklonRTOFS.max()+2,oklatRTOFS.min()-2:oklatRTOFS.max()+2])
            maxlatRTOFS = np.max(meshlatRTOFSg[0][oklonRTOFS.min()-2:oklonRTOFS.max()+2,oklatRTOFS.min()-2:oklatRTOFS.max()+2])

        # Getting subdomain for plotting glider track on bathymetry
        oklatbath = np.logical_and(bath_lat >= np.min(latg)-5,bath_lat <= np.max(latg)+5)
        oklonbath = np.logical_and(bath_lon >= np.min(long)-5,bath_lon <= np.max(long)+5)

        bath_latsub = bath_lat[oklatbath]
        bath_lonsub = bath_lon[oklonbath]
        bath_elevs = bath_elev[oklatbath,:]
        bath_elevsub = bath_elevs[:,oklonbath]

        ax = plt.subplot(grid[0:2,1])
        lev = np.arange(-9000,9100,100)
        plt.contourf(bath_lonsub,bath_latsub,bath_elevsub,lev,cmap=cmocean.cm.topo)
        #plt.contour(bath_lonsub,bath_latsub,bath_elevsub,[0],colors='k')
        #plt.contourf(bath_lonsub,bath_latsub,bath_elevsub,cmap='Blues_r')
        #plt.contourf(bath_lonsub,bath_latsub,bath_elevsub,[0,10000],colors='seashell')
        #plt.axis([np.min(long)-5,np.max(long)+5,np.min(latg)-5,np.max(latg)+5])
        plt.plot(long,latg,'.-',color='orange',label='Glider track',\
             markersize=3)
        if len(oklatRTOFS) != 0:
            rect = patches.Rectangle((minlonRTOFS,minlatRTOFS),\
                             maxlonRTOFS-minlonRTOFS,maxlatRTOFS-minlatRTOFS,\
                             linewidth=1,edgecolor='k',facecolor='none')
            ax.add_patch(rect)
        plt.title('Glider track and model grid positions',fontsize=20)
        plt.axis('scaled')
        plt.legend(loc='upper center',bbox_to_anchor=(1.1,1))

        ax = plt.subplot(grid[2,1])
        ax.plot(long,latg,'.-',color='orange',label='Glider track')
        ax.plot(long[0],latg[0],'sc',label='Initial profile time '+str(timeg[0])[0:16])
        ax.plot(long[-1],latg[-1],'sb',label='final profile time '+str(timeg[-1])[0:16])
        if len(oklatGOFS) != 0:
            ax.plot(meshlonGOFSg[0][oklatGOFS.min()-2:oklatGOFS.max()+2,oklonGOFS.min()-2:oklonGOFS.max()+2],\
                meshlatGOFSg[0][oklonGOFS.min()-2:oklonGOFS.max()+2,oklatGOFS.min()-2:oklatGOFS.max()+2].T,\
                '.',color='red')
            ax.plot(lonGOFSg[oklonGOFS],latGOFSg[oklatGOFS],'or',\
                markersize=8,markeredgecolor='k',\
                label='GOFS 3.1 grid points \n nx = ' + str(oklonGOFS) \
                  + '\n ny = ' + str(oklatGOFS) \
                  + '\n [day][hour] = ' + str(np.unique([str(i)[8:10] for i in timeGOFS])) \
                  + str([str(i)[11:13]for i in timeGOFS]))
        if len(oklatRTOFS) != 0:
            ax.plot(meshlonRTOFSg[0][oklatRTOFS.min()-2:oklatRTOFS.max()+2,oklonRTOFS.min()-2:oklonRTOFS.max()+2],\
                meshlatRTOFSg[0][oklonRTOFS.min()-2:oklonRTOFS.max()+2,oklatRTOFS.min()-2:oklatRTOFS.max()+2].T,\
                '.',color='green')
            ax.plot(lonRTOFSg[oklonRTOFS],latRTOFSg[oklatRTOFS],'og',\
                markersize=8,markeredgecolor='k',\
                label='RTOFS grid points \n nx = ' + str(oklonRTOFS) \
                + '\n ny = ' + str(oklatRTOFS) \
                + '\n [day][hour] = ' + str(np.unique([str(i)[8:10] for i in timeRTOFS])) \
                + str([str(i)[11:13]for i in timeRTOFS]))
        if len(oklatCOP) != 0:
            ax.plot(meshlonCOP[0][oklatCOP.min()-2:oklatCOP.max()+2,oklonCOP.min()-2:oklonCOP.max()+2],\
                meshlatCOP[0][oklonCOP.min()-2:oklonCOP.max()+2,oklatCOP.min()-2:oklatCOP.max()+2].T,\
                '.',color='darkorchid')
            ax.plot(lonCOP[oklonCOP],latCOP[oklatCOP],'o',color='darkorchid',\
                markersize=8,markeredgecolor='k',\
                label='Copernicus grid points \n nx = '+ str(oklonCOP_glob) \
                + '\n ny = '+str(oklatCOP_glob) \
                + '\n [day][hour] = ' + str([str(i)[8:10] for i in timeCOP]) \
                + str([str(i)[11:13]for i in timeCOP]))
        ax.legend(loc='upper center',bbox_to_anchor=(0.5,-0.3))

        folder = '/www/web/rucool/hurricane/Hurricane_season_' + ti.strftime('%Y') + '/' + ti.strftime('%b-%d') + '/'
        file = folder+'temp_profile_' + id + '_' + str(tini).split()[0] + '_' + str(tend).split()[0]
        plt.savefig(file,bbox_inches = 'tight',pad_inches = 0.1)

        # Salinity profile
        fig, ax = plt.subplots(figsize=(14, 12))
        grid = plt.GridSpec(5, 2, wspace=0.4, hspace=0.3)

        ax = plt.subplot(grid[:,0])
        plt.plot(saltg,-depthg,'.',color='cyan')
        plt.plot(np.nanmean(saltg_gridded,axis=1),-depthg_gridded,'.-b',\
             label=id[:-14]+' '+str(timeg[0])[0:4]+' '+'['+str(timeg[0])[5:19]+','+str(timeg[-1])[5:19]+']')
        plt.plot(target_saltGOFS,-depthGOFS,'.-',color='lightcoral',label='_nolegend_')
        if len(oktimeGOFS) != 0:
            plt.plot(np.nanmean(target_saltGOFS,axis=1),-depthGOFS,'.-r',markersize=12,linewidth=2,\
                label='GOFS 3.1'+' '+str(timeGOFS[0].year)+' '+'['+str(timeGOFS[0])[5:13]+','+str(timeGOFS[-1])[5:13]+']')
        plt.plot(target_saltRTOFS,-depthRTOFS,'.-',color='mediumseagreen',label='_nolegend_')
        if len(oktimeRTOFS) != 0:
            plt.plot(np.nanmean(target_saltRTOFS,axis=1),-depthRTOFS,'.-g',markersize=12,linewidth=2,\
                label='RTOFS'+' '+str(timeRTOFS[0].year)+' '+'['+str(timeRTOFS[0])[5:13]+','+str(timeRTOFS[-1])[5:13]+']')
        plt.plot(target_saltCOP,-depthCOP,'.-',color='plum',label='_nolegend_')
        if len(oktimeCOP) != 0:
            plt.plot(np.nanmean(target_saltCOP,axis=1),-depthCOP,'.-',color='darkorchid',markersize=12,linewidth=2,\
                label='Copernicus'+' '+str(timeCOP[0].year)+' '+'['+str(timeCOP[0])[5:13]+','+str(timeCOP[-1])[5:13]+']')
        plt.ylabel('Depth (m)',fontsize=20)
        plt.xlabel('Salinity',fontsize=20)
        plt.title('Salinity Profile ' + id,fontsize=20)
        if np.nanmax(depthg) <= 100:
            plt.ylim([-np.nanmax(depthg)-30,0.1])
        else:
            plt.ylim([-np.nanmax(depthg)-100,0.1])
        plt.legend(loc='lower left',bbox_to_anchor=(-0.2,0.0),fontsize=14)
        plt.grid('on')

        # lat and lon bounds of box to draw
        if len(oklatRTOFS) != 0:
            minlonRTOFS = np.min(meshlonRTOFSg[0][oklatRTOFS.min()-2:oklatRTOFS.max()+2,oklonRTOFS.min()-2:oklonRTOFS.max()+2])
            maxlonRTOFS = np.max(meshlonRTOFSg[0][oklatRTOFS.min()-2:oklatRTOFS.max()+2,oklonRTOFS.min()-2:oklonRTOFS.max()+2])
            minlatRTOFS = np.min(meshlatRTOFSg[0][oklonRTOFS.min()-2:oklonRTOFS.max()+2,oklatRTOFS.min()-2:oklatRTOFS.max()+2])
            maxlatRTOFS = np.max(meshlatRTOFSg[0][oklonRTOFS.min()-2:oklonRTOFS.max()+2,oklatRTOFS.min()-2:oklatRTOFS.max()+2])

        # Getting subdomain for plotting glider track on bathymetry
        oklatbath = np.logical_and(bath_lat >= np.min(latg)-5,bath_lat <= np.max(latg)+5)
        oklonbath = np.logical_and(bath_lon >= np.min(long)-5,bath_lon <= np.max(long)+5)

        ax = plt.subplot(grid[0:2,1])
        bath_latsub = bath_lat[oklatbath]
        bath_lonsub = bath_lon[oklonbath]
        bath_elevs = bath_elev[oklatbath,:]
        bath_elevsub = bath_elevs[:,oklonbath]

        lev = np.arange(-9000,9100,100)
        plt.contourf(bath_lonsub,bath_latsub,bath_elevsub,lev,cmap=cmocean.cm.topo)
        #plt.contour(bath_lonsub,bath_latsub,bath_elevsub,[0],colors='k')
        #plt.contourf(bath_lonsub,bath_latsub,bath_elevsub,cmap='Blues_r')
        #plt.contourf(bath_lonsub,bath_latsub,bath_elevsub,[0,10000],colors='seashell')
        #plt.axis([np.min(long)-5,np.max(long)+5,np.min(latg)-5,np.max(latg)+5])
        plt.plot(long,latg,'.-',color='orange',label='Glider track',\
             markersize=3)
        if len(oklatRTOFS) != 0:
            rect = patches.Rectangle((minlonRTOFS,minlatRTOFS),\
                             maxlonRTOFS-minlonRTOFS,maxlatRTOFS-minlatRTOFS,\
                             linewidth=1,edgecolor='k',facecolor='none')
            ax.add_patch(rect)
        plt.title('Glider track and model grid positions',fontsize=20)
        plt.axis('scaled')
        plt.legend(loc='upper center',bbox_to_anchor=(1.1,1))

        ax = plt.subplot(grid[2,1])
        ax.plot(long,latg,'.-',color='orange',label='Glider track')
        ax.plot(long[0],latg[0],'sc',label='Initial profile time '+str(timeg[0])[0:16])
        ax.plot(long[-1],latg[-1],'sb',label='final profile time '+str(timeg[-1])[0:16])
        if len(oklatGOFS) != 0:
            ax.plot(meshlonGOFSg[0][oklatGOFS.min()-2:oklatGOFS.max()+2,oklonGOFS.min()-2:oklonGOFS.max()+2],\
                meshlatGOFSg[0][oklonGOFS.min()-2:oklonGOFS.max()+2,oklatGOFS.min()-2:oklatGOFS.max()+2].T,\
                '.',color='red')
            ax.plot(lonGOFSg[oklonGOFS],latGOFSg[oklatGOFS],'or',\
                markersize=8,markeredgecolor='k',\
                label='GOFS 3.1 grid points \n nx = ' + str(oklonGOFS) \
                    + '\n ny = ' + str(oklatGOFS) \
                    + '\n [day][hour] = ' + str(np.unique([str(i)[8:10] for i in timeGOFS])) \
                    + str([str(i)[11:13]for i in timeGOFS]))
        if len(oklatRTOFS) != 0:
            ax.plot(meshlonRTOFSg[0][oklatRTOFS.min()-2:oklatRTOFS.max()+2,oklonRTOFS.min()-2:oklonRTOFS.max()+2],\
                meshlatRTOFSg[0][oklonRTOFS.min()-2:oklonRTOFS.max()+2,oklatRTOFS.min()-2:oklatRTOFS.max()+2].T,\
                '.',color='green')
            ax.plot(lonRTOFSg[oklonRTOFS],latRTOFSg[oklatRTOFS],'og',\
                markersize=8,markeredgecolor='k',\
                label='RTOFS grid points \n nx = ' + str(oklonRTOFS) \
                + '\n ny = ' + str(oklatRTOFS) \
                + '\n [day][hour] = ' + str(np.unique([str(i)[8:10] for i in timeRTOFS])) \
                + str([str(i)[11:13]for i in timeRTOFS]))
        if len(oklatCOP) != 0:
            ax.plot(meshlonCOP[0][oklatCOP.min()-2:oklatCOP.max()+2,oklonCOP.min()-2:oklonCOP.max()+2],\
                meshlatCOP[0][oklonCOP.min()-2:oklonCOP.max()+2,oklatCOP.min()-2:oklatCOP.max()+2].T,\
                '.',color='darkorchid')
            ax.plot(lonCOP[oklonCOP],latCOP[oklatCOP],'o',color='darkorchid',\
                markersize=8,markeredgecolor='k',\
                label='Copernicus grid points \n nx = '+ str(oklonCOP_glob) \
                + '\n ny = '+str(oklatCOP_glob) \
                + '\n [day][hour] = ' + str([str(i)[8:10]for i in timeCOP]) \
                + str([str(i)[11:13]for i in timeCOP]))
        ax.legend(loc='upper center',bbox_to_anchor=(0.5,-0.3))

        folder = '/www/web/rucool/hurricane/Hurricane_season_' + ti.strftime('%Y') + '/' + ti.strftime('%b-%d') + '/'
        file = folder+'salt_profile_' + id + '_' + str(tini).split()[0] + '_' + str(tend).split()[0]
        plt.savefig(file,bbox_inches = 'tight',pad_inches = 0.1)
