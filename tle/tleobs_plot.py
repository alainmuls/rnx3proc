import os
import sys
from termcolor import colored
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from matplotlib import dates
from typing import Tuple
from matplotlib.ticker import MultipleLocator

from ampyutils import amutils
from plot import plot_utils
from gfzrnx import gfzrnx_constants as gco

__author__ = 'amuls'


def tle_plot_arcs(marker: str, obsstatf: str, lst_PRNs: list, dfTabObs: pd.DataFrame, dfTle: pd.DataFrame, dTime: dict, show_plot: bool = False, logger: logging.Logger = None):
    """
    tle_plot_arcs plots the arcs caclculated by TLE for the GNSS
    """
    cFuncName = colored(os.path.basename(__file__), 'yellow') + ' - ' + colored(sys._getframe().f_code.co_name, 'green')

    # set up the plot
    plt.style.use('ggplot')

    # find minimum time for tle_rise and maximum time for tle_set columns
    dt_rise = []
    dt_set = []
    for j, (t_rise, t_set) in enumerate(zip(dfTle.tle_rise, dfTle.tle_set)):
        if len(t_rise) > 0:
            dt_rise.append(t_rise[0])
        if len(t_set) > 0:
            dt_set.append(t_set[-1])

    dt_min = min(dt_rise)
    dt_max = max(dt_set)

    if logger is not None:
        logger.info('{func:s}: TLE time span {start:s} -> {end:s}'.format(start=dt_min.strftime('%H:%M:%S'), end=dt_max.strftime('%H:%M:%S'), func=cFuncName))

    gnss_id = dfTle.index.to_list()[0][0]
    y_prns = [int(prn[1:]) + 1 for prn in dfTle.index.to_list()]

    fig, ax = plt.subplots(figsize=(8, 6))

    # create colormap with nrcolors discrete colors
    prn_colors, title_font = amutils.create_colormap_font(nrcolors=len(y_prns), font_size=12)

    # get the date of this observation to combine with rise and set times
    cur_date = dTime['date'].date()

    for y_prn, prn_color, (prn, tle_prn) in zip(y_prns, prn_colors, dfTle.iterrows()):
        for tle_rise, tle_set in zip(tle_prn.tle_rise, tle_prn.tle_set):
            ax.plot_date(y=[y_prn, y_prn], x=[datetime.combine(cur_date, tle_rise), datetime.combine(cur_date, tle_set)], linewidth=2, color=prn_color, linestyle='-', markersize=6, marker='|')
        for _, tle_cul in enumerate(tle_prn.tle_cul):
            if tle_cul is not np.NaN:
                ax.plot_date(y=y_prn, x=datetime.combine(cur_date, tle_cul), color=prn_color, markersize=6, marker='v')

    # beautify plot
    ax.xaxis.grid(b=True, which='major')
    ax.yaxis.grid(b=True, which='major')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), fancybox=True, shadow=True, ncol=6, markerscale=4)

    # ax.set_xlabel('PRN', fontdict=title_font)
    ax.set_ylabel('PRNs', fontdict=title_font)
    ax.set_xlabel('TLE arcs', fontdict=title_font)

    # plot title
    plt.title('TLE arcs: {marker:s}, {gnss:s}, {date!s} ({yy:04d}/{doy:03d})'.format(marker=marker, gnss=gco.dict_GNSSs[gnss_id], yy=dTime['YYYY'], doy=dTime['DOY'], date=dTime['date'].strftime('%d/%m/%Y')))

    # setticks on Y axis to represent the PRNs
    ax.yaxis.set_ticks(np.arange(1, y_prns[-1] + 1))
    tick_labels = []
    for i in np.arange(0, y_prns[-1]):
        tick_prn = '{gnss:s}{prn:02d}'.format(gnss=gnss_id, prn=i)
        if tick_prn in dfTle.index.to_list():
            tick_labels.append(tick_prn)
        else:
            tick_labels.append('')

    ax.set_yticklabels(tick_labels)

    # create the ticks for the time ax
    ax.set_xlim([datetime.combine(cur_date, dt_min), datetime.combine(cur_date, dt_max)])
    dtFormat = plot_utils.determine_datetime_ticks(startDT=datetime.combine(cur_date, dt_min), endDT=datetime.combine(cur_date, dt_max))

    if dtFormat['minutes']:
        # ax.xaxis.set_major_locator(dates.MinuteLocator(byminute=range(10, 60, 10), interval=1))
        pass
    else:
        ax.xaxis.set_major_locator(dates.HourLocator(interval=dtFormat['hourInterval']))   # every 4 hours
    ax.xaxis.set_major_formatter(dates.DateFormatter('%H:%M'))  # hours and minutes

    ax.xaxis.set_minor_locator(dates.DayLocator(interval=1))    # every day
    ax.xaxis.set_minor_formatter(dates.DateFormatter('\n%d-%m-%Y'))

    ax.xaxis.set_tick_params(rotation=0)
    for tick in ax.xaxis.get_major_ticks():
        # tick.tick1line.set_markersize(0)
        # tick.tick2line.set_markersize(0)
        tick.label1.set_horizontalalignment('center')
    fig.tight_layout()

    if show_plot:
        plt.show(block=True)
    else:
        plt.close(fig)

    # save the plot in subdir png of GNSSSystem
    amutils.mkdir_p('png')
    for ext in ['pdf', 'png', 'eps']:
        plt_name = os.path.join('png', '{basen:s}-TLEarcs.{ext:s}'.format(basen=obsstatf.split('.')[0], ext=ext))
        fig.savefig(plt_name, dpi=150, bbox_inches='tight', format=ext)
        logger.info('{func:s}: created plot {plot:s}'.format(func=cFuncName, plot=colored(plt_name, 'green')))



def obstle_plot_obscount(marker: str, obsstatf: str, dfObsTle: pd.DataFrame, dTime: dict, reduce2percentage: bool = False, show_plot: bool = False, logger: logging.Logger = None) -> str:
    """
    obstle_plot_arcs plots count of observations wrt to number obtained from TLE
    """
    cFuncName = colored(os.path.basename(__file__), 'yellow') + ' - ' + colored(sys._getframe().f_code.co_name, 'green')

    # set up the plot
    plt.style.use('ggplot')

    fig, ax = plt.subplots(figsize=(8, 6))

    gnss_id = dfObsTle.PRN.iloc[0][0]
    y_prns = [int(prn[1:]) for prn in dfObsTle.PRN.to_list()]

    # select the columns used for plotting
    col_names = dfObsTle.columns.tolist()
    obstypes = [x for x in col_names[col_names.index('PRN') + 1:]]

    # determine widths of bars to use for each PRN
    dy_obstypes, bar_width = bars_info(nr_arcs=len(obstypes), logger=logger)

    # create colormap with nrcolors discrete colors
    bar_colors, title_font = amutils.create_colormap_font(nrcolors=len(obstypes), font_size=12)

    # plot the TLE observation count
    for i, (y_prn, prn) in enumerate(zip(y_prns, dfObsTle.PRN)):
        for j, (obst, dy_obst, bar_color) in enumerate(zip(list(reversed(obstypes)), list(reversed(dy_obstypes)), list(reversed(bar_colors)))):
            prn_width = dfObsTle.iloc[i][obst]
            if not reduce2percentage:
                if i == 0:
                    ax.barh(y=y_prn + dy_obst, width=prn_width, height=bar_width, color=bar_color, label=obst)
                else:
                    ax.barh(y=y_prn + dy_obst, width=prn_width, height=bar_width, color=bar_color)
            else:
                if j == 0:
                    tle_width = prn_width / 100
                if tle_width != 0:
                    if i == 0:
                        ax.barh(y=y_prn + dy_obst, width=prn_width / tle_width, height=bar_width, color=bar_color, label=obst)
                    else:
                        ax.barh(y=y_prn + dy_obst, width=prn_width / tle_width, height=bar_width, color=bar_color)

    # beautify plot
    ax.xaxis.grid(b=True, which='major')
    ax.yaxis.grid(b=False)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), fancybox=True, shadow=True, ncol=6, markerscale=4)

    # ax.set_xlabel('PRN', fontdict=title_font)
    ax.set_ylabel('PRNs', fontdict=title_font)
    if not reduce2percentage:
        ax.set_xlabel('Observations Count [-]', fontdict=title_font)
    else:
        ax.set_xlabel('Observations Count [%]', fontdict=title_font)

    # plot title
    plt.title('Observations vs TLE: {marker:s}, {gnss:s}, {date!s} ({yy:04d}/{doy:03d})'.format(marker=marker, gnss=gco.dict_GNSSs[gnss_id], yy=dTime['YYYY'], doy=dTime['DOY'], date=dTime['date'].strftime('%d/%m/%Y')))

    # setticks on Y axis to represent the PRNs
    _, xlim_right = ax.get_xlim()
    ylim_left, ylim_right = ax.get_ylim()
    print('{} | {} => {}'.format(int(xlim_right), int(ylim_left), int(ylim_right)))
    for i in np.arange(int(ylim_left), int(ylim_right)):
        if i % 2 == 0:
            if not reduce2percentage:
                ax.barh(y=i, height=0.95, width=xlim_right, color='black', alpha=0.1)
            else:
                ax.barh(y=i, height=0.95, width=100, color='black', alpha=0.1)

    ax.yaxis.set_ticks(np.arange(1, y_prns[-1] + 1))
    tick_labels = []
    for i in np.arange(1, y_prns[-1] + 1):
        tick_prn = '{gnss:s}{prn:02d}'.format(gnss=gnss_id, prn=i)
        if tick_prn in dfObsTle.PRN.to_list():
            tick_labels.append(tick_prn)
        else:
            tick_labels.append('')

    ax.set_yticklabels(tick_labels)
    fig.tight_layout()

    if show_plot:
        plt.show(block=True)
    else:
        plt.close(fig)
    amutils.mkdir_p('png')

    # save the plot in subdir png of GNSSSystem
    for ext in ['pdf', 'png', 'eps']:
        if not reduce2percentage:
            plt_name = os.path.join('png', '{basen:s}-ObsTLE.{ext:s}'.format(basen=obsstatf.split('.')[0], ext=ext))
        else:
            plt_name = os.path.join('png', '{basen:s}-ObsTLEperc.{ext:s}'.format(basen=obsstatf.split('.')[0], ext=ext))
        fig.savefig(plt_name, dpi=150, bbox_inches='tight', format=ext)
        logger.info('{func:s}: created plot {plot:s}'.format(func=cFuncName, plot=colored(plt_name, 'green')))

    return plt_name


def bars_info(nr_arcs: int, logger: logging.Logger) -> Tuple[list, int]:
    """
    bars_info determines the width of an individual bar, the spaces between the arc bars, and localtion in delta-x-coordinates of beginning of each PRN arcs
    """
    cFuncName = colored(os.path.basename(__file__), 'yellow') + ' - ' + colored(sys._getframe().f_code.co_name, 'green')
    logger.info('{func:s}: determining the information for the bars'.format(func=cFuncName))

    # the bars for all arcs for 1 PRN may span over 0.8 units (from [-0.4 => 0.4]), including the spaces between the different arcs
    width_prn_arcs = 0.8
    dx_start = -0.4  # start of the bars relative to integer of PRN
    width_space = 0.02  # space between the different arcs for 1 PRN

    # substract width-spaces needed for nr_arcs
    width_arcs = width_prn_arcs - (nr_arcs - 1) * width_space

    # the width taken by 1 arc for 1 prn is
    width_arc = width_arcs / nr_arcs

    # get the delta-x to apply to the integer value that corresponds to a PRN
    dx_obs = [dx_start + i * (width_space + width_arc) for i in np.arange(nr_arcs)]

    return dx_obs, width_arc


def obstle_plot_relative(marker: str, obsstatf: str, dfObsTle: pd.DataFrame, dTime: dict, show_plot: bool = False, logger: logging.Logger = None) -> str:
    """
    obstle_plot_relativeobsstatf plots the percenatge of observations observed wrt the TLE determined max values.
    """
    cFuncName = colored(os.path.basename(__file__), 'yellow') + ' - ' + colored(sys._getframe().f_code.co_name, 'green')

    # set up the plot
    plt.style.use('ggplot')

    fig, ax = plt.subplots(figsize=(8, 6))

    gnss_id = dfObsTle.PRN.iloc[0][0]
    x_prns = [int(prn[1:]) for prn in dfObsTle.PRN.to_list()]
    x_crds = np.arange(1, 38)

    # select the columns used for plotting
    col_names = dfObsTle.columns.tolist()
    obstypes = [x for x in col_names[col_names.index('PRN') + 1:]]

    # create colormap with nrcolors discrete colors
    colors, title_font = amutils.create_colormap_font(nrcolors=len(obstypes[:-1]), font_size=12)
    # used markers
    lst_markers = ['o', 'v', '^', '<', '>', 'x', '+', 's', 'd', '.', ',']

    # create an offset to plot the markers per PRN
    dx_obs, dx_skip = bars_info(nr_arcs=len(obstypes) - 1, logger=logger)
    # print('dx_obs = {}'.format(dx_obs))
    # print('len(dx_obs) = {}'.format(len(dx_obs)))
    # print('dx_skip = {}'.format(dx_skip))

    # store the percantages in a dict
    for j, (obst, color, plotmarker) in enumerate(zip(list(reversed(obstypes[:-1])), list(reversed(colors)), lst_markers)):
        obs_percentages = [np.NaN] * 37
        for i, (x_prn, prn) in enumerate(zip(x_prns, dfObsTle.PRN)):
            tle_maxobs = dfObsTle.iloc[i][obstypes[-1]] / 100
            if tle_maxobs != 0:
                obs_perc = dfObsTle.iloc[i][obst] / tle_maxobs
                obs_percentages[x_prn] = obs_perc

            # plot the current percentages per PRN and per OBST
            if i == 0:
                ax.plot(x_prn + dx_obs[j] + dx_skip / len(dx_obs), obs_perc, marker=plotmarker, color=color, label=obst, linestyle='', markersize=3)
            else:
                ax.plot(x_prn + dx_obs[j] + dx_skip / len(dx_obs), obs_perc, marker=plotmarker, color=color, linestyle='', markersize=3)

    # beautify plot
    ax.xaxis.grid(b=False)
    ax.yaxis.grid(b=True, which='both')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1), fancybox=True, shadow=True, ncol=6, markerscale=3)

    ax.yaxis.grid(True)
    ax.yaxis.set_minor_locator(MultipleLocator(5))
    ax.yaxis.grid(which="minor", color='black', linestyle='-.', linewidth=5)

    # ax.set_xlabel('PRN', fontdict=title_font)
    ax.set_xlabel('PRNs', fontdict=title_font)
    ax.set_ylabel('Observations relative to TLE [-]', fontdict=title_font)

    # plot title
    plt.title('Relative Observations: {marker:s}, {gnss:s}, {date!s} ({yy:04d}/{doy:03d})'.format(marker=marker, gnss=gco.dict_GNSSs[gnss_id], yy=dTime['YYYY'], doy=dTime['DOY'], date=dTime['date'].strftime('%d/%m/%Y')))

    # set limits for y-axis
    # ax.set_ylim([70, 101])

    # setticks on X axis to represent the PRNs
    ax.xaxis.set_ticks(np.arange(0, x_crds[-1]))
    tick_labels = []
    for i in np.arange(0, x_crds[-1]):
        # create a grey bar for separating between PRNs
        if i % 2 == 0:
            ax.bar(i, 100, width=0.95, color='black', alpha=0.05)

        tick_prn = '{gnss:s}{prn:02d}'.format(gnss=gnss_id, prn=i)
        if tick_prn in dfObsTle.PRN.to_list():
            tick_labels.append(tick_prn)
        else:
            tick_labels.append('')

    ax.set_xticklabels(tick_labels, rotation=90, horizontalalignment='center')
    fig.tight_layout()

    if show_plot:
        plt.show(block=True)
    else:
        plt.close(fig)

    # save the plot in subdir png of GNSSSystem
    amutils.mkdir_p('png')
    for ext in ['pdf', 'png', 'eps']:
        plt_name = os.path.join('png', '{basen:s}-PERC.{ext:s}'.format(basen=obsstatf.split('.')[0], ext=ext))
        fig.savefig(plt_name, dpi=150, bbox_inches='tight', format=ext)
        logger.info('{func:s}: created plot {plot:s}'.format(func=cFuncName, plot=colored(plt_name, 'green')))

    return plt_name


def obstle_plot_prns(marker: str, obsstatf: str, lst_PRNs: list, dfTabObs: pd.DataFrame, dfTle: pd.DataFrame, dTime: dict, show_plot: bool = False, logger: logging.Logger = None):
    """
    tle_plot_arcs plots the arcs caclculated by TLE for the GNSS
    """
    cFuncName = colored(os.path.basename(__file__), 'yellow') + ' - ' + colored(sys._getframe().f_code.co_name, 'green')

    # set up the plot
    plt.style.use('ggplot')

    # find minimum time for tle_rise and maximum time for tle_set columns
    dt_rise = []
    dt_set = []
    for j, (t_rise, t_set) in enumerate(zip(dfTle.tle_rise, dfTle.tle_set)):
        if len(t_rise) > 0:
            dt_rise.append(t_rise[0])
        if len(t_set) > 0:
            dt_set.append(t_set[-1])

    dt_min = min(dt_rise)
    dt_max = max(dt_set)

    # get min and max times according the observation smade
    amutils.logHeadTailDataFrame(df=dfTabObs, dfName='dfTabObs', callerName=cFuncName, logger=logger)
    amutils.logHeadTailDataFrame(df=dfTle, dfName='dfTle', callerName=cFuncName, logger=logger)

    # XXXXXXXXXXXXXXXXXXXXXXXXXXxx
    # PLOT PRN ARCS FROM OBSERVED AND TLE
    sys.exit(88)


def plot_prnfreq(obsstatf: str, dfPrnObst: pd.DataFrame, idx_gaps_time: list, idx_snr_jumps: list,  snrth: float, dTime: dict, show_plot: bool = False, logger: logging.Logger = None):
    """
    plot_prnfreq plots for a given PRN the observation OBST on a frequency with the exponential moving average
    """
    cFuncName = colored(os.path.basename(__file__), 'yellow') + ' - ' + colored(sys._getframe().f_code.co_name, 'green')

    amutils.logHeadTailDataFrame(df=dfPrnObst, dfName='dfPrnObst', callerName=cFuncName, logger=logger)

    # find the indices positional index where the 'dt' column differs from the interval (cfr odx_gaps_time)
    pos_idx_gaps = []
    pos_idx_nextgaps = []
    # idx_gaps_time = dfPrnObst.index[dfPrnObst['dt'] != 1].tolist()
    for idx_gap in idx_gaps_time[1:]:
        pos_idx_gaps.append(dfPrnObst.index.get_loc(idx_gap))
        pos_idx_nextgaps.append(dfPrnObst.index.get_loc(idx_gap) + 1)  # indicates position of next
    print('idx_gaps_time = {} #{}'.format(idx_gaps_time, len(idx_gaps_time)))
    # print('idx_gaps[1:] = {} #{}'.format(idx_gaps[1:], len(idx_gaps[1:])))
    # print('idx_gaps[:-1] = {} #{}'.format(idx_gaps[:-1], len(idx_gaps[:-1])))
    # print('pos_idx_gaps = {}'.format(pos_idx_gaps))
    # print('pos_idx_nextgaps = {}'.format(pos_idx_nextgaps))

    # create colormap with nrcolors discrete colors
    # obstypes = [obst for obst in dfPrnObst.columns if obst not in ['DATE_TIME', 'PRN', 'dt', 'dS1C', 'EMA10', 'WMA10']]
    # print(obstypes)
    obstypes = [obst for obst in dfPrnObst.columns if obst not in ['DATE_TIME', 'PRN', 'dt'] and obst[0] != 'd']
    print(obstypes)

    # used markers
    lst_markers = ['o', 'x', '+', '.', ',', 'v', '^', '<', '>', 's', 'd']
    lst_colors, title_font = amutils.create_colormap_font(nrcolors=len(obstypes), font_size=12)

    # plot on ax1 the curves, use ax2 for the difference with previous value
    for obst, plot_marker, color in zip(obstypes, lst_markers[:len(obstypes)], lst_colors):
        if obst[0] == 'S':  # more detailled plot for SNR analysis
            fig = plt.figure(figsize=(10, 7))
            gs = fig.add_gridspec(nrows=2, hspace=0.1, height_ratios=[4, 1])
            ax1, ax2 = gs.subplots(sharex=True)
            # fig, (ax1, ax2) = plt.subplots(2, sharex=True, figsize=(8, 6), )
        else:
            fig, ax1 = plt.subplots(figsize=(8, 6))

        # go over the time intervals
        for i, (pos_idx_start, pos_idx_stop) in enumerate(zip(pos_idx_gaps[:-1], pos_idx_gaps[1:])):
            # print('{} => {}'.format(pos_idx_start, pos_idx_stop))
            # print(dfPrnObst.iloc[pos_idx_start:pos_idx_stop]['DATE_TIME'])
            # print(dfPrnObst.iloc[pos_idx_start:pos_idx_stop][obst])
            # print(dfPrnObst.iloc[pos_idx_start:pos_idx_stop]['DATE_TIME'].shape)
            # print(dfPrnObst.iloc[pos_idx_start:pos_idx_stop][obst].shape)
            dfTimeSegment = dfPrnObst.iloc[pos_idx_start:pos_idx_stop]
            if i == 0:
                ax1.plot(dfTimeSegment['DATE_TIME'],
                         dfTimeSegment[obst],
                         label=obst, linestyle='-', marker=plot_marker, markersize=2, color=color)

                if obst[0] == 'S':
                    ax2.fill_between(dfTimeSegment['DATE_TIME'], -snrth, +snrth, color='black', alpha=0.20, linestyle='-')
                    ax2.plot(dfTimeSegment['DATE_TIME'],
                             dfTimeSegment['d{obst:s}'.format(obst=obst)],
                             label='d{obst:s}'.format(obst=obst), linestyle='-', marker=plot_marker, markersize=2, color=color)

                # print a bar representing increase / decrease in SNR for a PRN / SNR pair
                # if obst[0] == 'S':
                #     # plot values in this segment where dSNR > snrth in green
                #     ax3.plot(dfTimeSegment[dfTimeSegment['d{obst:s}'.format(obst=obst)] > snrth]['DATE_TIME'], dfTimeSegment[dfTimeSegment['d{obst:s}'.format(obst=obst)] > snrth]['dS1C'], color='green', linestyle='', marker='^', markersize=5)
                #     ax3.plot(dfTimeSegment[dfTimeSegment['d{obst:s}'.format(obst=obst)] > snrth]['DATE_TIME'], dfTimeSegment[dfTimeSegment['d{obst:s}'.format(obst=obst)] > snrth]['dS1C'], color='red', linestyle='', marker='v', markersize=5)

            else:
                ax1.plot(dfTimeSegment['DATE_TIME'],
                         dfTimeSegment[obst],
                         linestyle='-', marker=plot_marker, markersize=2, color=color)

                if obst[0] == 'S':
                    ax2.fill_between(dfTimeSegment['DATE_TIME'], -snrth, +snrth, color='black', alpha=0.20, linestyle='-')
                    ax2.plot(dfTimeSegment['DATE_TIME'],
                             dfTimeSegment['d{obst:s}'.format(obst=obst)],
                             linestyle='-', marker=plot_marker, markersize=2, color=color)

    ax1.legend(loc='best', fancybox=True, shadow=True, ncol=6, markerscale=3)
    if obst[0] == 'S':
        ax2.legend(loc='best', fancybox=True, shadow=True, ncol=6, markerscale=3)

    fig.tight_layout()

    if show_plot:
        plt.show(block=True)
    else:
        plt.close(fig)
