from scipy import stats
from sksurv.nonparametric import kaplan_meier_estimator

def fit_survival_function(df, col_dict, method):
    """
    Calculate the survival function for different groups in a DataFrame using specified methods.

    This function computes the survival function for each unique group in the input DataFrame 
    based on the specified method. It supports the Kaplan-Meier estimator and Weibull distribution 
    fitting for survival analysis. The Kaplan-Meier estimator is a non-parametric statistic,
    while the Weibull distribution is a parametric model.

    Parameters
    ----------
    df : pandas.DataFrame
        A DataFrame containing failure data with at least three columns specified in `col_dict`:
        one for grouping, one for the time to failure, and one indicating whether the failure was observed

    col_dict : dict of {str : str}
        A dictionary that contains the column names relevant for survival analysis

        - **group_by** (*string*), should be assigned to the column to group by
        - **time_to_fail** (*string*), should be assigned to the column containing the time until failure
        - **was_observed** (*string*), should be assigned to the column indicating whether the failure was observed

    method : str
        The method to use for calculating the survival function. Must be one of:

        - 'kaplan-meier': Uses the Kaplan-Meier estimator for survival analysis.
        - 'weibull': Fits a Weibull distribution to the data.

    Returns
    -------
    dict

        - If `method` is `'kaplan-meier'`, contains keys `'times'`, `'fail_prob'`, and `'conf_int'`, which denote the times, failure probabilities, and confidence intervals on the failure probabilities.
        - If `method` is `'weibull'`, contains keys `'shape'`, `'scale'`, and `'distribution'`, which denote the shape parameter, scale parameter, and corresponding fitted `stats.weibull_min` distribution.
    """

    implemented_methods = ['kaplan-meier', 'weibull']
    if method not in implemented_methods:
        raise ValueError(f'method argument must be one of {implemented_methods}, got {method}')

    df = df.reset_index()

    group_by = col_dict['group_by']
    time_to_fail = col_dict['time_to_fail']
    was_observed = col_dict['was_observed']

    results = {}

    unique_group_by = df[group_by].unique()
    for group in unique_group_by:
        group_df = df[df[group_by] == group]

        if method == 'kaplan-meier':
            km_result = kaplan_meier_estimator(group_df[was_observed], group_df[time_to_fail], conf_type='log-log')
            group_result = {'times': km_result[0], 'fail_prob': km_result[1], 'conf_int': km_result[2]}

        elif method == 'weibull':
            uncensored_times = group_df[group_df[was_observed]][time_to_fail]
            censored_times = group_df[~group_df[was_observed]][time_to_fail]
            data = stats.CensoredData(uncensored=uncensored_times, right=censored_times)
            shape, _, scale = stats.weibull_min.fit(data, floc=0)
            group_result = {'shape': shape, 'scale': scale, 'distribution': stats.weibull_min(c=shape, scale=scale)}

        results[group] = group_result

    return results