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
    parser.add_argument(
        "input_csv", nargs="+", help="Input CSV file(s) from sourmash search"
    )
    parser.add_argument(
        "--output-plot", default="containment_plot.png", help="Output plot filename"
    )
    parser.add_argument(
        "--output-csv", default="containment.csv", help="Output CSV filename"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--title-prefix", default="", help="Prefix for the plot title")
    parser.add_argument(
        "--kmer", type=int, default=31, help="K-mer length used for sketching"
    )
    parser.add_argument(
        "--combined",
        action="store_true",
        help="Create combined plot from multiple CSV files",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Skip plot generation, only process CSV files",
    )

    args = parser.parse_args()

    # Route to appropriate plotting function
    if args.combined:
        create_combined_plot(args)
    else:
        create_single_plot(args)


def create_single_plot(args):
    """Create plot for a single CSV file."""
    input_csv = args.input_csv[0]  # Single file mode

    if args.debug:
        print(f"CSV file size: {os.path.getsize(input_csv)} bytes")
        print("CSV file contents:")
        with open(input_csv) as f:
            content = f.read()
            print(repr(content))

    if input_csv != args.output_csv:
        shutil.copy(input_csv, args.output_csv)

    try:
        if os.path.getsize(input_csv) == 0:
            print("ERROR: CSV file is empty")
            # Create a dummy PNG file
            with open(args.output_plot, "w") as f:
                f.write("No data to visualize - CSV file is empty")
            return

        df = pd.read_csv(input_csv)

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

        # Skip plotting if requested
        if args.no_plot:
            print(f"Skipping plot generation. CSV saved to: {args.output_csv}")
            return

        alt.data_transformers.enable("json")

        required_cols = ["name", "similarity"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"ERROR: Missing required columns: {missing_cols}")
            print(f"Available columns: {list(df.columns)}")
            with open(args.output_plot, "w") as f:
                f.write(f"Missing columns: {missing_cols}")
            return

        # Sort bars by sequence name (after first space if present)
        def get_sort_key(name):
            if " " in name:
                return name.split(" ", 1)[1]  # Substring after first space
            else:
                return name.split(" ")[0]  # First part (whole name if no space)

        df["sort_key"] = df["name"].apply(get_sort_key)
        df = df.sort_values("sort_key")
        df = df.drop("sort_key", axis=1)

        chart = (
            alt.Chart(df)
            .mark_bar(size=8)
            .encode(
                y=alt.Y("name:N", title="", sort=list(df["name"])),
                x=alt.X(
                    "similarity:Q", title="Containment", scale=alt.Scale(domain=[0, 1])
                ),
                tooltip=["name:N", "similarity:Q"]
                + (["md5:N"] if "md5" in df.columns else []),
            )
            .properties(
                width=600,
                height=alt.Step(20),
                title=f"{args.title_prefix + ' ' if args.title_prefix else ''}containment (k={args.kmer})",
            )
            .resolve_scale(y="independent")
        )

        chart.save(args.output_plot, scale_factor=2)
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


def create_combined_plot(args):
    """Create combined plot from multiple CSV files."""
    try:
        # First, create the combined CSV
        create_combined_csv(args)

        # Skip plotting if requested
        if args.no_plot:
            print("Skipping plot generation. CSV data processed.")
            return

        # Now create the plot from the combined CSV
        create_plot_from_combined_csv(args)

    except Exception as e:
        print(f"Error creating combined plot: {e}")
        import traceback

        traceback.print_exc()
        with open(args.output_plot, "w") as f:
            f.write(f"Error: {e}")
        sys.exit(1)


def create_combined_csv(args):
    """Create combined CSV from multiple individual CSV files."""
    # Read and combine all CSV files
    dfs = []
    for csv_file in args.input_csv:
        if os.path.exists(csv_file) and os.path.getsize(csv_file) > 0:
            df = pd.read_csv(csv_file)
            if not df.empty and "name" in df.columns and "similarity" in df.columns:
                # Extract sample name from filename
                sample_name = os.path.basename(csv_file).replace(".csv", "")
                df = df.assign(barcode=sample_name)
                dfs.append(df)

    if not dfs:
        print("No valid CSV files found")
        # Create empty CSV file to satisfy Nextflow output requirement
        empty_df = pd.DataFrame(columns=["name", "similarity", "barcode"])
        empty_df.to_csv(args.output_csv, index=False)
        print(f"Empty CSV saved to: {args.output_csv}")
        return False

    # Combine all dataframes
    combined_df = pd.concat(dfs, ignore_index=True)

    # Save combined CSV file
    combined_df.to_csv(args.output_csv, index=False)
    print(f"Combined CSV saved to: {args.output_csv}")
    return True


def create_plot_from_combined_csv(args):
    """Create plot from the combined CSV file."""
    # Read the combined CSV
    combined_df = pd.read_csv(args.output_csv)

    if combined_df.empty:
        print("No data in combined CSV")
        with open(args.output_plot, "w") as f:
            f.write("No valid data found")
        return

    # Extract short names for cleaner visualization
    def extract_short_name(name):
        if " " in name:
            return name.split(" ", 1)[1]
        return name

    combined_df["short_name"] = combined_df["name"].apply(extract_short_name)

    # Get unique sample names for ordering
    barcode_order = list(combined_df["barcode"].unique())

    # Create the combined chart
    chart = (
        alt.Chart(combined_df)
        .mark_bar(size=8)
        .encode(
            y=alt.Y("short_name:N", title=""),
            x=alt.X(
                "similarity:Q", title="Containment", scale=alt.Scale(domain=[0, 1])
            ),
            color=alt.Color("barcode", sort=barcode_order, title=""),
            yOffset=alt.YOffset("barcode:N", sort=barcode_order),
            tooltip=["short_name:N", "similarity:Q", "barcode:N"],
        )
        .properties(
            title=f"Combined containment analysis (k={args.kmer})",
            width=400,
            height=alt.Step(8),
        )
        .resolve_scale(y="independent")
    )

    chart.save(args.output_plot, scale_factor=2.0)
    print(f"Combined plot saved to: {args.output_plot}")


if __name__ == "__main__":
    main()
