import os
import argparse
import pandas as pd
from pyqt_corrector.tablemodel import openDataset


def main(args):
    """main

    :args: command line arguments

    """
    df = openDataset(args.csv_file)
    df1 = df.query("tp_fp == 0")
    df2 = df1.query("gt_box != '0x0x0x0'")
    df3 = df2.sort_values(by=["page", "score"])
    df4 = df3.reset_index(drop=True)
    df5 = df4.drop(columns=["gt_box", "tp_fp"])
    for key, value in args.map_class:
        df5 = df5.replace(key, value)
    if args.output == "":
        print(df5)
    else:
        df5.to_csv(args.output, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filter predictions from csv file by removing true "
        "positives and false positive associated with an existing manually "
        "labeled symbols. If no output file is specified, print the results to"
        " the standard output.")
    parser.add_argument("csv_file", help="input csv file path", type=str)
    parser.add_argument(
        "-o", "--output", help="output file", default="", type=str)
    parser.add_argument(
        "-m", "--map_class",
        help="-m BEMOL flat: map BEMOL class name to flat class name",
        nargs=2, action="append")
    args = parser.parse_args()
    main(args)
