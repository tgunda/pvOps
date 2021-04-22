# A set of preprocessing methods, both based on photovoltaic-specific physics and data quality methods.

import pvlib
import pvanalytics
from timezonefinder import TimezoneFinder


def prod_irradiance_filter(prod_df, prod_col_dict, meta_df, meta_col_dict,
                           drop=True, irradiance_type='ghi', csi_max=1.1
                           ):
    """
    Filter rows of production data frame according to performance and data quality

    Parameters

    ----------
    prod_df: DataFrame
        A data frame corresponding to production data.

    prod_df_col_dict: dict of {str : str}
        A dictionary that contains the column names associated with the production data,
        which consist of at least:

        - **timestamp** (*string*), should be assigned to associated time-stamp
        column name in prod_df
        - **siteid** (*string*), should be assigned to site-ID column name in prod_df
        - **irradiance** (*string*), should be assigned to associated irradiance column name in prod_df
        - **clearsky_irr** (*string*), should be assigned to clearsky irradiance column name in prod_df

    meta_df: DataFrame
        A data frame corresponding to site metadata.
        At the least, the columns in meta_col_dict be present.

    meta_col_dict: dict of {str : str}
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
        prod_times = prod_df.loc[site_prod_mask, prod_col_dict['timestamp']].tolist()

        # Extract site's position
        latitude, longitude = meta_df[meta_col_dict['latitude']
                                      ], meta_df[meta_col_dict['longitude']]
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
                "POA is currently not configured because it requires `surface_tilt` and `surface_azimuth`, a trait which is not usually in the meta data.")
            # Establish solarposition
            solpos = pvlib.solarposition.get_solarposition(prod_times,
                                                           latitude, longitude)

            # Returns dataframe with columns:
            # 'poa_global', 'poa_direct', 'poa_diffuse', 'poa_sky_diffuse', 'poa_ground_diffuse'
            cs_POA_irradiance = pvlib.irradiance.get_total_irradiance(
                surface_tilt=20,
                surface_azimuth=180,
                dni=cs['dni'],
                ghi=cs['ghi'],
                dhi=cs['dhi'],
                solar_zenith=solpos['apparent_zenith'].tolist(),
                solar_azimuth=solpos['azimuth'])

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
    """
    Filter rows of production data frame according to performance and data quality

    Parameters

    ----------
    prod_df: DataFrame
        A data frame corresponding to production data.

    prod_df_col_dict: dict of {str : str}
        A dictionary that contains the column names associated with the production data,
        which consist of at least:

        - **timestamp** (*string*), should be assigned to associated time-stamp
        column name in prod_df
        - **siteid** (*string*), should be assigned to site-ID column name in prod_df
        - **energyprod** (*string*), should be assigned to associated production column name in prod_df

    meta_df: DataFrame
        A data frame corresponding to site metadata.
        At the least, the columns in meta_col_dict be present.

    meta_col_dict: dict of {str : str}
        A dictionary that contains the column names relevant for the meta-data

        - **siteid** (*string*), should be assigned to site-ID column name
        - **latitude** (*string*), should be assigned to column name corresponding to site's latitude
        - **longitude** (*string*), should be assigned to column name corresponding to site's longitude

    model: str
        A string distinguishing the inverter clipping detection model programmed in pvanalytics. Available options: ['geometric', 'threshold', 'levels']

    kwargs:
        Extra parameters passed to the relevant pvanalytics model. If none passed, defaults are used.

    Returns

    -------
    prod_df: DataFrame
        If drop=True, a filtered dataframe with clipping periods removed is returned.
    """

    prod_df = prod_df.copy()
    meta_df = meta_df.copy()

    individual_sites = set(meta_df[meta_col_dict['siteid']].tolist())

    for site in individual_sites:

        # ac_power = prod_df[prod_col_dict["energyprod"]]
        site_prod_mask = prod_df.loc[:, prod_col_dict["siteid"]] == site

        ac_power = prod_df.loc[site_prod_mask, prod_col_dict["energyprod"]]

        if model == 'geometric':
            window = kwargs.get('window')
            slope_max = kwargs.get('slope_max') or 0.2
            freq = kwargs.get('freq')
            tracking = kwargs.get('tracking') or False
            prod_df.loc[site_prod_mask, "mask"] = pvanalytics.features.clipping.geometric(
                ac_power, window=window, slope_max=slope_max, freq=freq, tracking=tracking)

        elif model == 'threshold':
            slope_max = kwargs.get('slope_max') or 0.0035
            power_min = kwargs.get('power_min') or 0.75
            power_quantile = kwargs.get('power_quantile') or 0.995
            prod_df.loc[site_prod_mask, "mask"] = pvanalytics.features.clipping.threshold(
                ac_power, slope_max=slope_max, power_min=power_min, power_quantile=power_quantile, freq=None)

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
