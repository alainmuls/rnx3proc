#!/usr/bin/env python

import sys
import os
import argparse
from termcolor import colored
import logging
import json
from datetime import datetime
from pathlib import Path
import pandas as pd
from shutil import copyfile

from gfzrnx import gfzrnx_constants as gfzc
from ampyutils import gnss_cmd_opts as gco

from ampyutils import am_config as amc
from ampyutils import amutils
from tle import tle_visibility, tleobs_plot
from ltx import ltx_obstab_reporting


__author__ = 'amuls'


def treatCmdOpts(argv):
    """
    Treats the command line options

    :param argv: the options
    :type argv: list of string
    """
    baseName = os.path.basename(__file__)
    amc.cBaseName = colored(baseName, 'yellow')

    helpTxt = amc.cBaseName + ' analyses observation tabular file for selected GNSSs'

    # create the parser for command line arguments
    parser = argparse.ArgumentParser(description=helpTxt)

    parser.add_argument('-o', '--obstab', help='observation tabular file', type=str, required=True)

    parser.add_argument('-f', '--freqs', help='select frequencies to use (out of {freqs:s}, default {freq:s})'.format(freqs='|'.join(gfzc.lst_freqs), freq=colored(gfzc.lst_freqs[0], 'green')), default=gfzc.lst_freqs[0], type=str, required=False, action=gco.freqtype_action, nargs='+')

    parser.add_argument('-i', '--interval', help='measurement interval in seconds (default {interv:s}s)'.format(interv=colored('1', 'green')), required=False, default=1., type=float, action=gco.interval_action)

    parser.add_argument('-c', '--cutoff', help='cutoff angle in degrees (default {mask:s})'.format(mask=colored('0', 'green')), default=0, type=int, required=False, action=gco.cutoff_action)

    parser.add_argument('-p', '--plot', help='displays interactive plots (default False)', action='store_true', required=False, default=False)

    parser.add_argument('-l', '--logging', help='specify logging level console/file (two of {choices:s}, default {choice:s})'.format(choices='|'.join(gco.lst_logging_choices), choice=colored(' '.join(gco.lst_logging_choices[3:5]), 'green')), nargs=2, required=False, default=gco.lst_logging_choices[3:5], action=gco.logging_action)

    # drop argv[0]
    args = parser.parse_args(argv[1:])

    # return arguments
    return args.obstab, args.freqs, args.interval, args.cutoff, args.plot, args.logging


def check_arguments(logger: logging.Logger = None):
    """
    check arhuments and change working directory
    """
    cFuncName = colored(os.path.basename(__file__), 'yellow') + ' - ' + colored(sys._getframe().f_code.co_name, 'green')

    # check & change working dir
    dTab['dir'] = os.path.dirname(Path(dTab['cli']['obstabf']).resolve())
    dTab['obstabf'] = os.path.basename(dTab['cli']['obstabf'])

    if not amutils.changeDir(dTab['dir']):
        if logger is not None:
            logger.error('{func:s}: changing to directory {dir:s} failed'.format(dir=dTab['dir'], func=cFuncName))
        sys.exit(amc.E_DIR_NOT_EXIST)

    # check accessibilty of observation statistics file
    if not amutils.file_exists(fname=dTab['obstabf'], logger=logger):
        if logger is not None:
            logger.error('{func:s}: observation file {file:s} not accessible'.format(file=dTab['obstabf'], func=cFuncName))
        sys.exit(amc.E_FILE_NOT_EXIST)

    # create dir for storing the latex sections
    dTab['ltx']['path'] = os.path.join(dTab['dir'], 'ltx')
    if not amutils.mkdir_p(dTab['ltx']['path']):
        if logger is not None:
            logger.error('{func:s}: cannot create directory {dir:s} failed'.format(dir=dTab['ltx']['path'], func=cFuncName))
        sys.exit(amc.E_FAILURE)

    # extract YY and DOY from filename
    dTab['time']['YYYY'] = int(dTab['obstabf'][12:16])
    dTab['time']['DOY'] = int(dTab['obstabf'][16:19])
    # converting to date
    dTab['time']['date'] = datetime.strptime('{year:04d}-{doy:03d}'.format(year=dTab['time']['YYYY'], doy=dTab['time']['DOY']), "%Y-%j")


def read_obstab(logger: logging.Logger = None) -> pd.DataFrame:
    """
    read_obstab reads the SNR for the selected frequencies into a dataframe
    """
    cFuncName = colored(os.path.basename(__file__), 'yellow') + ' - ' + colored(sys._getframe().f_code.co_name, 'green')

    dfTmp = pd.read_csv(dTab['obstabf'], delimiter=',')

    if logger is not None:
        amutils.logHeadTailDataFrame(df=dfTmp, dfName='dfTmp', callerName=cFuncName, logger=logger)

    # select the SNR colmuns for the selected frequencies
    # col_names = dfTmp.columns.tolist()
    # print(col_names)
    # cols2keep = col_names[:4]
    # for freq in dTab['cli']['freqs']:
    #     cols2keep += [col for col in col_names[4:] if col.startswith('S{freq:s}'.format(freq=freq))]

    # return dfTmp[cols2keep]


def obstab_analyse(argv):
    """
    obstab_analyse analyses the created OBSTAB files and compares with TLE data
    """

    cFuncName = colored(os.path.basename(__file__), 'yellow') + ' - ' + colored(sys._getframe().f_code.co_name, 'green')

    global dTab
    dTab = {}
    dTab['cli'] = {}
    dTab['time'] = {}
    dTab['ltx'] = {}
    dTab['plots'] = {}

    dTab['cli']['obstabf'], dTab['cli']['freqs'], dTab['time']['interval'], dTab['cli']['mask'], show_plot, logLevels = treatCmdOpts(argv)

    # create logging for better debugging
    logger, log_name = amc.createLoggers(baseName=os.path.basename(__file__), logLevels=logLevels)

    # verify input
    check_arguments(logger=logger)

    # read obsstat into a dataframe and select the SNR for the selected frequencies
    dfObsTab = read_obstab(logger=logger)
    amutils.logHeadTailDataFrame(df=dfObsTab, dfName='dfObsTab', callerName=cFuncName, logger=logger)


    # report to the user
    logger.info('{func:s}: Project information =\n{json!s}'.format(func=cFuncName, json=json.dumps(dTab, sort_keys=False, indent=4, default=amutils.json_convertor)))

    # store the json structure
    jsonName = os.path.join(dTab['dir'], '{scrname:s}.json'.format(scrname=os.path.splitext(os.path.basename(__file__))[0]))
    with open(jsonName, 'w+') as f:
        json.dump(dTab, f, ensure_ascii=False, indent=4, default=amutils.json_convertor)

    # clean up
    copyfile(log_name, os.path.join(dTab['dir'], '{scrname:s}.log'.format(scrname=os.path.basename(__file__).replace('.', '_'))))
    os.remove(log_name)


if __name__ == "__main__":  # Only run if this file is called directly
    obstab_analyse(sys.argv)
