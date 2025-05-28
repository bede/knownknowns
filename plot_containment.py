#!/usr/bin/env python3

import argparse
import os
import shutil
import sys

import altair as alt
import pandas as pd


def main():
    parser = argparse.ArgumentParser(
        description="Create containment visualization from sourmash search results"
    )
    parser.add_argument("input_csv", help="Input CSV file from sourmash search")
    parser.add_argument(
        "--output-plot", default="containment_plot.png", help="Output plot filename"
    )
    parser.add_argument(
        "--output-csv", default="containment.csv", help="Output CSV filename"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    # Debug: Check file contents
    if args.debug:
        print(f"CSV file size: {os.path.getsize(args.input_csv)} bytes")
        print("CSV file contents:")
        with open(args.input_csv) as f:
            content = f.read()
            print(repr(content))

    if args.input_csv != args.output_csv:
        shutil.copy(args.input_csv, args.output_csv)

    try:
        if os.path.getsize(args.input_csv) == 0:
            print("ERROR: CSV file is empty")
            # Create a dummy PNG file
            with open(args.output_plot, "w") as f:
                f.write("No data to visualize - CSV file is empty")
            return

        df = pd.read_csv(args.input_csv)

        if args.debug:
            print(f"CSV columns: {list(df.columns)}")
            print(f"CSV shape: {df.shape}")
            print("First few rows:")
            print(df.head())

        if df.empty:
            print("No containment results found")
            # Create a dummy PNG file
            with open(args.output_plot, "w") as f:
                f.write("No matches found")
            return

        # PNG export
        alt.data_transformers.enable("json")

        # Check required columns exist
        required_cols = ["name", "similarity"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"ERROR: Missing required columns: {missing_cols}")
            print(f"Available columns: {list(df.columns)}")
            # Create error PNG
            with open(args.output_plot, "w") as f:
                f.write(f"Missing columns: {missing_cols}")
            return

        # Create the Altair chart
        chart = (
            alt.Chart(df)
            .mark_bar(size=8)
            .encode(
                y=alt.Y("name:N", title="", sort="-x"),
                x=alt.X(
                    "similarity:Q", title="Containment", scale=alt.Scale(domain=[0, 1])
                ),
                tooltip=["name:N", "similarity:Q"]
                + (["md5:N"] if "md5" in df.columns else []),
            )
            .properties(width=600, height=alt.Step(20), title="31mer containment")
            .resolve_scale(y="independent")
        )

        chart.save(args.output_plot, scale_factor=2)

        print(f"Created visualization with {len(df)} reference sequences")
        print(
            f"Containment scores range: {df['similarity'].min():.3f} - {df['similarity'].max():.3f}"
        )
        print(f"Plot saved to: {args.output_plot}")
        print(f"CSV saved to: {args.output_csv}")

    except Exception as e:
        print(f"Error processing CSV: {e}")
        import traceback

        traceback.print_exc()
        # Create error PNG
        with open(args.output_plot, "w") as f:
            f.write(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
