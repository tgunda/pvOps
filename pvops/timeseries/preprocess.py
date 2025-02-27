# A set of preprocessing methods, both based on photovoltaic-specific physics and data quality methods.

import pvlib
import pvanalytics
from timezonefinder import TimezoneFinder
import pandas as pd


def establish_solar_loc(prod_df, prod_col_dict, meta_df, meta_col_dict):
    """Adds solar position column using pvLib.

    Parameters
    ----------
    prod_df : DataFrame
        A data frame corresponding to production data containing a datetime index.

    prod_col_dict : dict of {str : str}
        A dictionary that contains the column names associated with the production data,
        which consist of at least:

        - **siteid** (*string*), should be assigned to site-ID column name in prod_df

    meta_df : DataFrame
        A data frame corresponding to site metadata.
        At the least, the columns in meta_col_dict be present.
        The index must contain the site IDs used in prod_df.

    meta_col_dict : dict of {str : str}
        A dictionary that contains the column names relevant for the meta-data

        - **longitude** (*string*), should be assigned to site's longitude
        - **latitude** (*string*), should be assigned to site's latitude

    Returns
    -------
    Original dataframe (copied) with new timeseries solar position data using
    the same column name definitions provided in pvLib.
    """
    prod_df = prod_df.copy()
    meta_df = meta_df.copy()

    sites = prod_df['randid'].unique()
    longitude_col = meta_col_dict['longitude']
    latitude_col = meta_col_dict['latitude']

    positional_columns = ['apparent_zenith',
                          'zenith',
                          'apparent_elevation',
                          'elevation',
                          'azimuth',
                          'equation_of_time']
    for site in sites:
        site_mask = prod_df[prod_col_dict['siteid']] == site
        prod_df.loc[site_mask, positional_columns] = (
            pvlib.solarposition.spa_python(prod_df.loc[site_mask].index,
                                           meta_df.loc[site, longitude_col],
                                           meta_df.loc[site, latitude_col]
                                           ))

    return prod_df


def normalize_production_by_capacity(prod_df,
                                     prod_col_dict,
                                     meta_df,
                                     meta_col_dict):
    """Normalize power by capacity. This preprocessing step is meant as a
    step prior to a modeling attempt where a model is trained on multiple
    sites simultaneously.

    Parameters
    ----------
    prod_df: DataFrame
        A data frame corresponding to production data.
    prod_df_col_dict: dict of {str : str}
        A dictionary that contains the column names associated with the production data,
        which consist of at least:

        - **energyprod** (*string*), should be assigned to production data in prod_df
        - **siteid** (*string*), should be assigned to site-ID column name in prod_df
        - **capacity_normalized_power** (*string*), should be assigned to a column name 
          where the normalized output signal will be stored

    meta_df: DataFrame
        A data frame corresponding to site metadata.
        At the least, the columns in meta_col_dict be present.
    meta_col_dict: dict of {str : str}
        A dictionary that contains the column names relevant for the meta-data

        - **siteid** (*string*), should be assigned to site-ID column name
        - **dcsize** (*string*), should be assigned to column name corresponding
          to site's DC size

    Returns
    -------
    prod_df : DataFrame
        normalized production data
    """

    prod_df = prod_df.copy()
    meta_df = meta_df.copy()

    output_name = prod_col_dict["capacity_normalized_power"]
    power_name = prod_col_dict["energyprod"]
    dcsize_name = meta_col_dict["dcsize"]

    individual_sites = set(meta_df[meta_col_dict['siteid']].tolist())

    for site in individual_sites:
        # Get site-specific meta data
        site_meta_mask = meta_df.loc[:, meta_col_dict["siteid"]] == site
        site_prod_mask = prod_df.loc[:, prod_col_dict["siteid"]] == site

        # Calculate and save  power/capacity
        prod_df.loc[site_prod_mask, output_name] = \
            prod_df.loc[site_prod_mask, power_name] / \
            meta_df.loc[site_meta_mask, dcsize_name].iloc[0]

    return prod_df


def prod_irradiance_filter(prod_df, prod_col_dict, meta_df, meta_col_dict,
                           drop=True, irradiance_type='ghi', csi_max=1.1
                           ):
    """Filter rows of production data frame according to performance and data quality.

    THIS METHOD IS CURRENTLY IN DEVELOPMENT.

    Parameters
    ----------
    prod_df : DataFrame
        A data frame corresponding to production data.

    prod_df_col_dict : dict of {str : str}
        A dictionary that contains the column names associated with the production data,
        which consist of at least:

        - **timestamp** (*string*), should be assigned to associated time-stamp
          column name in prod_df
        - **siteid** (*string*), should be assigned to site-ID column name in prod_df
        - **irradiance** (*string*), should be assigned to associated irradiance column name in prod_df
        - **clearsky_irr** (*string*), should be assigned to clearsky irradiance column name in prod_df

    meta_df : DataFrame
        A data frame corresponding to site metadata.
        At the least, the columns in meta_col_dict be present.

    meta_col_dict : dict of {str : str}
        A dictionary that contains the column names relevant for the meta-data

        - **siteid** (*string*), should be assigned to site-ID column name
        - **latitude** (*string*), should be assigned to column name corresponding to site's latitude
        - **longitude** (*string*), should be assigned to column name corresponding to site's longitude

    irradiance_type : str
        A string description of the irradiance_type which was passed in prod_df. 
        Options: `ghi`, `dni`, `dhi`.
        In future, `poa` may be a feature.

    csi_max: int
        A pvanalytics parameter of maximum ratio of measured to clearsky (clearsky index).

    Returns
    -------
    prod_df: DataFrame
        A dataframe with new **clearsky_irr** column. If drop=True, a filtered prod_df according to clearsky.
    clearsky_mask : series
        Returns True for each value where the clearsky index is less than or equal to csi_mask
    """

    prod_df = prod_df.copy()
    meta_df = meta_df.copy()

    irr_name = prod_col_dict["irradiance"]
    clearsky_irr_name = prod_col_dict["clearsky_irr"]

    individual_sites = set(meta_df[meta_col_dict['siteid']].tolist())

    for site in individual_sites:

        # Get site-specific meta data
        # site_meta_data= meta_df[meta_df[meta_col_dict['siteid']] == site]
        site_meta_mask = meta_df.loc[:, meta_col_dict["siteid"]] == site
        site_prod_mask = prod_df.loc[:, prod_col_dict["siteid"]] == site

        # Save times in object
        prod_times = prod_df.loc[site_prod_mask,
                                 prod_col_dict['timestamp']].tolist()

        # Extract site's position
        latitude = meta_df.loc[site_meta_mask, meta_col_dict['latitude']].tolist()[
            0]
        longitude = meta_df.loc[site_meta_mask, meta_col_dict['longitude']].tolist()[
            0]

        # Derive
        tf = TimezoneFinder()
        derived_timezone = tf.timezone_at(lng=longitude, lat=latitude)

        # Define Location object
        # Altitude is not passed because it's not available usually. Fortunately, a clearsky
        # model exists which does not use altitude.
        loc = pvlib.location.Location(latitude, longitude, tz=derived_timezone)
        times = pd.DatetimeIndex(
            data=prod_times,
            tz=loc.tz,
        )
        # Derive clearsky values
        cs = loc.get_clearsky(times, model='haurwitz')
        # Localize timestamps
        cs.index = cs.index.tz_localize(None)

        if irradiance_type == 'poa':

            raise ValueError(
                "POA is currently not configured because it requires `surface_tilt` and `surface_azimuth`, \
                a trait which is not usually in the meta data.")
            # Establish solarposition
            # solpos = pvlib.solarposition.get_solarposition(prod_times,
            #                                                latitude, longitude)

            # # Returns dataframe with columns:
            # # 'poa_global', 'poa_direct', 'poa_diffuse', 'poa_sky_diffuse', 'poa_ground_diffuse'
            # cs_POA_irradiance = pvlib.irradiance.get_total_irradiance(
            #     surface_tilt=20,
            #     surface_azimuth=180,
            #     dni=cs['dni'],
            #     ghi=cs['ghi'],
            #     dhi=cs['dhi'],
            #     solar_zenith=solpos['apparent_zenith'].tolist(),
            #     solar_azimuth=solpos['azimuth'])

            # df = pd.merge(df, POA_irradiance, how="inner", left_index=True, right_index=True)

        elif irradiance_type in ['dni', 'ghi', 'dhi']:
            prod_df[clearsky_irr_name] = cs[irradiance_type]

        else:
            raise ValueError(
                "Incorrect value passed to `irradiance_type`. Expected ['dni','ghi', or 'dhi']")

    mask_series = pvanalytics.quality.irradiance.clearsky_limits(
        prod_df[irr_name], prod_df[clearsky_irr_name], csi_max=csi_max)

    prod_df['mask'] = mask_series

    if not drop:
        return prod_df, mask_series

    if drop:
        prod_df = prod_df[prod_df['mask'] == False]
        prod_df.drop(columns=['mask'], inplace=True)
        return prod_df, mask_series


def prod_inverter_clipping_filter(prod_df, prod_col_dict, meta_df, meta_col_dict, model, **kwargs):
    """Filter rows of production data frame according to performance and data quality

    Parameters
    ----------
    prod_df : DataFrame
        A data frame corresponding to production data.
    prod_df_col_dict : dict of {str : str}
        A dictionary that contains the column names associated with the production data,
        which consist of at least:

        - **timestamp** (*string*), should be assigned to associated time-stamp
          column name in prod_df
        - **siteid** (*string*), should be assigned to site-ID column name in prod_df
        - **powerprod** (*string*), should be assigned to associated power production column name in prod_df

    meta_df : DataFrame
        A data frame corresponding to site metadata.
        At the least, the columns in meta_col_dict be present.
    meta_col_dict : dict of {str : str}
        A dictionary that contains the column names relevant for the meta-data

        - **siteid** (*string*), should be assigned to site-ID column name
        - **latitude** (*string*), should be assigned to column name corresponding to site's latitude
        - **longitude** (*string*), should be assigned to column name corresponding to site's longitude

    model : str
        A string distinguishing the inverter clipping detection model programmed in pvanalytics.
        Available options: ['geometric', 'threshold', 'levels']

    kwargs:
        Extra parameters passed to the relevant pvanalytics model. If none passed, defaults are used.

    Returns
    -------
    prod_df : DataFrame
        If drop=True, a filtered dataframe with clipping periods removed is returned.
    """

    prod_df = prod_df.copy()
    meta_df = meta_df.copy()

    individual_sites = set(meta_df[meta_col_dict['siteid']].tolist())

    for site in individual_sites:

        site_prod_mask = prod_df.loc[:, prod_col_dict["siteid"]] == site
        ac_power = prod_df.loc[site_prod_mask, prod_col_dict["powerprod"]]

        if len(ac_power) == 0:
            # If no rows exist for this company, skip it.
            continue

        if model == 'geometric':
            window = kwargs.get('window')
            slope_max = kwargs.get('slope_max') or 0.2
            freq = kwargs.get('freq')  # Optional
            tracking = kwargs.get('tracking') or False
            prod_df.loc[site_prod_mask, "mask"] = pvanalytics.features.clipping.geometric(
                ac_power, window=window, slope_max=slope_max, freq=freq, tracking=tracking)

        elif model == 'threshold':
            slope_max = kwargs.get('slope_max') or 0.0035
            power_min = kwargs.get('power_min') or 0.75
            power_quantile = kwargs.get('power_quantile') or 0.995
            freq = kwargs.get('freq')  # Optional
            prod_df.loc[site_prod_mask, "mask"] = pvanalytics.features.clipping.threshold(
                ac_power, slope_max=slope_max, power_min=power_min, power_quantile=power_quantile, freq=freq)

        elif model == 'levels':
            window = kwargs.get('window') or 4
            fraction_in_window = kwargs.get('fraction_in_window') or 0.75
            rtol = kwargs.get('rtol') or 0.005
            levels = kwargs.get('levels') or 2
            prod_df.loc[site_prod_mask, "mask"] = pvanalytics.features.clipping.levels(
                ac_power, window=window, fraction_in_window=fraction_in_window, rtol=rtol, levels=levels)

        else:
            raise ValueError(
                "Invalid value passed to parameter `calculation`. Expected a value in ['geometric', 'threshold', 'levels']")

    return prod_df


def identify_right_censored_data(om_df, col_dict):
    """
    Identify censored data for site-group pairs in a given DataFrame.

    This function processes a DataFrame containing failure events to identify 
    the first observed failure for each site-group pair and the last failure 
    for each site. It constructs a new DataFrame that includes both observed 
    and right-censored data, where unobserved site-group pairs are reported
    with the time of the last observed failure for that site.

    Parameters
    ----------
    om_df : pandas.DataFrame
        A DataFrame containing failure data with at least two columns 
        specified in `col_dict`: one for grouping and one for site.

    col_dict : dict
        A dictionary containing the following keys:
        - 'group_by': The column name to group by.
        - 'site': The column name representing the site.

    Returns
    -------
    pandas.DataFrame
        A DataFrame indexed by unique site-group pairs, containing the 
        first observed failure times and the last failure times, with 
        an additional column indicating whether the failure was observed 
        or censored.
    """
    # extract the columns we need
    group_by = col_dict['group_by']
    site = col_dict['site']

    # find the first failure of a given site-group_by pair
    first_fails_df = om_df.groupby([site, group_by]).first()
    first_fails_df['was_observed'] = True

    # find the last failure for a given site
    last_fails_df = om_df.groupby(site).last().drop(columns=[group_by])  # we don't care about the group_by value
    last_fails_df['was_observed'] = False

    # initialize dataframe with a row for every unique site-group_by pair
    unique_sites = om_df[site].unique()
    unique_group_bys = om_df[group_by].unique()
    all_sites_assets_df = pd.DataFrame(index=pd.MultiIndex.from_product([unique_sites, unique_group_bys], 
                                                                        names=[site, group_by]),
                                       columns=first_fails_df.columns,
                                       dtype=first_fails_df.dtypes.values)

    # prefill dataframe with the last possible times (the censored times)
    for unique_site in unique_sites:
        all_sites_assets_df.loc[(unique_site, slice(None)), :] = last_fails_df.loc[unique_site].values

    # for every row that did have a recorded event, replace the censored time with the observed one
    all_sites_assets_df.loc[first_fails_df.index] = first_fails_df

    # set the column dtypes appropriately
    return all_sites_assets_df.astype(first_fails_df.dtypes)