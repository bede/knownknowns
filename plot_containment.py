#!/usr/bin/env python3

import argparse
import os
import re
import shutil
import sys

import altair as alt
import pandas as pd


def natural_sort_key(text):
    """Generate a sort key for natural sorting of strings with numbers."""
    return tuple(int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", text))


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
        "--min-depth", type=int, default=1, help="Minimum depth used for filtering"
    )
    parser.add_argument(
        "--scaled", type=int, default=100, help="Scaled value used for sketching"
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

        required_cols = ["query_name", "containment"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"ERROR: Missing required columns: {missing_cols}")
            print(f"Available columns: {list(df.columns)}")
            with open(args.output_plot, "w") as f:
                f.write(f"Missing columns: {missing_cols}")
            return

        # Sort bars by sequence name (after first space if present) using natural sorting
        def get_sort_key(name):
            if " " in name:
                return name.split(" ", 1)[1]  # Substring after first space
            else:
                return name.split(" ")[0]  # First part (whole name if no space)

        df["sort_key"] = df["query_name"].apply(
            lambda x: natural_sort_key(get_sort_key(x))
        )
        df = df.sort_values("sort_key")
        df = df.drop("sort_key", axis=1)

        # Create text labels for median abundance (if column exists)
        if "median_abund" in df.columns:
            # Format the median abundance values
            df["depth_label"] = df["median_abund"].apply(
                lambda x: f"med(depth): {x:.0f}" if pd.notna(x) else "med(depth): 0"
            )

        # Create the bar chart
        bars = (
            alt.Chart(df)
            .mark_bar(size=8)
            .encode(
                y=alt.Y("query_name:N", title="", sort=list(df["query_name"])),
                x=alt.X(
                    "containment:Q", title="Containment", scale=alt.Scale(domain=[0, 1])
                ),
                tooltip=["query_name:N", "containment:Q"]
                + (["query_md5:N"] if "query_md5" in df.columns else []),
            )
        )

        # Add text labels if median abundance exists
        if "median_abund" in df.columns:
            text_labels = (
                alt.Chart(df)
                .mark_text(
                    align="left",
                    baseline="middle",
                    dx=5,  # Position just after the x-axis origin
                    fontSize=10,
                    color="black",
                )
                .encode(
                    y=alt.Y("query_name:N", sort=list(df["query_name"])),
                    x=alt.value(0),  # Position at x=0 (origin)
                    text="depth_label:N",
                )
            )

            # Layer the charts and add properties
            # Build title with scaled and min_depth (if > 1)
            title_parts = [f"scaled={args.scaled}"]
            if args.min_depth > 1:
                title_parts.append(f"min_depth={args.min_depth}")
            title = f"{args.title_prefix + ' ' if args.title_prefix else ''}(k={args.kmer}, {', '.join(title_parts)})"

            chart = (
                (bars + text_labels)
                .properties(
                    width=600,
                    height=alt.Step(20),
                    title=title,
                )
                .resolve_scale(y="shared")
            )
        else:
            # Build title with scaled and min_depth (if > 1)
            title_parts = [f"scaled={args.scaled}"]
            if args.min_depth > 1:
                title_parts.append(f"min_depth={args.min_depth}")
            title = f"{args.title_prefix + ' ' if args.title_prefix else ''}(k={args.kmer}, {', '.join(title_parts)})"

            chart = bars.properties(
                width=600,
                height=alt.Step(20),
                title=title,
            ).resolve_scale(y="independent")

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
            if (
                not df.empty
                and "query_name" in df.columns
                and "containment" in df.columns
            ):
                # Extract sample name from filename
                sample_name = os.path.basename(csv_file).replace(".csv", "")
                df = df.assign(barcode=sample_name)
                dfs.append(df)

    if not dfs:
        print("No valid CSV files found")
        # Create empty CSV file to satisfy Nextflow output requirement
        empty_df = pd.DataFrame(columns=["query_name", "containment", "barcode"])
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

    combined_df["short_name"] = combined_df["query_name"].apply(extract_short_name)

    # Get unique sample names for ordering using natural sorting
    barcode_order = sorted(combined_df["barcode"].unique(), key=natural_sort_key)

    # Sort the dataframe by natural sort order for consistent bar positioning
    combined_df["barcode_sort_key"] = combined_df["barcode"].apply(natural_sort_key)
    combined_df["short_name_sort_key"] = combined_df["short_name"].apply(
        natural_sort_key
    )
    combined_df = combined_df.sort_values(["short_name_sort_key", "barcode_sort_key"])
    combined_df = combined_df.drop(["barcode_sort_key", "short_name_sort_key"], axis=1)

    # Get naturally sorted unique short names for y-axis ordering
    short_name_order = sorted(combined_df["short_name"].unique(), key=natural_sort_key)

    # Create text labels for median abundance (if column exists)
    if "median_abund" in combined_df.columns:
        # Format the median abundance values
        combined_df["depth_label"] = combined_df["median_abund"].apply(
            lambda x: f"med(depth): {x:.0f}" if pd.notna(x) else "med(depth): 0"
        )

    # Create the combined bar chart
    bars = (
        alt.Chart(combined_df)
        .mark_bar(size=8)
        .encode(
            y=alt.Y("short_name:N", title="", sort=short_name_order),
            x=alt.X(
                "containment:Q", title="Containment", scale=alt.Scale(domain=[0, 1])
            ),
            color=alt.Color(
                "barcode",
                sort=barcode_order,
                title="",
                scale=alt.Scale(scheme="category20"),
            ),
            yOffset=alt.YOffset("barcode:N", sort=barcode_order),
            tooltip=["short_name:N", "containment:Q", "barcode:N"],
        )
    )

    # Add text labels if median abundance exists
    if "median_abund" in combined_df.columns:
        text_labels = (
            alt.Chart(combined_df)
            .mark_text(
                align="left",
                baseline="middle",
                dx=5,  # Position just after the x-axis origin
                fontSize=8,
                color="black",
            )
            .encode(
                y=alt.Y("short_name:N", sort=short_name_order),
                yOffset=alt.YOffset("barcode:N", sort=barcode_order),
                x=alt.value(0),  # Position at x=0 (origin)
                text="depth_label:N",
            )
        )

        # Layer the charts and add properties
        # Build title with scaled and min_depth (if > 1)
        title_parts = [f"scaled={args.scaled}"]
        if args.min_depth > 1:
            title_parts.append(f"min_depth={args.min_depth}")
        title = f"k={args.kmer}, {', '.join(title_parts)}"

        chart = (
            (bars + text_labels)
            .properties(
                title=title,
                width=400,
                height=alt.Step(8),
            )
            .resolve_scale(y="shared")
        )
    else:
        # Build title with scaled and min_depth (if > 1)
        title_parts = [f"scaled={args.scaled}"]
        if args.min_depth > 1:
            title_parts.append(f"min_depth={args.min_depth}")
        title = f"k={args.kmer}, {', '.join(title_parts)}"

        chart = bars.properties(
            title=title,
            width=400,
            height=alt.Step(8),
        ).resolve_scale(y="independent")

    chart.save(args.output_plot, scale_factor=2.0)
    print(f"Combined plot saved to: {args.output_plot}")


if __name__ == "__main__":
    main()
